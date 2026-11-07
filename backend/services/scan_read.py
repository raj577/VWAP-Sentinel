"""Shared read helpers for scan runs and results."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from backend.db.models import ScanResult, ScanRun
from backend.schemas.market_data import ScanResultOut, ScanRunDetail, ScanRunOut


def load_scan_detail(db: Session, run_id: int) -> ScanRunDetail | None:
    run = db.scalar(
        select(ScanRun)
        .options(selectinload(ScanRun.results).selectinload(ScanResult.candles))
        .where(ScanRun.id == run_id)
    )
    if run is None:
        return None
    return ScanRunDetail(
        **ScanRunOut.model_validate(run).model_dump(),
        results=[
            ScanResultOut.model_validate(item)
            for item in sorted(
                run.results, key=lambda item: abs(float(item.distance_pct))
            )
        ],
    )


def latest_completed_run_id(db: Session) -> int | None:
    return db.scalar(
        select(ScanRun.id)
        .where(ScanRun.status == "COMPLETED")
        .order_by(ScanRun.id.desc())
        .limit(1)
    )
