"""Read/update the singleton scheduler settings row."""

from __future__ import annotations

from datetime import datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.core.config import get_settings
from backend.db.models import SchedulerSettings
from backend.services.market_calendar import MarketCalendar, env_holidays, parse_holidays

SETTINGS_ID = 1


def get_scheduler_settings(db: Session) -> SchedulerSettings:
    row = db.get(SchedulerSettings, SETTINGS_ID)
    if row is not None:
        return row

    settings = get_settings()
    row = SchedulerSettings(
        id=SETTINGS_ID,
        scheduler_enabled=settings.scheduler_enabled,
        scan_interval_minutes=settings.scheduler_interval_minutes,
        market_open_time="09:15",
        market_close_time="15:30",
        timezone="Asia/Kolkata",
        allow_manual_outside_market_hours=True,
        market_holidays=env_holidays(),
        next_run_at=None,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def calendar_from_settings(row: SchedulerSettings) -> MarketCalendar:
    return MarketCalendar(
        timezone=row.timezone,
        open_time=row.market_open_time,
        close_time=row.market_close_time,
        holidays=frozenset(parse_holidays(row.market_holidays)),
    )


def compute_next_run(
    now: datetime, interval_minutes: int, enabled: bool
) -> datetime | None:
    if not enabled:
        return None
    return now + timedelta(minutes=max(int(interval_minutes), 1))


def initialize_next_run(db: Session, now: datetime) -> SchedulerSettings:
    row = get_scheduler_settings(db)
    if row.next_run_at is None:
        row.next_run_at = compute_next_run(
            now, row.scan_interval_minutes, row.scheduler_enabled
        )
        db.commit()
        db.refresh(row)
    return row


def reset_next_run(db: Session, row: SchedulerSettings, now: datetime) -> None:
    row.next_run_at = compute_next_run(
        now, row.scan_interval_minutes, row.scheduler_enabled
    )
    db.commit()
    db.refresh(row)


def find_settings(db: Session) -> SchedulerSettings | None:
    return db.scalar(select(SchedulerSettings).where(SchedulerSettings.id == SETTINGS_ID))
