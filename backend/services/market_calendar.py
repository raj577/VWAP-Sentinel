"""Asia/Kolkata trading calendar.

Holidays are configuration, never invented. The list comes from
``scheduler_settings.market_holidays`` (admin editable) with an optional
``MARKET_HOLIDAYS`` environment seed for first boot.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time
from zoneinfo import ZoneInfo

from backend.core.config import get_settings


def parse_hhmm(value: str) -> time:
    text = str(value).strip()
    try:
        hours, minutes = text.split(":")
        parsed = time(int(hours), int(minutes))
    except (ValueError, AttributeError) as exc:
        raise ValueError(f"Invalid HH:MM value: {value!r}") from exc
    if not (0 <= parsed.hour <= 23 and 0 <= parsed.minute <= 59):
        raise ValueError(f"Invalid HH:MM value: {value!r}")
    return parsed


def parse_holidays(values: list[str] | str | None) -> set[date]:
    if values is None:
        return set()
    if isinstance(values, str):
        raw = [part.strip() for part in values.split(",") if part.strip()]
    else:
        raw = [str(part).strip() for part in values if str(part).strip()]
    holidays: set[date] = set()
    for item in raw:
        try:
            holidays.add(date.fromisoformat(item))
        except ValueError as exc:
            raise ValueError(f"Invalid holiday date: {item!r}") from exc
    return holidays


def env_holidays() -> list[str]:
    raw = get_settings().market_holidays
    return [part.strip() for part in raw.split(",") if part.strip()]


@dataclass(frozen=True)
class MarketCalendar:
    timezone: str = "Asia/Kolkata"
    open_time: str = "09:15"
    close_time: str = "15:30"
    holidays: frozenset[date] = frozenset()

    def _tz(self) -> ZoneInfo:
        return ZoneInfo(self.timezone)

    def localize(self, value: datetime) -> datetime:
        if value.tzinfo is None:
            return value.replace(tzinfo=self._tz())
        return value.astimezone(self._tz())

    def is_trading_day(self, day: date) -> bool:
        return day.weekday() < 5 and day not in self.holidays

    def is_market_open(self, moment: datetime | None = None) -> bool:
        current = self.localize(moment or datetime.now(tz=self._tz()))
        if not self.is_trading_day(current.date()):
            return False
        opening = parse_hhmm(self.open_time)
        closing = parse_hhmm(self.close_time)
        return opening <= current.time().replace(tzinfo=None) <= closing

    def market_date(self, moment: datetime | None = None) -> date:
        return self.localize(moment or datetime.now(tz=self._tz())).date()
