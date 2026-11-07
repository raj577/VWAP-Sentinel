"""Admin scheduler and pipeline control APIs."""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.api.deps import require_admin_key
from backend.core.config import get_settings
from backend.core.time import utcnow
from backend.db.models import MarketCandle, PipelineJob, PipelineJobLog, ScanRun
from backend.db.session import get_db
from backend.schemas.market_data import ScanRunOut
from backend.schemas.pipeline import (
    CancelJobRequest,
    PipelineJobLogOut,
    PipelineJobOut,
    PipelineJobPage,
    PipelineLogPage,
    PipelineSummaryOut,
    RunScannerRequest,
    SchedulerSettingsOut,
    SchedulerSettingsPatch,
    SchedulerStatusOut,
)
from backend.services.pipeline import (
    JOB_FULL_PIPELINE,
    JOB_SCAN,
    STATUS_CANCELLED,
    STATUS_COMPLETED,
    STATUS_FAILED,
    STATUS_PARTIALLY_COMPLETED,
    STATUS_PENDING,
    STATUS_RUNNING,
    TRIGGER_MANUAL,
    PipelineAlreadyRunning,
    active_pipeline_job,
    enqueue_pipeline_in_session,
)
from backend.services.scheduler_settings import (
    calendar_from_settings,
    compute_next_run,
    get_scheduler_settings,
)

logger = logging.getLogger("vwap_sentinel.admin_pipeline")

router = APIRouter(
    prefix="/admin",
    tags=["admin"],
    dependencies=[Depends(require_admin_key)],
)

TERMINAL_STATUSES = {
    STATUS_COMPLETED,
    STATUS_PARTIALLY_COMPLETED,
    STATUS_FAILED,
    STATUS_CANCELLED,
}


def _aware(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value


def _settings_out(row) -> SchedulerSettingsOut:
    return SchedulerSettingsOut.model_validate(row)


def _job_or_404(db: Session, job_id: int) -> PipelineJob:
    job = db.get(PipelineJob, job_id)
    if job is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Pipeline job not found: {job_id}",
        )
    return job


def _freshness(db: Session) -> datetime | None:
    return db.scalar(select(func.max(MarketCandle.timestamp)))


def _latest_scan(db: Session) -> ScanRun | None:
    return db.scalar(
        select(ScanRun)
        .where(ScanRun.status == "COMPLETED")
        .order_by(ScanRun.id.desc())
        .limit(1)
    )


# --------------------------------------------------------------- scheduler
@router.get(
    "/scheduler/settings",
    response_model=SchedulerSettingsOut,
    summary="Scheduler settings",
)
def get_settings_endpoint(db: Session = Depends(get_db)) -> SchedulerSettingsOut:
    return _settings_out(get_scheduler_settings(db))


@router.patch(
    "/scheduler/settings",
    response_model=SchedulerSettingsOut,
    summary="Update scheduler settings",
)
def patch_settings(
    payload: SchedulerSettingsPatch, db: Session = Depends(get_db)
) -> SchedulerSettingsOut:
    row = get_scheduler_settings(db)
    changes = payload.model_dump(exclude_unset=True)

    if "market_open_time" in changes or "market_close_time" in changes:
        opening = changes.get("market_open_time", row.market_open_time)
        closing = changes.get("market_close_time", row.market_close_time)
        if opening >= closing:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="market_open_time must be earlier than market_close_time",
            )

    for key, value in changes.items():
        setattr(row, key, value)
    row.updated_by = "admin"
    if row.scheduler_enabled:
        row.next_run_at = compute_next_run(
            utcnow(), row.scan_interval_minutes, row.scheduler_enabled
        )
    else:
        row.next_run_at = None
    db.commit()
    db.refresh(row)
    return _settings_out(row)


