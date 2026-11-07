"""Tests for immutable scan runs and the admin scan APIs."""

from __future__ import annotations

from collections.abc import Iterator
from datetime import date, timedelta

import pandas as pd
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session, sessionmaker

from backend.core.config import Settings, get_settings
from backend.db.base import Base
from backend.db.models import MarketCandle, ScanResult, ScanResultCandle, ScanRun
from backend.db.session import get_db
from backend.api.v1.admin_scans import get_scanner_service
from backend.main import app
from backend.services.scanner import ScannerService
from tests.helpers import make_frame

IST = "Asia/Kolkata"


def _factory(tmp_path) -> sessionmaker[Session]:
    engine = create_engine(
        f"sqlite+pysqlite:///{tmp_path / 'scans.db'}",
        connect_args={"check_same_thread": False},
    )
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def _seed(
    factory: sessionmaker[Session],
    symbol: str,
    frame: pd.DataFrame,
) -> int:
    with factory() as db:
        from backend.db.models import Instrument

        instrument = Instrument(
            fyers_symbol=symbol,
            underlying_symbol=symbol.split(":")[1][:3],
            expiry_date=date.today() + timedelta(days=20),
            is_active=True,
        )
        db.add(instrument)
        db.flush()
        for row in frame.itertuples(index=False):
            timestamp = pd.Timestamp(row.timestamp)
            if timestamp.tzinfo is None:
                timestamp = timestamp.tz_localize(IST)
            db.add(
                MarketCandle(
                    instrument_id=instrument.id,
                    timeframe="60",
                    timestamp=timestamp.tz_convert("UTC").to_pydatetime(),
                    open=float(row.open),
                    high=float(row.high),
                    low=float(row.low),
                    close=float(row.close),
                    volume=float(row.volume),
                )
            )
        db.commit()
        return instrument.id


def _matching_frame() -> pd.DataFrame:
    return make_frame(pattern_count=2)


def _non_matching_frame() -> pd.DataFrame:
    far = {
        "open": 110.0,
        "high": 110.4,
        "low": 109.6,
        "close": 110.2,
        "volume": 1000.0,
    }
    return make_frame(pattern_candles=[far])


def test_scan_creates_immutable_snapshot(tmp_path) -> None:
    factory = _factory(tmp_path)
    _seed(factory, "NSE:AAA26NOVFUT", _matching_frame())
    _seed(factory, "NSE:BBB26NOVFUT", _non_matching_frame())

    service = ScannerService(factory, backend_settings=Settings())
    first = service.run(triggered_by="test")

    assert first.status == "COMPLETED"
    assert first.instruments_scanned == 2
    assert first.matches_count == 1

    with factory() as db:
        run = db.get(ScanRun, first.scan_run_id)
        assert run is not None
        assert run.matches_count == 1
        assert run.data_freshness_at is not None

        result = db.scalar(
            select(ScanResult).where(ScanResult.scan_run_id == run.id)
        )
        assert result is not None
        assert result.avwap > 0
        assert result.classification.startswith("AVWAP")
        assert result.candle_count >= 1

        preserved = db.scalar(
            select(func.count())
            .select_from(ScanResultCandle)
            .where(ScanResultCandle.scan_result_id == result.id)
        )
        assert preserved == result.candle_count

        first_result_id = result.id

    second = service.run(triggered_by="test")
    assert second.scan_run_id > first.scan_run_id
    assert second.matches_count == 1

    with factory() as db:
        assert db.get(ScanResult, first_result_id) is not None
        first_run_results = db.scalar(
            select(func.count())
            .select_from(ScanResult)
            .where(ScanResult.scan_run_id == first.scan_run_id)
        )
        assert first_run_results == 1


def test_scan_with_no_instruments_completes_empty(tmp_path) -> None:
    summary = ScannerService(
        _factory(tmp_path), backend_settings=Settings()
    ).run(triggered_by="test")
    assert summary.status == "COMPLETED"
    assert summary.instruments_scanned == 0
    assert summary.matches_count == 0


