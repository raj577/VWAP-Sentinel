"""Market-data API schemas."""

from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field


class InstrumentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    fyers_symbol: str
    underlying_symbol: str
    exchange: str
    instrument_type: str
    expiry_date: date
    lot_size: float | None = None
    tick_size: float | None = None
    is_active: bool
    first_available_timestamp: datetime | None = None


class InstrumentPage(BaseModel):
    items: list[InstrumentOut]
    total: int
    page: int
    page_size: int


class CandleOut(BaseModel):
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float


class CandlePage(BaseModel):
    symbol: str
    timeframe: str
    items: list[CandleOut]
    total: int
    limit: int
    offset: int


class AvwapPoint(BaseModel):
    timestamp: datetime
    close: float
    avwap: float | None
    session_vwap: float | None
    atr: float | None


class AvwapResponse(BaseModel):
    symbol: str
    underlying_symbol: str
    expiry_date: date
    timeframe: str
    anchor_timestamp: datetime | None
    latest: AvwapPoint | None
    points: list[AvwapPoint]


class FyersStatusOut(BaseModel):
    status: str
    message: str
    token_present: bool
    token_age_hours: float | None
    last_success_at: datetime | None
    checked_at: datetime


class JobOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    job_type: str
    status: str
    started_at: datetime | None
    completed_at: datetime | None
    total_instruments: int
    successful_instruments: int
    failed_instruments: int
    candles_inserted: int
    candles_updated: int
    error_summary: str | None
    triggered_by: str


class JobItemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    symbol: str
    status: str
    candles_seen: int
    candles_inserted: int
    candles_updated: int
    error: str | None


class JobPage(BaseModel):
    items: list[JobOut]
    total: int
    page: int
    page_size: int


class JobDetail(JobOut):
    items: list[JobItemOut]


class MarketDataStatusOut(BaseModel):
    timeframe: str
    instruments_total: int
    instruments_active: int
    candles_total: int
    latest_candle_at: datetime | None
    fyers: FyersStatusOut
    last_job: JobOut | None


class IngestionSummaryOut(BaseModel):
    jobs_total: int
    completed_jobs: int
    failed_jobs: int
    last_completed_at: datetime | None
    last_success_at: datetime | None
    last_failed_instruments: list[str] = Field(default_factory=list)


class FyersLoginUrlOut(BaseModel):
    login_url: str
    redirect_uri: str
    state_expires_at: float


class ScanResultCandleOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float


class ScanResultOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    symbol: str
    expiry_date: date
    last_price: float
    avwap: float
    session_vwap: float | None
    distance_pct: float
    candle_count: int
    avg_body_ratio: float
    max_body_ratio: float
    classification: str
    detected_at: datetime
    pattern_start: datetime | None
    pattern_end: datetime | None
    latest_atr: float | None
    candles: list[ScanResultCandleOut] = Field(default_factory=list)


class ScanRunOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    scan_type: str
    status: str
    started_at: datetime | None
    completed_at: datetime | None
    instruments_scanned: int
    failed_instruments: int
    matches_count: int
    config_version: str
    data_freshness_at: datetime | None
    error_summary: str | None
    triggered_by: str


class ScanRunPage(BaseModel):
    items: list[ScanRunOut]
    total: int
    page: int
    page_size: int


class ScanRunDetail(ScanRunOut):
    results: list[ScanResultOut] = Field(default_factory=list)
