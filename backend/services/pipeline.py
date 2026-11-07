"""Pipeline orchestration: ingestion then scanning, with locking and recovery.

A pipeline job is the unit of work for both the scheduler and manual admin
actions. A separate worker process claims PENDING jobs and executes them.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from time import monotonic, perf_counter
from typing import Any

from sqlalchemy import select, text
from sqlalchemy.orm import Session, sessionmaker

from backend.core.config import get_settings
from backend.core.time import utcnow
from backend.db.models import IngestionJobItem, PipelineJob, PipelineJobLog
from backend.services.ingestion import (
    IngestionAlreadyRunning,
    IngestionCancelled,
    IngestionResult,
    MarketDataIngestionService,
)
from backend.services.scanner import (
    ScanAlreadyRunning,
    ScanCancelled,
    ScanRunSummary,
    ScannerService,
)

logger = logging.getLogger("vwap_sentinel.pipeline")

JOB_FULL_PIPELINE = "FULL_PIPELINE"
JOB_INGESTION = "INGESTION"
JOB_SCAN = "SCAN"

TRIGGER_MANUAL = "MANUAL"
TRIGGER_SCHEDULED = "SCHEDULED"

STATUS_PENDING = "PENDING"
STATUS_RUNNING = "RUNNING"
STATUS_COMPLETED = "COMPLETED"
STATUS_PARTIALLY_COMPLETED = "PARTIALLY_COMPLETED"
STATUS_FAILED = "FAILED"
STATUS_CANCELLED = "CANCELLED"

STAGE_QUEUED = "QUEUED"
STAGE_FETCHING = "FETCHING_CANDLES"
STAGE_SCANNING = "RUNNING_SCANNER"
STAGE_DONE = "COMPLETED"


class PipelineError(RuntimeError):
    """A pipeline job could not be queued or executed."""


class PipelineAlreadyRunning(PipelineError):
    def __init__(self, job_id: int) -> None:
        super().__init__(f"Pipeline job {job_id} is already pending or running.")
        self.job_id = job_id


class PipelineFailure(PipelineError):
    """A stage reported a hard failure."""


@dataclass(frozen=True)
class IngestionOutcome:
    job_id: int | None
    status: str
    total: int
    successful: int
    failed: int
    inserted: int
    updated: int
    error: str | None = None


@dataclass(frozen=True)
class ScanOutcome:
    scan_run_id: int | None
    status: str
    scanned: int
    failed: int
    matches: int
    error: str | None = None


def _as_aware(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value


def active_pipeline_job(db: Session) -> PipelineJob | None:
    return db.scalar(
        select(PipelineJob)
        .where(PipelineJob.status.in_([STATUS_PENDING, STATUS_RUNNING]))
        .order_by(PipelineJob.id)
        .limit(1)
    )


def enqueue_pipeline_in_session(
    db: Session, job_type: str, trigger_source: str
) -> PipelineJob:
    """Queue a job using an existing session (API request or scheduler loop)."""

    settings = get_settings()
    if db.get_bind().dialect.name == "postgresql":
        db.execute(
            text("SELECT pg_advisory_xact_lock(:key)"),
            {"key": settings.pipeline_lock_key},
        )
    active = active_pipeline_job(db)
    if active is not None:
        raise PipelineAlreadyRunning(active.id)

    job = PipelineJob(
        job_type=job_type,
        trigger_source=trigger_source,
        status=STATUS_PENDING,
        stage=STAGE_QUEUED,
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    logger.info("Queued pipeline job %s (%s)", job.id, job_type)
    return job


def enqueue_pipeline(
    session_factory: sessionmaker[Session],
    job_type: str,
    trigger_source: str,
) -> PipelineJob:
    """Create a PENDING job, refusing a second concurrent pipeline."""

    db = session_factory()
    try:
        return enqueue_pipeline_in_session(db, job_type, trigger_source)
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def claim_next_job(
    session_factory: sessionmaker[Session], owner: str
) -> int | None:
    db = session_factory()
    try:
        statement = (
            select(PipelineJob)
            .where(PipelineJob.status == STATUS_PENDING)
            .order_by(PipelineJob.id)
            .limit(1)
        )
        if db.get_bind().dialect.name == "postgresql":
            statement = statement.with_for_update(skip_locked=True)
        job = db.scalar(statement)
        if job is None:
            return None
        now = utcnow()
        job.status = STATUS_RUNNING
        job.stage = "STARTING"
        job.owner = owner
        job.started_at = now
        job.heartbeat_at = now
        db.commit()
        logger.info("Worker %s claimed pipeline job %s", owner, job.id)
        return job.id
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def recover_abandoned_jobs(
    session_factory: sessionmaker[Session],
    timeout_seconds: int,
    now: datetime | None = None,
) -> list[int]:
    """Fail or cancel RUNNING jobs whose worker heartbeat went stale."""

    current = _as_aware(now or utcnow())
    assert current is not None
    cutoff = current - timedelta(seconds=max(int(timeout_seconds), 1))

    db = session_factory()
    recovered: list[int] = []
    try:
        jobs = list(
            db.scalars(select(PipelineJob).where(PipelineJob.status == STATUS_RUNNING))
        )
        for job in jobs:
            reference = _as_aware(job.heartbeat_at or job.started_at)
            if reference is None or reference >= cutoff:
                continue
            job.status = (
                STATUS_CANCELLED
                if job.cancellation_requested_at is not None
                else STATUS_FAILED
            )
            job.stage = job.status
            job.completed_at = current
            job.duration_seconds = (
                (current - (_as_aware(job.started_at) or current)).total_seconds()
            )
            job.error_summary = (
                "Cancellation acknowledged after worker shutdown"
                if job.status == STATUS_CANCELLED
                else "Worker heartbeat expired; job marked abandoned"
            )
            recovered.append(job.id)
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()

    if recovered:
        logger.warning("Recovered abandoned pipeline jobs: %s", recovered)
    return recovered


class PipelineExecutor:
    """Executes one claimed pipeline job and records every stage."""

    def __init__(
        self,
        session_factory: sessionmaker[Session],
        *,
        ingestion_runner: Callable[[PipelineJob, Callable[[], bool], Callable[..., None]], IngestionOutcome] | None = None,
        scan_runner: Callable[[PipelineJob, Callable[[], bool], Callable[..., None]], ScanOutcome] | None = None,
        clock: Callable[[], datetime] = utcnow,
    ) -> None:
        self.session_factory = session_factory
        self._ingestion_runner = ingestion_runner
        self._scan_runner = scan_runner
        self._clock = clock
        self.settings = get_settings()

    # ------------------------------------------------------------------ run
    def execute(self, job_id: int, owner: str = "worker") -> PipelineJob:
        db = self.session_factory()
        job = db.get(PipelineJob, job_id)
        if job is None:
            db.close()
            raise PipelineError(f"Pipeline job not found: {job_id}")
        if job.status != STATUS_RUNNING:
            now = self._clock()
            job.status = STATUS_RUNNING
            job.stage = "STARTING"
            job.owner = owner
            job.started_at = now
            job.heartbeat_at = now
            db.commit()
            db.refresh(job)

        started = perf_counter()
        cancel_check = self._cancel_probe(job.id)
        ingestion: IngestionOutcome | None = None
        scan: ScanOutcome | None = None
        cancelled = False
        failure: str | None = None

        try:
            if cancel_check():
                raise IngestionCancelled("Cancellation requested")

            if job.job_type in {JOB_FULL_PIPELINE, JOB_INGESTION}:
                self._set_stage(db, job, STAGE_FETCHING)
                ingestion = self._run_ingestion(job, cancel_check)
                self._apply_ingestion(db, job, ingestion)
                if ingestion.status == STATUS_CANCELLED:
                    cancelled = True
                elif ingestion.status == STATUS_FAILED:
                    raise PipelineFailure(
                        ingestion.error or "Ingestion failed; scan skipped."
                    )

            if (
                not cancelled
                and job.job_type in {JOB_FULL_PIPELINE, JOB_SCAN}
                and failure is None
            ):
                if cancel_check():
                    raise IngestionCancelled("Cancellation requested")
                self._set_stage(db, job, STAGE_SCANNING)
                scan = self._run_scan(job, cancel_check, ingestion)
                self._apply_scan(db, job, scan)
                if scan.status == STATUS_CANCELLED:
                    cancelled = True

        except (IngestionCancelled, ScanCancelled):
            cancelled = True
        except (IngestionAlreadyRunning, ScanAlreadyRunning) as exc:
            failure = str(exc)
        except PipelineFailure as exc:
            failure = str(exc)
        except Exception as exc:
            logger.exception("Pipeline job %s failed", job.id)
            failure = f"{type(exc).__name__}: {exc}"
        finally:
            self._finalize(
                db,
                job,
                cancelled=cancelled,
                failure=failure,
                ingestion=ingestion,
                scan=scan,
                duration=perf_counter() - started,
            )
            db.close()

        return job

    # --------------------------------------------------------------- stages
    def _run_ingestion(
        self, job: PipelineJob, cancel_check: Callable[[], bool]
    ) -> IngestionOutcome:
        if self._ingestion_runner is not None:
            return self._ingestion_runner(job, cancel_check, self._progress(job.id))

        service = MarketDataIngestionService(self.session_factory)
        result: IngestionResult = service.run(
            triggered_by=job.trigger_source.lower(),
            pipeline_job_id=job.id,
            should_cancel=cancel_check,
            progress_callback=self._ingestion_progress(job.id),
        )
        return IngestionOutcome(
            job_id=result.job_id,
            status=result.status,
            total=result.total_instruments,
            successful=result.successful_instruments,
            failed=result.failed_instruments,
            inserted=result.candles_inserted,
            updated=result.candles_updated,
            error=result.error_summary,
        )

    def _run_scan(
        self,
        job: PipelineJob,
        cancel_check: Callable[[], bool],
        ingestion: IngestionOutcome | None,
    ) -> ScanOutcome:
        if self._scan_runner is not None:
            return self._scan_runner(job, cancel_check, self._progress(job.id))

        service = ScannerService(self.session_factory)
        summary: ScanRunSummary = service.run(
            triggered_by=job.trigger_source.lower(),
            scan_type="AUTOMATIC" if job.trigger_source == TRIGGER_SCHEDULED else "MANUAL",
            pipeline_job_id=job.id,
            ingestion_job_id=ingestion.job_id if ingestion else None,
            should_cancel=cancel_check,
            progress_callback=self._scan_progress(job.id, job.job_type),
        )
        return ScanOutcome(
            scan_run_id=summary.scan_run_id,
            status=summary.status,
            scanned=summary.instruments_scanned,
            failed=summary.failed_instruments,
            matches=summary.matches_count,
            error=None,
        )

    # ------------------------------------------------------------ recording
    def _set_stage(self, db: Session, job: PipelineJob, stage: str) -> None:
        job.stage = stage
        job.heartbeat_at = self._clock()
        db.commit()

    def _apply_ingestion(
        self, db: Session, job: PipelineJob, outcome: IngestionOutcome
    ) -> None:
        job.ingestion_job_id = outcome.job_id
        job.total_instruments = outcome.total
        job.processed_instruments = outcome.successful
        job.failed_instruments = outcome.failed
        job.candles_fetched = outcome.inserted + outcome.updated
        job.candles_inserted = outcome.inserted
        job.candles_updated = outcome.updated
        job.heartbeat_at = self._clock()
        if outcome.error:
            job.error_summary = outcome.error[:2000]
        if outcome.job_id is not None:
            items = db.scalars(
                select(IngestionJobItem).where(
                    IngestionJobItem.job_id == outcome.job_id
                )
            ).all()
            for item in items:
                db.add(
                    PipelineJobLog(
                        job_id=job.id,
                        instrument_id=item.instrument_id,
                        symbol=item.symbol,
                        status=item.status,
                        candles_processed=item.candles_seen,
                        error_message=item.error,
                    )
                )
        db.commit()

    def _apply_scan(
        self, db: Session, job: PipelineJob, outcome: ScanOutcome
    ) -> None:
        job.scan_run_id = outcome.scan_run_id
        if job.job_type == JOB_SCAN:
            job.total_instruments = outcome.scanned
            job.processed_instruments = outcome.scanned - outcome.failed
            job.failed_instruments = outcome.failed
        job.heartbeat_at = self._clock()
        if outcome.error:
            job.error_summary = outcome.error[:2000]
        db.commit()

    def _finalize(
        self,
        db: Session,
        job: PipelineJob,
        *,
        cancelled: bool,
        failure: str | None,
        ingestion: IngestionOutcome | None,
        scan: ScanOutcome | None,
        duration: float,
    ) -> None:
        now = self._clock()
        if cancelled:
            status = STATUS_CANCELLED
        elif failure is not None:
            status = STATUS_FAILED
        elif ingestion is not None and ingestion.status == STATUS_PARTIALLY_COMPLETED:
            status = STATUS_PARTIALLY_COMPLETED
        elif ingestion is not None and ingestion.status == STATUS_FAILED:
            status = STATUS_FAILED
        elif scan is not None and scan.status not in {STATUS_COMPLETED}:
            status = STATUS_FAILED
        elif job.job_type == JOB_SCAN and scan is None:
            status = STATUS_FAILED
        else:
            status = STATUS_COMPLETED

        job.status = status
        job.stage = status
        job.completed_at = now
        job.duration_seconds = round(duration, 3)
        job.heartbeat_at = now
        if failed := failure:
            job.error_summary = (job.error_summary or "") or failed
            job.error_summary = job.error_summary[:2000]
        if status == STATUS_CANCELLED:
            job.error_summary = "Cancellation requested"
        try:
            db.commit()
        except Exception:
            db.rollback()
            logger.exception("Could not finalize pipeline job %s", job.id)

    # ------------------------------------------------------------- progress
    def _progress(self, job_id: int) -> Callable[..., None]:
        def update(**fields: Any) -> None:
            self._update(job_id, **fields)

        return update

    def _ingestion_progress(self, job_id: int) -> Callable[[int, int, int, int], None]:
        state = {"calls": 0}

        def update(processed: int, total: int, successful: int, failed: int) -> None:
            state["calls"] += 1
            if state["calls"] % 5 != 0:
                return
            self._update(
                job_id,
                processed_instruments=successful,
                failed_instruments=failed,
                total_instruments=total,
                heartbeat_at=self._clock(),
            )

        return update

    def _scan_progress(self, job_id: int, job_type: str) -> Callable[[int, int, int, int], None]:
        state = {"calls": 0}

        def update(scanned: int, total: int, matches: int, failed: int) -> None:
            state["calls"] += 1
            if state["calls"] % 10 != 0:
                return
            fields: dict[str, Any] = {
                "processed_instruments": scanned,
                "heartbeat_at": self._clock(),
            }
            if job_type == JOB_SCAN:
                fields["total_instruments"] = total
                fields["failed_instruments"] = failed
            self._update(job_id, **fields)

        return update

    def _update(self, job_id: int, **fields: Any) -> None:
        db = self.session_factory()
        try:
            job = db.get(PipelineJob, job_id)
            if job is not None:
                for key, value in fields.items():
                    setattr(job, key, value)
                db.commit()
        except Exception:
            db.rollback()
            logger.debug("Could not update pipeline progress", exc_info=True)
        finally:
            db.close()

    def _cancel_probe(self, job_id: int) -> Callable[[], bool]:
        cache: dict[str, float | bool] = {"checked": 0.0, "cancelled": False}

        def should_cancel() -> bool:
            now = monotonic()
            if now - float(cache["checked"]) < 2.0:
                return bool(cache["cancelled"])
            db = self.session_factory()
            try:
                job = db.get(PipelineJob, job_id)
                cache["cancelled"] = bool(
                    job is not None
                    and (
                        job.cancellation_requested_at is not None
                        or job.status == STATUS_CANCELLED
                    )
                )
            except Exception:
                logger.debug("Cancellation probe failed", exc_info=True)
            finally:
                db.close()
            cache["checked"] = now
            return bool(cache["cancelled"])

        return should_cancel