@pytest.fixture()
def client(tmp_path, monkeypatch) -> Iterator[TestClient]:
    factory = _factory(tmp_path)
    _seed(factory, "NSE:AAA26NOVFUT", _matching_frame())

    service = ScannerService(factory, backend_settings=Settings())

    def override_get_db() -> Iterator[Session]:
        session = factory()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_scanner_service] = lambda: service
    monkeypatch.setenv("ADMIN_API_KEY", "test-admin-key")
    get_settings.cache_clear()

    from backend.core.time import utcnow
    from backend.db.models import Role, User, UserRole
    from backend.services.security import (
        STATUS_ACTIVE,
        create_access_token,
        hash_password,
    )

    with factory() as db:
        role = db.scalar(select(Role).where(Role.name == "CUSTOMER"))
        if role is None:
            role = Role(name="CUSTOMER")
            db.add(role)
            db.flush()
        user = User(
            full_name="Scanner Test",
            email="scanner-tests@example.com",
            password_hash=hash_password("Scanner!Pass123"),
            account_status=STATUS_ACTIVE,
            email_verified_at=utcnow(),
        )
        db.add(user)
        db.flush()
        db.add(UserRole(user_id=user.id, role_id=role.id))
        db.commit()
        token, _ = create_access_token(user.id)

    with TestClient(app) as test_client:
        test_client.headers.update({"Authorization": f"Bearer {token}"})
        yield test_client

    app.dependency_overrides.clear()
    get_settings.cache_clear()


def test_admin_can_run_and_read_scans(client: TestClient) -> None:
    headers = {"X-Admin-Key": "test-admin-key"}

    denied = client.post("/api/v1/admin/scans/run")
    assert denied.status_code in {401, 403}

    created = client.post("/api/v1/admin/scans/run", headers=headers)
    assert created.status_code == 200
    body = created.json()
    run_id = body["id"]
    assert body["status"] == "COMPLETED"
    assert body["instruments_scanned"] == 1
    assert body["matches_count"] == 1
    assert len(body["results"]) == 1
    assert body["results"][0]["classification"].startswith("AVWAP")
    assert body["results"][0]["candles"]

    latest = client.get("/api/v1/admin/scans/latest", headers=headers)
    assert latest.status_code == 200
    assert latest.json()["id"] == run_id

    history = client.get("/api/v1/admin/scans", headers=headers)
    assert history.status_code == 200
    assert history.json()["total"] == 1

    detail = client.get(f"/api/v1/admin/scans/{run_id}", headers=headers)
    assert detail.status_code == 200
    assert detail.json()["results"][0]["symbol"] == "NSE:AAA26NOVFUT"

    missing = client.get("/api/v1/admin/scans/9999", headers=headers)
    assert missing.status_code == 404


def test_second_scan_appends_without_mutating_first(client: TestClient) -> None:
    headers = {"X-Admin-Key": "test-admin-key"}
    first = client.post("/api/v1/admin/scans/run", headers=headers).json()
    second = client.post("/api/v1/admin/scans/run", headers=headers).json()

    assert first["id"] != second["id"]
    first_again = client.get(
        f"/api/v1/admin/scans/{first['id']}", headers=headers
    ).json()
    assert first_again["matches_count"] == first["matches_count"]
    assert len(first_again["results"]) == len(first["results"])


def test_scanner_service_rejects_concurrent_runs_on_same_lock(tmp_path) -> None:
    """SQLite has no advisory lock, but a PostgreSQL lock is exercised in integration."""

    factory = _factory(tmp_path)
    service = ScannerService(factory, backend_settings=Settings())
    assert service.run(triggered_by="test").status == "COMPLETED"

@pytest.mark.parametrize("count", [1, 2, 3, 4, 5])
def test_scanner_detects_one_to_five_candles(tmp_path, count) -> None:
    factory = _factory(tmp_path)
    _seed(factory, "NSE:AAA26NOVFUT", make_frame(pattern_count=count))

    summary = ScannerService(factory, backend_settings=Settings()).run(
        triggered_by="test"
    )
    assert summary.matches_count == 1
    assert summary.failed_instruments == 0

    with factory() as db:
        result = db.scalar(select(ScanResult))
        assert result is not None
        assert result.candle_count == count


