"""PostgreSQL-only integration check for the candle upsert path.

Skipped unless TEST_DATABASE_URL points at a migrated PostgreSQL database.
Rows created here are deleted again in ``finally``.
"""

from __future__ import annotations

import os
from datetime import date, timedelta

import pandas as pd
import pytest
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import sessionmaker

from backend.core.config import Settings
from backend.db.models import Instrument, MarketCandle
from backend.services.ingestion import MarketDataIngestionService

DATABASE_URL = os.getenv("TEST_DATABASE_URL")

pytestmark = pytest.mark.skipif(
    not DATABASE_URL, reason="TEST_DATABASE_URL is not configured"
)

SYMBOL = "NSE:PGCHECK26NOVFUT"


def _frame() -> pd.DataFrame:
    start = pd.Timestamp("2026-10-01 09:15", tz="Asia/Kolkata")
    timestamps = pd.date_range(start=start, periods=5, freq="h")
    return pd.DataFrame(
        {
            "timestamp": timestamps,
            "open": [100.0] * 5,
            "high": [100.5] * 5,
            "low": [99.5] * 5,
            "close": [100.2] * 5,
            "volume": [1000.0] * 5,
        }
    )


def test_postgres_upsert_is_idempotent() -> None:
    engine = create_engine(DATABASE_URL, connect_args={"connect_timeout": 5})
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    service = MarketDataIngestionService(
        factory,
        backend_settings=Settings(database_url=DATABASE_URL),
        instrument_source=lambda: pd.DataFrame(),
        candle_source=lambda instrument: pd.DataFrame(),
        timeframe="60",
    )

    session = factory()
    try:
        instrument = Instrument(
            fyers_symbol=SYMBOL,
            underlying_symbol="PGCHECK",
            expiry_date=date.today() + timedelta(days=20),
            is_active=True,
        )
        session.add(instrument)
        session.commit()
        session.refresh(instrument)

        candles = _frame()
        inserted, updated = service._upsert_candles(session, instrument.id, candles)
        session.commit()
        assert (inserted, updated) == (5, 0)

        inserted, updated = service._upsert_candles(session, instrument.id, candles)
        session.commit()
        assert (inserted, updated) == (0, 5)

        stored = session.scalar(
            select(func.count())
            .select_from(MarketCandle)
            .where(MarketCandle.instrument_id == instrument.id)
        )
        assert stored == 5
    finally:
        session.rollback()
        session.execute(
            MarketCandle.__table__.delete().where(
                MarketCandle.instrument_id.in_(
                    select(Instrument.id).where(Instrument.fyers_symbol == SYMBOL)
                )
            )
        )
        session.execute(
            Instrument.__table__.delete().where(Instrument.fyers_symbol == SYMBOL)
        )
        session.commit()
        session.close()
        engine.dispose()
