"""Customer-facing scanner read APIs: current, history, results and charts."""

from __future__ import annotations

import math
from datetime import date, datetime

import pandas as pd
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from backend.api.deps import require_active_account
from backend.core.config import get_settings
from backend.db.models import Instrument, ScanResult, ScanRun

from backend.db.session import get_db
from backend.schemas.market_data import ScanResultOut, ScanRunDetail, ScanRunPage
from backend.schemas.scanner import (
    ChartPatternInfo,
    ChartPoint,
    ScanChartResponse,
    ScanComparisonOut,
    SymbolAppearanceOut,
    SymbolAppearancesOut,
)
from backend.services.analytics import AnalyticsService
from backend.services.scan_read import latest_completed_run_id, load_scan_detail
from data.historical_data import drop_incomplete_candles

router = APIRouter(
    prefix="/scanner",
    tags=["scanner"],
    dependencies=[Depends(require_active_account)],
)


def _detail_or_404(db: Session, run_id: int) -> ScanRunDetail:
    detail = load_scan_detail(db, run_id)
    if detail is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Scan run not found: {run_id}",
        )
    return detail


def _run_or_404(db: Session, run_id: int) -> ScanRun:
    run = db.get(ScanRun, run_id)
    if run is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Scan run not found: {run_id}",
        )
    return run


@router.get("/current", response_model=ScanRunDetail, summary="Latest completed scan")
def current_scan(db: Session = Depends(get_db)) -> ScanRunDetail:
    run_id = latest_completed_run_id(db)
    if run_id is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No completed scan exists yet.",
        )
    return _detail_or_404(db, run_id)


@router.get("/history", response_model=ScanRunPage, summary="Scan history")
def scan_history(
    db: Session = Depends(get_db),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    symbol: str | None = Query(None, max_length=64),
    classification: str | None = Query(None, max_length=32),
    min_distance: float | None = Query(None),
    max_distance: float | None = Query(None),
    expiry: date | None = Query(None),
    start: datetime | None = Query(None),
    end: datetime | None = Query(None),
) -> ScanRunPage:
    filters = [ScanRun.status == "COMPLETED"]
    if symbol:
        filters.append(ScanRun.results.any(ScanResult.symbol == symbol))
    if classification:
        filters.append(
            ScanRun.results.any(ScanResult.classification == classification)
        )
    if min_distance is not None:
        filters.append(
            ScanRun.results.any(ScanResult.distance_pct >= min_distance)
        )
    if max_distance is not None:
        filters.append(
            ScanRun.results.any(ScanResult.distance_pct <= max_distance)
        )
    if expiry is not None:
        filters.append(
            ScanRun.results.any(ScanResult.expiry_date == expiry)
        )
    if start is not None:
        filters.append(ScanRun.completed_at >= start)
    if end is not None:
        filters.append(ScanRun.completed_at <= end)

    total = int(
        db.scalar(select(func.count()).select_from(ScanRun).where(*filters)) or 0
    )
    rows = db.scalars(
        select(ScanRun)
        .where(*filters)
        .order_by(ScanRun.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()

    from backend.schemas.market_data import ScanRunOut

    return ScanRunPage(
        items=[ScanRunOut.model_validate(row) for row in rows],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get(
    "/history/{run_id}",
    response_model=ScanRunDetail,
    summary="One historical scan",
)
def historical_scan(run_id: int, db: Session = Depends(get_db)) -> ScanRunDetail:
    return _detail_or_404(db, run_id)


@router.get(
    "/results/{result_id}",
    response_model=ScanResultOut,
    summary="One scan result with preserved candles",
)
def scan_result(result_id: int, db: Session = Depends(get_db)) -> ScanResultOut:
    result = db.scalar(
        select(ScanResult)
        .options(selectinload(ScanResult.candles))
        .where(ScanResult.id == result_id)
    )
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Scan result not found: {result_id}",
        )
    return ScanResultOut.model_validate(result)


@router.get(
    "/chart/{symbol}",
    response_model=ScanChartResponse,
    summary="1-hour candles with AVWAP, VWAP and the latest pattern",
)
def scan_chart(
    symbol: str,
    db: Session = Depends(get_db),
    limit: int = Query(240, ge=20, le=1000),
) -> ScanChartResponse:
    instrument = db.scalar(
        select(Instrument).where(Instrument.fyers_symbol == symbol)
    )
    if instrument is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Instrument not found: {symbol}",
        )

    analytics = AnalyticsService()
    timeframe = get_settings().market_data_timeframe

    candles = analytics.load_candles(db, instrument.id, timeframe)
    frame = analytics.frame_from_candles(candles)

    if frame.empty:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No candles stored for {symbol}.",
        )
    frame = drop_incomplete_candles(
        frame,
        timeframe,
        now=pd.Timestamp.now(tz=analytics.timezone),
        timezone=analytics.timezone,
    )
    if frame.empty:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No completed candles stored for {symbol}.",
        )
    frame = analytics.compute(frame).tail(limit)

    latest = db.execute(
        select(ScanResult, ScanRun)
        .join(ScanRun, ScanRun.id == ScanResult.scan_run_id)
        .where(
            ScanResult.symbol == symbol,
            ScanRun.status == "COMPLETED",
        )
        .order_by(ScanRun.id.desc())
        .limit(1)
    ).first()

    points: list[ChartPoint] = []
    for row in frame.itertuples(index=False):
        points.append(
            ChartPoint(
                timestamp=row.timestamp.tz_convert("UTC").to_pydatetime(),
                open=float(row.open),
                high=float(row.high),
                low=float(row.low),
                close=float(row.close),
                volume=float(row.volume),
                avwap=_finite(row.avwap),
                session_vwap=_finite(row.session_vwap),
            )
        )

    pattern = None
    scan_completed_at = None
    scan_run_id = None
    if latest is not None:
        result, run = latest
        scan_run_id = run.id
        scan_completed_at = run.completed_at
        pattern = ChartPatternInfo(
            scan_run_id=run.id,
            classification=result.classification,
            detected_at=result.detected_at,
            candle_count=result.candle_count,
            distance_pct=float(result.distance_pct),
            pattern_start=result.pattern_start,
            pattern_end=result.pattern_end,
        )

    return ScanChartResponse(
        symbol=instrument.fyers_symbol,
        underlying_symbol=instrument.underlying_symbol,
        expiry_date=instrument.expiry_date,
        timeframe=timeframe,
        scan_run_id=scan_run_id,
        scan_completed_at=scan_completed_at,
        pattern=pattern,
        points=points,
    )