@router.post(
    "/scheduler/pause",
    response_model=SchedulerSettingsOut,
    summary="Pause automatic scheduling",
)
def pause_scheduler(db: Session = Depends(get_db)) -> SchedulerSettingsOut:
    row = get_scheduler_settings(db)
    row.scheduler_enabled = False
    row.next_run_at = None
    row.updated_by = "admin"
    db.commit()
    db.refresh(row)
    return _settings_out(row)


@router.post(
    "/scheduler/resume",
    response_model=SchedulerSettingsOut,
    summary="Resume automatic scheduling",
)
def resume_scheduler(db: Session = Depends(get_db)) -> SchedulerSettingsOut:
    row = get_scheduler_settings(db)
    row.scheduler_enabled = True
    row.next_run_at = compute_next_run(
        utcnow(), row.scan_interval_minutes, True
    )
    row.updated_by = "admin"
    db.commit()
    db.refresh(row)
    return _settings_out(row)


@router.get(
    "/scheduler/status",
    response_model=SchedulerStatusOut,
    summary="Scheduler and data status",
)
def scheduler_status(db: Session = Depends(get_db)) -> SchedulerStatusOut:
    row = get_scheduler_settings(db)
    calendar = calendar_from_settings(row)
    scan = _latest_scan(db)
    return SchedulerStatusOut(
        settings=_settings_out(row),
        market_open=calendar.is_market_open(),
        server_time=utcnow(),
        active_job=(
            PipelineJobOut.model_validate(active)
            if (active := active_pipeline_job(db)) is not None
            else None
        ),
        last_scan_run=ScanRunOut.model_validate(scan) if scan else None,
        data_freshness_at=_freshness(db),
    )


# ---------------------------------------------------------------- pipeline
def _enqueue(db: Session, job_type: str) -> PipelineJobOut:
    try:
        job = enqueue_pipeline_in_session(db, job_type, TRIGGER_MANUAL)
    except PipelineAlreadyRunning as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Pipeline job {exc.job_id} is already pending or running.",
        ) from exc
    return PipelineJobOut.model_validate(job)


@router.post(
    "/pipeline/refresh",
    response_model=PipelineJobOut,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Queue market-data ingestion followed by scanning",
)
def refresh_market_data(db: Session = Depends(get_db)) -> PipelineJobOut:
    row = get_scheduler_settings(db)
    calendar = calendar_from_settings(row)
    if (
        not calendar.is_market_open()
        and not row.allow_manual_outside_market_hours
    ):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "The market is closed and manual refresh outside market hours is "
                "disabled in scheduler settings."
            ),
        )
    return _enqueue(db, JOB_FULL_PIPELINE)


@router.post(
    "/pipeline/run-scanner",
    response_model=PipelineJobOut,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Queue a scan using stored candles",
)
def run_scanner(
    payload: RunScannerRequest = RunScannerRequest(),
    db: Session = Depends(get_db),
) -> PipelineJobOut:
    fresh_at = _aware(_freshness(db))
    if fresh_at is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="No stored candles exist. Run a market-data refresh first.",
        )

    stale_after = get_settings().scan_stale_warning_hours
    age_hours = (utcnow() - fresh_at).total_seconds() / 3600.0
    if age_hours > stale_after and not payload.confirm_stale:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                f"Stored candles are stale ({age_hours:.1f}h old, threshold "
                f"{stale_after}h). Retry with confirm_stale=true to scan anyway."
            ),
        )
    return _enqueue(db, JOB_SCAN)


@router.post(
    "/pipeline/jobs/{job_id}/cancel",
    response_model=PipelineJobOut,
    summary="Request pipeline job cancellation",
)
def cancel_job(
    job_id: int,
    payload: CancelJobRequest = CancelJobRequest(),
    db: Session = Depends(get_db),
) -> PipelineJobOut:
    job = _job_or_404(db, job_id)
    if job.status in TERMINAL_STATUSES:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Job {job_id} is already {job.status}.",
        )

    now = utcnow()
    reason = (payload.reason or "Cancellation requested").strip()[:500]
    job.cancellation_requested_at = now

    if job.status == STATUS_PENDING:
        job.status = STATUS_CANCELLED
        job.stage = STATUS_CANCELLED
        job.completed_at = now
        job.error_summary = reason

    db.commit()
    db.refresh(job)
    return PipelineJobOut.model_validate(job)


