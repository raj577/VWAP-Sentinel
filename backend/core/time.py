"""Time helpers.

Rule: store timestamps in UTC, render them in Asia/Kolkata.
"""

from __future__ import annotations

from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from backend.core.config import get_settings


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def ensure_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        raise ValueError("Naive datetimes are not allowed; attach a timezone first")
    return value.astimezone(timezone.utc)


def to_display_timezone(value: datetime) -> datetime:
    return ensure_utc(value).astimezone(ZoneInfo(get_settings().timezone))