def _finite(value: object) -> float | None:
    try:
        number = float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


@router.get(
    "/comparison",
    response_model=ScanComparisonOut,
    summary="Compare two scan runs by symbol membership",
)
def compare_scans(
    base_run_id: int = Query(..., ge=1),
    compare_run_id: int = Query(..., ge=1),
    db: Session = Depends(get_db),
) -> ScanComparisonOut:
    _run_or_404(db, base_run_id)
    _run_or_404(db, compare_run_id)

    base = set(
        db.scalars(
            select(ScanResult.symbol).where(ScanResult.scan_run_id == base_run_id)
        )
    )
    compare = set(
        db.scalars(
            select(ScanResult.symbol).where(ScanResult.scan_run_id == compare_run_id)
        )
    )
    return ScanComparisonOut(
        base_run_id=base_run_id,
        compare_run_id=compare_run_id,
        appeared=sorted(compare - base),
        disappeared=sorted(base - compare),
        persisted=sorted(base & compare),
    )


@router.get(
    "/symbols/{symbol}/appearances",
    response_model=SymbolAppearancesOut,
    summary="First and latest appearance of a symbol across scans",
)
def symbol_appearances(
    symbol: str, db: Session = Depends(get_db)
) -> SymbolAppearancesOut:
    rows = db.execute(
        select(ScanResult, ScanRun.completed_at)
        .join(ScanRun, ScanRun.id == ScanResult.scan_run_id)
        .where(
            ScanResult.symbol == symbol,
            ScanRun.status == "COMPLETED",
        )
        .order_by(ScanRun.id)
    ).all()
    if not rows:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No scan appearances for {symbol}.",
        )

    appearances = [
        SymbolAppearanceOut(
            scan_run_id=result.scan_run_id,
            completed_at=completed_at,
            classification=result.classification,
            distance_pct=float(result.distance_pct),
        )
        for result, completed_at in rows
    ]
    return SymbolAppearancesOut(
        symbol=symbol,
        first_seen_at=appearances[0].completed_at,
        latest_seen_at=appearances[-1].completed_at,
        appearances=appearances,
    )