# ------------------------------------------------------------ job reads
@router.get(
    "/pipeline/jobs",
    response_model=PipelineJobPage,
    summary="Pipeline job history",
)
def list_jobs(
    db: Session = Depends(get_db),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    job_status: str | None = Query(None, alias="status"),
    job_type: str | None = Query(None),
    trigger_source: str | None = Query(None),
    start: datetime | None = Query(None),
    end: datetime | None = Query(None),
) -> PipelineJobPage:
    filters = []
    if job_status:
        filters.append(PipelineJob.status == job_status)
    if job_type:
        filters.append(PipelineJob.job_type == job_type)
    if trigger_source:
        filters.append(PipelineJob.trigger_source == trigger_source)
    if start is not None:
        filters.append(PipelineJob.created_at >= start)
    if end is not None:
        filters.append(PipelineJob.created_at <= end)

    total = int(
        db.scalar(select(func.count()).select_from(PipelineJob).where(*filters))
        or 0
    )
    rows = db.scalars(
        select(PipelineJob)
        .where(*filters)
        .order_by(PipelineJob.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()
    return PipelineJobPage(
        items=[PipelineJobOut.model_validate(row) for row in rows],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get(
    "/pipeline/jobs/{job_id}",
    response_model=PipelineJobOut,
    summary="One pipeline job",
)
def get_job(job_id: int, db: Session = Depends(get_db)) -> PipelineJobOut:
    return PipelineJobOut.model_validate(_job_or_404(db, job_id))


@router.get(
    "/pipeline/jobs/{job_id}/logs",
    response_model=PipelineLogPage,
    summary="Per-instrument pipeline logs",
)
def get_job_logs(
    job_id: int,
    db: Session = Depends(get_db),
    page: int = Query(1, ge=1),
    page_size: int = Query(100, ge=1, le=500),
    log_status: str | None = Query(None, alias="status"),
) -> PipelineLogPage:
    _job_or_404(db, job_id)
    filters = [PipelineJobLog.job_id == job_id]
    if log_status:
        filters.append(PipelineJobLog.status == log_status)
    total = int(
        db.scalar(select(func.count()).select_from(PipelineJobLog).where(*filters))
        or 0
    )
    rows = db.scalars(
        select(PipelineJobLog)
        .where(*filters)
        .order_by(PipelineJobLog.id)
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()
    return PipelineLogPage(
        items=[PipelineJobLogOut.model_validate(row) for row in rows],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get(
    "/pipeline/summary",
    response_model=PipelineSummaryOut,
    summary="Pipeline health summary",
)
def pipeline_summary(db: Session = Depends(get_db)) -> PipelineSummaryOut:
    rows = db.execute(
        select(PipelineJob.status, func.count()).group_by(PipelineJob.status)
    ).all()
    counts = {status_value: int(count) for status_value, count in rows}
    total_jobs = sum(counts.values())
    active = active_pipeline_job(db)
    last_completed = db.scalar(
        select(func.max(PipelineJob.completed_at)).where(
            PipelineJob.status.in_(
                [STATUS_COMPLETED, STATUS_PARTIALLY_COMPLETED]
            )
        )
    )
    last_failed = db.scalar(
        select(func.max(PipelineJob.completed_at)).where(
            PipelineJob.status == STATUS_FAILED
        )
    )
    latest_scan = _latest_scan(db)
    return PipelineSummaryOut(
        counts=counts,
        total_jobs=total_jobs,
        active_job=(
            PipelineJobOut.model_validate(active) if active is not None else None
        ),
        last_completed_at=last_completed,
        last_failed_at=last_failed,
        last_scan_run_id=latest_scan.id if latest_scan else None,
        data_freshness_at=_freshness(db),
    )
