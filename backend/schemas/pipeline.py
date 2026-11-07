"""Schemas for scheduler control, pipeline jobs and logs."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from backend.schemas.market_data import ScanRunOut
from backend.services.market_calendar import parse_holidays, parse_hhmm


class SchedulerSettingsOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    scheduler_enabled: bool
    scan_interval_minutes: int
    market_open_time: str
    market_close_time: str
    timezone: str
    allow_manual_outside_market_hours: bool
    market_holidays: list[str]
    last_run_at: datetime | None
    next_run_at: datetime | None
    updated_by: str | None
    updated_at: datetime


class SchedulerSettingsPatch(BaseModel):
    scheduler_enabled: bool | None = None
    scan_interval_minutes: int | None = Field(default=None, ge=1, le=1440)
    market_open_time: str | None = None
    market_close_time: str | None = None
    timezone: str | None = Field(default=None, max_length=64)
    allow_manual_outside_market_hours: bool | None = None
    market_holidays: list[str] | None = None

    @field_validator("market_open_time", "market_close_time")
    @classmethod
    def _valid_time(cls, value: str | None) -> str | None:
        if value is not None:
            parse_hhmm(value)
        return value

    @field_validator("market_holidays")
    @classmethod
    def _valid_holidays(cls, value: list[str] | None) -> list[str] | None:
        if value is not None:
            parse_holidays(value)
        return value


class PipelineJobOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    job_type: str
    trigger_source: str
    status: str
    stage: str | None
    started_at: datetime | None
    completed_at: datetime | None
    duration_seconds: float | None
    total_instruments: int
    processed_instruments: int
    failed_instruments: int
    candles_fetched: int
    candles_inserted: int
    candles_updated: int
    error_summary: str | None
    cancellation_requested_at: datetime | None
    ingestion_job_id: int | None
    scan_run_id: int | None
    created_at: datetime


class PipelineJobLogOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    job_id: int
    symbol: str
    status: str
    candles_processed: int
    error_message: str | None
    started_at: datetime | None
    completed_at: datetime | None


class PipelineJobPage(BaseModel):
    items: list[PipelineJobOut]
    total: int
    page: int
    page_size: int


class PipelineLogPage(BaseModel):
    items: list[PipelineJobLogOut]
    total: int
    page: int
    page_size: int


class SchedulerStatusOut(BaseModel):
    settings: SchedulerSettingsOut
    market_open: bool
    server_time: datetime
    active_job: PipelineJobOut | None
    last_scan_run: ScanRunOut | None
    data_freshness_at: datetime | None


class PipelineSummaryOut(BaseModel):
    counts: dict[str, int]
    total_jobs: int
    active_job: PipelineJobOut | None
    last_completed_at: datetime | None
    last_failed_at: datetime | None
    last_scan_run_id: int | None
    data_freshness_at: datetime | None


class RunScannerRequest(BaseModel):
    confirm_stale: bool = Field(
        default=False,
        description="Allow scanning when stored candles are older than the freshness threshold.",
    )


class CancelJobRequest(BaseModel):
    reason: str | None = Field(default=None, max_length=500)
