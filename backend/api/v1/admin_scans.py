"""Admin scan execution and immutable scan history."""

from __future__ import annotations

import logging
from functools import lru_cache

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from backend.api.deps import require_admin_key
from backend.db.models import ScanResult, ScanRun
from backend.db.session import get_db, get_session_factory
from backend.schemas.market_data import (
    ScanResultOut,
    ScanRunDetail,
    ScanRunOut,
    ScanRunPage,
)
from backend.services.scanner import (
    ScanAlreadyRunning,
    ScanError,
    ScannerService,
)

logger = logging.getLogger("vwap_sentinel.scans")

router = APIRouter(
    prefix="/admin/scans",
    tags=["admin"],
    dependencies=[Depends(require_admin_key)],
)


@lru_cache(maxsize=1)
def get_scanner_service() -> ScannerService:
    return ScannerService(get_session_factory())


def _detail(db: Session, run_id: int) -> ScanRunDetail:
    run = db.scalar(
        select(ScanRun)
        .options(selectinload(ScanRun.results).selectinload(ScanResult.candles))
        .where(ScanRun.id == run_id)
    )
    if run is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Scan run not found: {run_id}",
        )
    return ScanRunDetail(
        **ScanRunOut.model_validate(run).model_dump(),
        results=[ScanResultOut.model_validate(item) for item in run.results],
    )


@router.post("/run", response_model=ScanRunDetail, summary="Run a scan now")
def run_scan(
    db: Session = Depends(get_db),
    service: ScannerService = Depends(get_scanner_service),
) -> ScanRunDetail:
    try:
        summary = service.run(triggered_by="admin", scan_type="MANUAL")
    except ScanAlreadyRunning as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail=str(exc)
        ) from exc
    except ScanError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)
        ) from exc
    return _detail(db, summary.scan_run_id)


@router.get("/latest", response_model=ScanRunDetail, summary="Latest completed scan")
def latest_scan(db: Session = Depends(get_db)) -> ScanRunDetail:
    run_id = db.scalar(
        select(ScanRun.id)
        .where(ScanRun.status == "COMPLETED")
        .order_by(ScanRun.id.desc())
        .limit(1)
    )
    if run_id is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No completed scan exists yet.",
        )
    return _detail(db, run_id)


@router.get("", response_model=ScanRunPage, summary="Scan run history")
def list_scans(
    db: Session = Depends(get_db),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
) -> ScanRunPage:
    total = int(db.scalar(select(func.count()).select_from(ScanRun)) or 0)
    rows = db.scalars(
        select(ScanRun)
        .order_by(ScanRun.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()
    return ScanRunPage(
        items=[ScanRunOut.model_validate(row) for row in rows],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/{run_id}", response_model=ScanRunDetail, summary="One scan run")
def get_scan(run_id: int, db: Session = Depends(get_db)) -> ScanRunDetail:
    return _detail(db, run_id)
