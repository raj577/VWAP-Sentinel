"""Admin diagnostics for market-data ingestion.

Protected by the interim admin API key until Phase 5 introduces JWT roles.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.api.deps import require_admin_key
from backend.db.models import IngestionJob, IngestionJobItem
from backend.db.session import get_db
from backend.schemas.market_data import (
    IngestionSummaryOut,
    JobDetail,
    JobItemOut,
    JobOut,
    JobPage,
)

router = APIRouter(
    prefix="/admin/market-data",
    tags=["admin"],
    dependencies=[Depends(require_admin_key)],
)


@router.get("/jobs", response_model=JobPage, summary="Ingestion job history")
def list_jobs(
    db: Session = Depends(get_db),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
) -> JobPage:
    total = int(
        db.scalar(select(func.count()).select_from(IngestionJob)) or 0
    )
    rows = db.scalars(
        select(IngestionJob)
        .order_by(IngestionJob.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()
    return JobPage(
        items=[JobOut.model_validate(row) for row in rows],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get(
    "/jobs/{job_id}",
    response_model=JobDetail,
    summary="One ingestion job with per-instrument results",
)
def get_job(job_id: int, db: Session = Depends(get_db)) -> JobDetail:
    job = db.get(IngestionJob, job_id)
    if job is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Ingestion job not found: {job_id}",
        )
    items = db.scalars(
        select(IngestionJobItem)
        .where(IngestionJobItem.job_id == job_id)
        .order_by(IngestionJobItem.symbol)
    ).all()
    return JobDetail(
        **JobOut.model_validate(job).model_dump(),
        items=[JobItemOut.model_validate(item) for item in items],
    )


@router.get(
    "/ingestion-summary",
    response_model=IngestionSummaryOut,
    summary="Aggregate ingestion health",
)
def ingestion_summary(db: Session = Depends(get_db)) -> IngestionSummaryOut:
    jobs_total = int(
        db.scalar(select(func.count()).select_from(IngestionJob)) or 0
    )
    completed = int(
        db.scalar(
            select(func.count())
            .select_from(IngestionJob)
            .where(IngestionJob.status == "COMPLETED")
        )
        or 0
    )
    failed = int(
        db.scalar(
            select(func.count())
            .select_from(IngestionJob)
            .where(IngestionJob.status == "FAILED")
        )
        or 0
    )
    last_completed = db.scalar(select(func.max(IngestionJob.completed_at)))
    last_success = db.scalar(
        select(func.max(IngestionJob.completed_at)).where(
            IngestionJob.status == "COMPLETED"
        )
    )

    last_job_id = db.scalar(select(func.max(IngestionJob.id)))
    failure_symbols: list[str] = []
    if last_job_id is not None:
        failure_symbols = list(
            db.scalars(
                select(IngestionJobItem.symbol)
                .where(
                    IngestionJobItem.job_id == last_job_id,
                    IngestionJobItem.status == "FAILED",
                )
                .order_by(IngestionJobItem.symbol)
                .limit(50)
            )
        )

    return IngestionSummaryOut(
        jobs_total=jobs_total,
        completed_jobs=completed,
        failed_jobs=failed,
        last_completed_at=last_completed,
        last_success_at=last_success,
        last_failed_instruments=failure_symbols,
    )
