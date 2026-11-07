"""Schemas for the customer-facing scanner APIs."""

from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field


class ChartPoint(BaseModel):
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float
    avwap: float | None
    session_vwap: float | None


class ChartPatternInfo(BaseModel):
    scan_run_id: int
    classification: str
    detected_at: datetime
    candle_count: int
    distance_pct: float
    pattern_start: datetime | None
    pattern_end: datetime | None


class ScanChartResponse(BaseModel):
    symbol: str
    underlying_symbol: str
    expiry_date: date
    timeframe: str
    scan_run_id: int | None
    scan_completed_at: datetime | None
    pattern: ChartPatternInfo | None
    points: list[ChartPoint]


class ScanComparisonOut(BaseModel):
    base_run_id: int
    compare_run_id: int
    appeared: list[str] = Field(default_factory=list)
    disappeared: list[str] = Field(default_factory=list)
    persisted: list[str] = Field(default_factory=list)


class SymbolAppearanceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    scan_run_id: int
    completed_at: datetime | None
    classification: str
    distance_pct: float


class SymbolAppearancesOut(BaseModel):
    symbol: str
    first_seen_at: datetime | None
    latest_seen_at: datetime | None
    appearances: list[SymbolAppearanceOut]
