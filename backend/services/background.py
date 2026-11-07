"""Optional in-process worker and scheduler for single-service free hosting.

Set RUN_WORKER_INPROCESS=true and RUN_SCHEDULER_INPROCESS=true to run the
pipeline loops inside the API process. This is intended for one-instance hosts
such as Render/Koyeb free tiers; dedicated deployments should keep the separate
worker and scheduler commands.
"""

from __future__ import annotations

import logging
import os
import socket
import threading
import time
from datetime import timezone
from time import monotonic

from backend.core.config import get_settings
from backend.core.time import utcnow
from backend.db.session import get_session_factory
from backend.scheduler_main import should_enqueue_scheduled
from backend.services.pipeline import (
    JOB_FULL_PIPELINE,
    TRIGGER_SCHEDULED,
    PipelineAlreadyRunning,
    PipelineExecutor,
    claim_next_job,
    enqueue_pipeline,
    recover_abandoned_jobs,
)
from backend.services.scheduler_settings import (
    calendar_from_settings,
    compute_next_run,
    get_scheduler_settings,
)

logger = logging.getLogger("vwap_sentinel.inprocess")


class BackgroundRuntime:
    def __init__(self) -> None:
        self._stop = threading.Event()
        self._threads: list[threading.Thread] = []

    @property
    def running(self) -> bool:
        return any(thread.is_alive() for thread in self._threads)

    def start(self) -> None:
        settings = get_settings()
        if self.running:
            return
        if settings.run_worker_inprocess:
            thread = threading.Thread(
                target=self._worker_loop,
                name="inprocess-worker",
                daemon=True,
            )
            thread.start()
            self._threads.append(thread)
            logger.info("In-process worker started")
        if settings.run_scheduler_inprocess:
            thread = threading.Thread(
                target=self._scheduler_loop,
                name="inprocess-scheduler",
                daemon=True,
            )
            thread.start()
            self._threads.append(thread)
            logger.info("In-process scheduler started")

    def stop(self) -> None:
        self._stop.set()

    def _worker_loop(self) -> None:
        settings = get_settings()
        factory = get_session_factory()
        owner = f"inline-{socket.gethostname()}-{os.getpid()}"
        last_recovery = monotonic()
        try:
            recover_abandoned_jobs(factory, settings.job_heartbeat_timeout_seconds)
        except Exception:
            logger.exception("In-process worker recovery failed")

        while not self._stop.is_set():
            try:
                if monotonic() - last_recovery >= 60:
                    recover_abandoned_jobs(
                        factory, settings.job_heartbeat_timeout_seconds
                    )
                    last_recovery = monotonic()
                job_id = claim_next_job(factory, owner)
                if job_id is None:
                    self._stop.wait(max(settings.worker_poll_seconds, 1))
                    continue
                PipelineExecutor(factory).execute(job_id, owner=owner)
            except Exception:
                logger.exception("In-process worker loop error")
                self._stop.wait(max(settings.worker_poll_seconds, 1))

    def _scheduler_loop(self) -> None:
        settings = get_settings()
        factory = get_session_factory()
        while not self._stop.is_set():
            db = None
            try:
                db = factory()
                row = get_scheduler_settings(db)
                now = utcnow()
                if row.scheduler_enabled and row.next_run_at is None:
                    row.next_run_at = compute_next_run(
                        now, row.scan_interval_minutes, True
                    )
                    db.commit()

                next_run = row.next_run_at
                if next_run is not None and next_run.tzinfo is None:
                    next_run = next_run.replace(tzinfo=timezone.utc)

                due = (
                    row.scheduler_enabled
                    and next_run is not None
                    and now >= next_run
                )
                calendar = calendar_from_settings(row)

                if should_enqueue_scheduled(
                    row.scheduler_enabled, next_run, now, calendar
                ):
                    try:
                        enqueue_pipeline(
                            factory, JOB_FULL_PIPELINE, TRIGGER_SCHEDULED
                        )
                        row.last_run_at = now
                        logger.info("In-process scheduler enqueued a pipeline")
                    except PipelineAlreadyRunning as exc:
                        logger.warning(
                            "Scheduled run skipped; job %s active", exc.job_id
                        )
                elif due:
                    logger.info(
                        "Scheduled run skipped; market closed (%s)", row.timezone
                    )

                if due:
                    row.next_run_at = compute_next_run(
                        now, row.scan_interval_minutes, True
                    )
                    row.updated_by = "scheduler"
                    db.commit()
            except Exception:
                logger.exception("In-process scheduler loop error")
            finally:
                if db is not None:
                    db.close()
            self._stop.wait(max(settings.scheduler_tick_seconds, 1))


_runtime: BackgroundRuntime | None = None


def start_background_runtime() -> BackgroundRuntime | None:
    global _runtime
    settings = get_settings()
    if not (settings.run_worker_inprocess or settings.run_scheduler_inprocess):
        return None
    if _runtime is None:
        _runtime = BackgroundRuntime()
        _runtime.start()
    return _runtime


def stop_background_runtime() -> None:
    global _runtime
    if _runtime is not None:
        _runtime.stop()
        _runtime = None
