"""Public market-data read APIs."""

from __future__ import annotations

import math
from datetime import date, datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from backend.core.config import get_settings
from backend.db.models import IngestionJob, Instrument, MarketCandle
from backend.db.session import get_db
from backend.schemas.market_data import (
    AvwapPoint,
    AvwapResponse,
    CandleOut,
    CandlePage,
    FyersStatusOut,
    InstrumentOut,
    InstrumentPage,
    JobOut,
    MarketDataStatusOut,
)
from backend.services.analytics import AnalyticsService
from backend.services.fyers_status import FyersStatusService, get_fyers_status_service

router = APIRouter(prefix="/market-data", tags=["market-data"])


def _finite(value: object) -> float | None:
    try:
        number = float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def _instrument_or_404(db: Session, symbol: str) -> Instrument:
    instrument = db.scalar(
        select(Instrument).where(Instrument.fyers_symbol == symbol)
    )
    if instrument is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Instrument not found: {symbol}",
        )
    return instrument


@router.get("/status", response_model=MarketDataStatusOut, summary="Ingestion status")
def market_data_status(
    db: Session = Depends(get_db),
    fyers_service: FyersStatusService = Depends(get_fyers_status_service),
) -> MarketDataStatusOut:
    settings = get_settings()
    fyers = fyers_service.check()

    instruments_total = int(
        db.scalar(select(func.count()).select_from(Instrument)) or 0
    )
    instruments_active = int(
        db.scalar(
            select(func.count()).select_from(Instrument).where(Instrument.is_active)
        )
        or 0
    )
    candles_total = int(
        db.scalar(select(func.count()).select_from(MarketCandle)) or 0
    )
    latest_candle = db.scalar(select(func.max(MarketCandle.timestamp)))

    last_job = db.scalar(
        select(IngestionJob).order_by(IngestionJob.id.desc()).limit(1)
    )

    return MarketDataStatusOut(
        timeframe=settings.market_data_timeframe,
        instruments_total=instruments_total,
        instruments_active=instruments_active,
        candles_total=candles_total,
        latest_candle_at=latest_candle,
        fyers=FyersStatusOut(
            status=fyers.status,
            message=fyers.message,
            token_present=fyers.token_present,
            token_age_hours=fyers.token_age_hours,
            last_success_at=fyers.last_success_at,
            checked_at=fyers.checked_at,
        ),
        last_job=JobOut.model_validate(last_job) if last_job else None,
    )


@router.get(
    "/instruments",
    response_model=InstrumentPage,
    summary="List futures instruments",
)
def list_instruments(
    db: Session = Depends(get_db),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    active: bool | None = Query(None, description="Filter by active status"),
    underlying: str | None = Query(None, max_length=64),
    expiry: date | None = Query(None),
    q: str | None = Query(None, max_length=64),
) -> InstrumentPage:
    filters = []
    if active is not None:
        filters.append(Instrument.is_active == active)
    if underlying:
        filters.append(Instrument.underlying_symbol == underlying.upper())
    if expiry is not None:
        filters.append(Instrument.expiry_date == expiry)
    if q:
        pattern = f"%{q.strip().upper()}%"
        filters.append(
            or_(
                Instrument.fyers_symbol.ilike(pattern),
                Instrument.underlying_symbol.ilike(pattern),
            )
        )

    total = int(
        db.scalar(select(func.count()).select_from(Instrument).where(*filters))
        or 0
    )
    rows = db.scalars(
        select(Instrument)
        .where(*filters)
        .order_by(
            Instrument.underlying_symbol,
            Instrument.expiry_date,
            Instrument.fyers_symbol,
        )
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()

    return InstrumentPage(
        items=[InstrumentOut.model_validate(row) for row in rows],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get(
    "/instruments/{symbol}",
    response_model=InstrumentOut,
    summary="Get one futures instrument",
)
def get_instrument(symbol: str, db: Session = Depends(get_db)) -> InstrumentOut:
    return InstrumentOut.model_validate(_instrument_or_404(db, symbol))


@router.get(
    "/candles/{symbol}",
    response_model=CandlePage,
    summary="Stored 1-hour candles for a contract",
)
def get_candles(
    symbol: str,
    db: Session = Depends(get_db),
    timeframe: str | None = Query(None, max_length=8),
    limit: int = Query(500, ge=1, le=5000),
    offset: int = Query(0, ge=0),
    start: datetime | None = Query(None),
    end: datetime | None = Query(None),
) -> CandlePage:
    instrument = _instrument_or_404(db, symbol)
    resolution = timeframe or get_settings().market_data_timeframe

    filters = [
        MarketCandle.instrument_id == instrument.id,
        MarketCandle.timeframe == resolution,
    ]
    if start is not None:
        filters.append(MarketCandle.timestamp >= start)
    if end is not None:
        filters.append(MarketCandle.timestamp <= end)

    total = int(
        db.scalar(select(func.count()).select_from(MarketCandle).where(*filters))
        or 0
    )
    rows = db.scalars(
        select(MarketCandle)
        .where(*filters)
        .order_by(MarketCandle.timestamp)
        .offset(offset)
        .limit(limit)
    ).all()

    return CandlePage(
        symbol=instrument.fyers_symbol,
        timeframe=resolution,
        items=[
            CandleOut(
                timestamp=row.timestamp,
                open=float(row.open),
                high=float(row.high),
                low=float(row.low),
                close=float(row.close),
                volume=float(row.volume),
            )
            for row in rows
        ],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get(
    "/avwap/{symbol}",
    response_model=AvwapResponse,
    summary="Contract-start AVWAP series from stored candles",
)
def get_avwap(
    symbol: str,
    db: Session = Depends(get_db),
    timeframe: str | None = Query(None, max_length=8),
    limit: int = Query(200, ge=1, le=5000),
) -> AvwapResponse:
    instrument = _instrument_or_404(db, symbol)
    resolution = timeframe or get_settings().market_data_timeframe
    analytics = AnalyticsService()

    frame = analytics.load_full_frame(db, instrument.id, resolution)
    points: list[AvwapPoint] = []
    if not frame.empty:
        view = frame.tail(limit)
        for row in view.itertuples(index=False):
            points.append(
                AvwapPoint(
                    timestamp=row.timestamp.to_pydatetime(),
                    close=float(row.close),
                    avwap=_finite(row.avwap),
                    session_vwap=_finite(row.session_vwap),
                    atr=_finite(row.atr),
                )
            )

    anchor = None
    if not frame.empty:
        anchor = frame["timestamp"].iloc[0].to_pydatetime()

    return AvwapResponse(
        symbol=instrument.fyers_symbol,
        underlying_symbol=instrument.underlying_symbol,
        expiry_date=instrument.expiry_date,
        timeframe=resolution,
        anchor_timestamp=anchor,
        latest=points[-1] if points else None,
        points=points,
    )
