"""Synthetic, deterministic candle fixtures for unit tests only."""

from __future__ import annotations

from typing import Iterable

import pandas as pd

from indicators.atr import compute_atr
from indicators.avwap import compute_contract_avwap
from indicators.vwap import compute_session_vwap

TZ = "Asia/Kolkata"

BASELINE_CANDLE = {
    "open": 99.5,
    "high": 100.8,
    "low": 99.2,
    "close": 100.5,
    "volume": 1000.0,
}

SMALL_PATTERN_CANDLE = {
    "open": 100.05,
    "high": 100.30,
    "low": 99.90,
    "close": 100.10,
    "volume": 1000.0,
}


def make_frame(
    pattern_count: int = 0,
    pattern_candles: Iterable[dict[str, float]] | None = None,
    baseline_count: int = 40,
    now: pd.Timestamp | None = None,
) -> pd.DataFrame:
    """Build baseline candles followed by a small-candle pattern cluster."""
    patterns = list(pattern_candles) if pattern_candles is not None else [
        dict(SMALL_PATTERN_CANDLE) for _ in range(pattern_count)
    ]
    total = baseline_count + len(patterns)
    if now is None:
        now = pd.Timestamp.now(tz=TZ)
    last_complete = now.floor("h") - pd.Timedelta(hours=4)
    start = last_complete - pd.Timedelta(hours=total - 1)

    rows = []
    for offset in range(total):
        candle = dict(BASELINE_CANDLE) if offset < baseline_count else patterns[offset - baseline_count]
        rows.append(
            {
                "timestamp": start + pd.Timedelta(hours=offset),
                **candle,
            }
        )
    frame = pd.DataFrame(rows)
    frame["volume"] = frame["volume"].astype("float64")
    return frame


def add_indicators(frame: pd.DataFrame) -> pd.DataFrame:
    enriched = frame.copy()
    enriched["avwap"] = compute_contract_avwap(enriched)
    enriched["session_vwap"] = compute_session_vwap(enriched, TZ)
    enriched["atr"] = compute_atr(enriched, period=14)
    return enriched


def make_instrument(symbol: str = "NSE:TEST26NOVFUT", underlying: str = "TEST", expiry=None):
    from datetime import date, timedelta

    from scanner.models import Instrument

    return Instrument(
        symbol=symbol,
        underlying=underlying,
        expiry=expiry or (date.today() + timedelta(days=20)),
        description=f"{underlying} FUT",
        lot_size=1.0,
        is_index=False,
    )
