"""Pydantic response/request schemas for the API."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class LivenessResponse(BaseModel):
    status: str = "ok"
    service: str
    version: str
    environment: str
    time_utc: datetime = Field(description="Server time in UTC")


class ReadinessResponse(BaseModel):
    status: str
    database: str
    time_utc: datetime