def test_missing_candles_are_counted_as_failed(tmp_path) -> None:
    factory = _factory(tmp_path)
    with factory() as db:
        from backend.db.models import Instrument

        db.add(
            Instrument(
                fyers_symbol="NSE:NOCANDLES26NOVFUT",
                underlying_symbol="NOCANDLES",
                expiry_date=date.today() + timedelta(days=20),
                is_active=True,
            )
        )
        db.commit()

    summary = ScannerService(factory, backend_settings=Settings()).run(
        triggered_by="test"
    )
    assert summary.instruments_scanned == 1
    assert summary.failed_instruments == 1
    assert summary.matches_count == 0

    with factory() as db:
        run = db.get(ScanRun, summary.scan_run_id)
        assert run is not None
        assert run.error_summary


def test_forming_candle_is_excluded(tmp_path) -> None:
    factory = _factory(tmp_path)
    forming = pd.DataFrame(
        {
            "timestamp": [pd.Timestamp.now(tz=IST).normalize() + pd.Timedelta(days=1, hours=10)],
            "open": [100.0],
            "high": [100.5],
            "low": [99.5],
            "close": [100.1],
            "volume": [1000.0],
        }
    )
    _seed(factory, "NSE:FORMING26NOVFUT", forming)

    summary = ScannerService(factory, backend_settings=Settings()).run(
        triggered_by="test"
    )
    assert summary.failed_instruments == 1
    assert summary.matches_count == 0


def test_public_scanner_endpoints(client: TestClient) -> None:
    headers = {"X-Admin-Key": "test-admin-key"}
    first = client.post("/api/v1/admin/scans/run", headers=headers).json()
    second = client.post("/api/v1/admin/scans/run", headers=headers).json()

    current = client.get("/api/v1/scanner/current")
    assert current.status_code == 200
    assert current.json()["id"] == second["id"]

    history = client.get("/api/v1/scanner/history")
    assert history.status_code == 200
    assert history.json()["total"] == 2

    filtered = client.get(
        "/api/v1/scanner/history",
        params={
            "symbol": "NSE:AAA26NOVFUT",
            "classification": current.json()["results"][0]["classification"],
            "min_distance": -100,
            "max_distance": 100,
        },
    )
    assert filtered.status_code == 200
    assert filtered.json()["total"] == 2

    empty = client.get(
        "/api/v1/scanner/history", params={"symbol": "NSE:ZZZNOPE"}
    )
    assert empty.status_code == 200
    assert empty.json()["total"] == 0

    detail = client.get(f"/api/v1/scanner/history/{first['id']}")
    assert detail.status_code == 200
    result_id = detail.json()["results"][0]["id"]

    result = client.get(f"/api/v1/scanner/results/{result_id}")
    assert result.status_code == 200
    assert result.json()["symbol"] == "NSE:AAA26NOVFUT"
    assert result.json()["candles"]

    chart = client.get("/api/v1/scanner/chart/NSE:AAA26NOVFUT")
    assert chart.status_code == 200
    body = chart.json()
    assert len(body["points"]) > 0
    assert body["points"][0]["timestamp"].endswith("Z")
    assert body["pattern"] is not None
    assert body["scan_run_id"] == second["id"]

    missing = client.get("/api/v1/scanner/chart/NSE:NOPE")
    assert missing.status_code == 404

    comparison = client.get(
        "/api/v1/scanner/comparison",
        params={"base_run_id": first["id"], "compare_run_id": second["id"]},
    )
    assert comparison.status_code == 200
    assert "NSE:AAA26NOVFUT" in comparison.json()["persisted"]

    appearances = client.get(
        "/api/v1/scanner/symbols/NSE:AAA26NOVFUT/appearances"
    )
    assert appearances.status_code == 200
    assert len(appearances.json()["appearances"]) == 2
    assert appearances.json()["first_seen_at"]
    assert appearances.json()["latest_seen_at"]
