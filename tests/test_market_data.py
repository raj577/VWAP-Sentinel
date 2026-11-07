"""Phase 2 tests: ingestion, candle storage, AVWAP isolation and APIs.

All FYERS interaction is faked. No network calls are made.
"""

from __future__ import annotations

from collections.abc import Iterator
from datetime import timedelta


import pandas as pd
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session, sessionmaker


from backend.core.config import Settings, get_settings
from backend.db.base import Base
from backend.db.models import IngestionJob, Instrument, MarketCandle
from backend.db.session import get_db
from backend.main import app
from backend.services.analytics import AnalyticsService
from backend.services.fyers_status import (
    STATUS_CONNECTED,
    FyersStatus,
    get_fyers_status_service,
)
from backend.services.ingestion import (
    STATUS_COMPLETED,
    STATUS_PARTIALLY_COMPLETED,
    MarketDataIngestionService,
    clean_candles,
)
from backend.core.time import utcnow

IST = "Asia/Kolkata"


def _master_frame() -> pd.DataFrame:
    today = pd.Timestamp.now(tz=IST).date()
    rows = [
        {
            "symbol": "NSE:AAA26NOVFUT",
            "underlying": "AAA",
            "expiry": today + timedelta(days=20),
            "lot_size": 1000.0,
            "tick_size": 0.05,
            "is_index": False,
        },
        {
            "symbol": "NSE:AAA26DECFUT",
            "underlying": "AAA",
            "expiry": today + timedelta(days=50),
            "lot_size": 1000.0,
            "tick_size": 0.05,
            "is_index": False,
        },
        {
            "symbol": "NSE:EXPIRED26JANFUT",
            "underlying": "EXPIRED",
            "expiry": today - timedelta(days=10),
            "lot_size": 500.0,
            "tick_size": 0.05,
            "is_index": False,
        },
        {
            "symbol": "NSE:NIFTY26NOVFUT",
            "underlying": "NIFTY",
            "expiry": today + timedelta(days=20),
            "lot_size": 75.0,
            "tick_size": 0.05,
            "is_index": True,
        },
    ]
    frame = pd.DataFrame(rows)
    frame["expiry"] = pd.to_datetime(frame["expiry"]).dt.date
    return frame


def _candles(base_price: float, count: int = 40) -> pd.DataFrame:
    start = pd.Timestamp("2026-10-01 09:15", tz=IST)
    timestamps = pd.date_range(start=start, periods=count, freq="h")
    rows = []
    for index, stamp in enumerate(timestamps):
        price = base_price + index * 0.1
        rows.append(
            {
                "timestamp": stamp,
                "open": price,
                "high": price + 0.5,
                "low": price - 0.5,
                "close": price + 0.2,
                "volume": 1000.0 + index,
            }
        )
    return pd.DataFrame(rows)


def _session_factory(tmp_path) -> sessionmaker[Session]:
    engine = create_engine(
        f"sqlite+pysqlite:///{tmp_path / 'phase2.db'}",
        connect_args={"check_same_thread": False},
    )
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def _service(factory, candle_source) -> MarketDataIngestionService:
    return MarketDataIngestionService(
        factory,
        backend_settings=Settings(database_url="sqlite+pysqlite://"),
        legacy_settings=None,
        instrument_source=_master_frame,
        candle_source=candle_source,
        clock=utcnow,
        timeframe="60",
    )


def test_clean_candles_dedupes_and_removes_invalid_rows() -> None:
    frame = _candles(100.0, count=3)
    duplicate = frame.iloc[[1]].copy()
    duplicate["close"] = 999.0
    bad = frame.iloc[[2]].copy()
    bad["high"] = bad["low"] - 1.0
    merged = pd.concat([frame, duplicate, bad], ignore_index=True)

    cleaned = clean_candles(merged)

    assert len(cleaned) == 3
    assert cleaned["timestamp"].is_monotonic_increasing
    middle = cleaned.iloc[1]
    assert middle["close"] == pytest.approx(999.0)


