"""AVWAP / session VWAP calculation over stored candles.

Reuses the legacy indicator implementations so the SaaS and the Streamlit app
can never drift apart.
"""

from __future__ import annotations

from collections.abc import Sequence

import pandas as pd
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.core.config import get_settings
from backend.db.models import MarketCandle
from indicators.atr import compute_atr
from indicators.avwap import compute_contract_avwap
from indicators.vwap import compute_session_vwap

OHLCV_COLUMNS = ["timestamp", "open", "high", "low", "close", "volume"]


class AnalyticsService:
    def __init__(self, timezone: str | None = None) -> None:
        self.timezone = timezone or get_settings().timezone

    def frame_from_candles(
        self, candles: Sequence[MarketCandle]
    ) -> pd.DataFrame:
        rows = [
            {
                "timestamp": candle.timestamp,
                "open": float(candle.open),
                "high": float(candle.high),
                "low": float(candle.low),
                "close": float(candle.close),
                "volume": float(candle.volume),
            }
            for candle in candles
        ]
        frame = pd.DataFrame(rows, columns=OHLCV_COLUMNS)
        if frame.empty:
            return frame
        frame["timestamp"] = pd.to_datetime(
            frame["timestamp"], utc=True, errors="coerce"
        ).dt.tz_convert(self.timezone)
        frame = frame.dropna(subset=["timestamp"]).sort_values("timestamp")
        return frame.reset_index(drop=True)

    def compute(self, frame: pd.DataFrame) -> pd.DataFrame:
        """Attach contract-start AVWAP, session VWAP and ATR columns."""

        if frame.empty:
            return frame.copy()
        enriched = frame.copy()
        enriched["avwap"] = compute_contract_avwap(enriched, anchor_index=0)
        enriched["session_vwap"] = compute_session_vwap(enriched, self.timezone)
        enriched["atr"] = compute_atr(enriched, period=14)
        return enriched

    def load_candles(
        self,
        db: Session,
        instrument_id: int,
        timeframe: str,
        limit: int | None = None,
    ) -> list[MarketCandle]:
        statement = (
            select(MarketCandle)
            .where(
                MarketCandle.instrument_id == instrument_id,
                MarketCandle.timeframe == timeframe,
            )
            .order_by(MarketCandle.timestamp.desc())
        )
        if limit is not None:
            statement = statement.limit(limit)
        rows = list(db.scalars(statement))
        rows.reverse()
        return rows

    def load_full_frame(
        self, db: Session, instrument_id: int, timeframe: str
    ) -> pd.DataFrame:
        """Load the whole contract history so the AVWAP anchor is correct."""

        candles = self.load_candles(db, instrument_id, timeframe)
        return self.compute(self.frame_from_candles(candles))
