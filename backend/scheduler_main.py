"""Dedicated scheduler process.

One instance only. It holds a PostgreSQL advisory lock for its lifetime, so a
second scheduler exits instead of double-scheduling. It only enqueues jobs;
the worker executes them.
"""

from __future__ import annotations

import logging
import time
from datetime import timezone

from sqlalchemy import text

from backend.core.config import get_settings
from backend.core.logging import configure_logging
from backend.core.time import utcnow
from backend.db.session import get_session_factory
from backend.services.pipeline import (
    JOB_FULL_PIPELINE,
    TRIGGER_SCHEDULED,
    PipelineAlreadyRunning,
    enqueue_pipeline,
)
from backend.services.scheduler_settings import (
    calendar_from_settings,
    compute_next_run,
    get_scheduler_settings,
)

logger = logging.getLogger("vwap_sentinel.scheduler")


def should_enqueue_scheduled(
    enabled: bool,
    next_run_at,
    now,
    calendar,
) -> bool:
    """Pure decision used by the loop and by tests."""

    if not enabled or next_run_at is None:
        return False
    current = next_run_at
    if current.tzinfo is None:
        current = current.replace(tzinfo=timezone.utc)
    if now < current:
        return False
    return calendar.is_market_open(now)


def _acquire_instance_lock(factory):
    bind = factory.kw["bind"] if "bind" in factory.kw else None
    if bind is None:
        return None
    if bind.dialect.name != "postgresql":
        return None
    connection = bind.connect()
    acquired = bool(
        connection.execute(
            text("SELECT pg_try_advisory_lock(:key)"),
            {"key": get_settings().scheduler_lock_key},
        ).scalar()
    )
    if not acquired:
        connection.close()
        return False
    return connection


def main() -> int:
    settings = get_settings()
    configure_logging(settings.log_level)
    factory = get_session_factory()

    lock = _acquire_instance_lock(factory)
    if lock is False:
        logger.error("Another scheduler instance already holds the lock; exiting")
        return 0

    logger.info(
        "Scheduler started (interval=%s min, timezone=%s)",
        settings.scheduler_interval_minutes,
        settings.timezone,
    )

    while True:
        try:
            db = factory()
            try:
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
                        logger.info("Scheduled pipeline enqueued")
                    except PipelineAlreadyRunning as exc:
                        logger.warning(
                            "Skipping scheduled run; job %s active", exc.job_id
                        )
                elif due:
                    logger.info(
                        "Skipping scheduled run; market closed (%s)",
                        row.timezone,
                    )

                if due:
                    row.next_run_at = compute_next_run(
                        now, row.scan_interval_minutes, True
                    )
                    row.updated_by = "scheduler"
                    db.commit()
            finally:
                db.close()
        except KeyboardInterrupt:
            logger.info("Scheduler interrupted; exiting")
            return 0
        except Exception:
            logger.exception("Scheduler loop error; continuing")

        time.sleep(max(settings.scheduler_tick_seconds, 1))


if __name__ == "__main__":
    raise SystemExit(main())