def test_ingestion_stores_candles_and_is_idempotent(tmp_path) -> None:
    factory = _session_factory(tmp_path)
    source = {
        "NSE:AAA26NOVFUT": _candles(100.0),
        "NSE:AAA26DECFUT": _candles(200.0),
    }
    service = _service(factory, lambda instrument: source[instrument.symbol])

    first = service.run(triggered_by="test")
    assert first.status == STATUS_COMPLETED
    assert first.total_instruments == 2
    assert first.successful_instruments == 2
    assert first.candles_inserted == 80
    assert first.candles_updated == 0

    second = service.run(triggered_by="test")
    assert second.status == STATUS_COMPLETED
    assert second.candles_inserted == 0
    assert second.candles_updated == 80

    with factory() as db:
        assert db.scalar(select(func.count()).select_from(Instrument)) == 2
        assert db.scalar(select(func.count()).select_from(MarketCandle)) == 80
        assert db.scalar(select(func.count()).select_from(IngestionJob)) == 2


def test_expired_and_index_contracts_are_excluded(tmp_path) -> None:
    factory = _session_factory(tmp_path)
    service = _service(
        factory,
        lambda instrument: _candles(100.0),
    )
    service.run(triggered_by="test")

    with factory() as db:
        symbols = set(db.scalars(select(Instrument.fyers_symbol)))
    assert symbols == {"NSE:AAA26NOVFUT", "NSE:AAA26DECFUT"}


def test_failed_instrument_does_not_abort_job(tmp_path) -> None:
    factory = _session_factory(tmp_path)

    def candle_source(instrument):
        if instrument.symbol == "NSE:AAA26DECFUT":
            raise RuntimeError("provider exploded")
        return _candles(100.0)

    result = _service(factory, candle_source).run(triggered_by="test")

    assert result.status == STATUS_PARTIALLY_COMPLETED
    assert result.successful_instruments == 1
    assert result.failed_instruments == 1
    assert "provider exploded" in (result.error_summary or "")

    with factory() as db:
        assert db.scalar(select(func.count()).select_from(MarketCandle)) == 40
        job = db.scalar(select(IngestionJob).order_by(IngestionJob.id))
        assert job.status == STATUS_PARTIALLY_COMPLETED


def test_contract_start_avwap_is_isolated_per_expiry(tmp_path) -> None:
    factory = _session_factory(tmp_path)
    source = {
        "NSE:AAA26NOVFUT": _candles(100.0),
        "NSE:AAA26DECFUT": _candles(500.0),
    }
    _service(factory, lambda instrument: source[instrument.symbol]).run(
        triggered_by="test"
    )

    analytics = AnalyticsService(timezone=IST)
    with factory() as db:
        instruments = {
            row.fyers_symbol: row.id
            for row in db.scalars(select(Instrument))
        }
        first = analytics.load_full_frame(db, instruments["NSE:AAA26NOVFUT"], "60")
        second = analytics.load_full_frame(db, instruments["NSE:AAA26DECFUT"], "60")

    assert first["avwap"].iloc[0] < 200
    assert second["avwap"].iloc[0] > 400
    assert first["avwap"].iloc[-1] < second["avwap"].iloc[-1]
    # AVWAP must never reset: it is cumulative from the first contract candle.
    assert first["avwap"].iloc[0] == pytest.approx(
        (first["high"].iloc[0] + first["low"].iloc[0] + first["close"].iloc[0]) / 3.0
    )


def test_zero_volume_candle_yields_nan_avwap(tmp_path) -> None:
    factory = _session_factory(tmp_path)
    frame = _candles(100.0, count=3)
    frame.loc[:, "volume"] = 0.0
    _service(factory, lambda instrument: frame).run(triggered_by="test")

    analytics = AnalyticsService(timezone=IST)
    with factory() as db:
        instrument = db.scalar(select(Instrument))
        computed = analytics.load_full_frame(db, instrument.id, "60")
    assert computed["avwap"].isna().all()
    assert computed["session_vwap"].isna().all()


# --------------------------------------------------------------------- API
class _FakeFyersStatus:
    def check(self, force: bool = False) -> FyersStatus:
        now = utcnow()
        return FyersStatus(
            status=STATUS_CONNECTED,
            message="FYERS connection is healthy.",
            token_present=True,
            token_age_hours=1.5,
            last_success_at=now,
            checked_at=now,
        )


@pytest.fixture()
def api_client(tmp_path, monkeypatch) -> Iterator[TestClient]:
    factory = _session_factory(tmp_path)
    source = {
        "NSE:AAA26NOVFUT": _candles(100.0),
        "NSE:AAA26DECFUT": _candles(500.0),
    }
    _service(factory, lambda instrument: source[instrument.symbol]).run(
        triggered_by="test"
    )

    def override_get_db() -> Iterator[Session]:
        session = factory()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_fyers_status_service] = lambda: _FakeFyersStatus()

    monkeypatch.setenv("ADMIN_API_KEY", "test-admin-key")
    get_settings.cache_clear()
    with TestClient(app) as client:
        yield client
    app.dependency_overrides.clear()
    get_settings.cache_clear()


def test_status_endpoint_reports_counts_and_fyers(api_client: TestClient) -> None:
    response = api_client.get("/api/v1/market-data/status")
    assert response.status_code == 200
    body = response.json()
    assert body["instruments_total"] == 2
    assert body["instruments_active"] == 2
    assert body["candles_total"] == 80
    assert body["fyers"]["status"] == "CONNECTED"
    assert body["last_job"]["status"] == "COMPLETED"


def test_instrument_list_and_detail(api_client: TestClient) -> None:
    listing = api_client.get(
        "/api/v1/market-data/instruments",
        params={"page": 1, "page_size": 1, "underlying": "aaa"},
    )
    assert listing.status_code == 200
    body = listing.json()
    assert body["total"] == 2
    assert len(body["items"]) == 1

    symbol = body["items"][0]["fyers_symbol"]
    detail = api_client.get(f"/api/v1/market-data/instruments/{symbol}")
    assert detail.status_code == 200
    assert detail.json()["fyers_symbol"] == symbol

    missing = api_client.get("/api/v1/market-data/instruments/NSE:NOPE")
    assert missing.status_code == 404


def test_candles_endpoint_is_paginated_and_ordered(api_client: TestClient) -> None:
    response = api_client.get(
        "/api/v1/market-data/candles/NSE:AAA26NOVFUT",
        params={"limit": 10, "offset": 0},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 40
    assert len(body["items"]) == 10
    timestamps = [item["timestamp"] for item in body["items"]]
    assert timestamps == sorted(timestamps)


def test_avwap_endpoint_returns_series(api_client: TestClient) -> None:
    response = api_client.get(
        "/api/v1/market-data/avwap/NSE:AAA26DECFUT", params={"limit": 5}
    )
    assert response.status_code == 200
    body = response.json()
    assert len(body["points"]) == 5
    assert body["anchor_timestamp"]
    assert body["latest"]["avwap"] is not None
    assert body["latest"]["avwap"] > 400


def test_admin_endpoints_require_key(api_client: TestClient) -> None:
    denied = api_client.get("/api/v1/admin/market-data/jobs")
    assert denied.status_code == 401

    allowed = api_client.get(
        "/api/v1/admin/market-data/jobs",
        headers={"X-Admin-Key": "test-admin-key"},
    )
    assert allowed.status_code == 200
    assert allowed.json()["total"] == 1

    summary = api_client.get(
        "/api/v1/admin/market-data/ingestion-summary",
        headers={"X-Admin-Key": "test-admin-key"},
    )
    assert summary.status_code == 200
    assert summary.json()["completed_jobs"] == 1

    job_id = allowed.json()["items"][0]["id"]
    detail = api_client.get(
        f"/api/v1/admin/market-data/jobs/{job_id}",
        headers={"X-Admin-Key": "test-admin-key"},
    )
    assert detail.status_code == 200
    assert len(detail.json()["items"]) == 2
