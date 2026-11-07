"""Phase 4 tests: calendar, scheduler settings, pipeline execution and APIs."""

from __future__ import annotations

from collections.abc import Iterator
from datetime import date, datetime, timedelta, timezone
from zoneinfo import ZoneInfo

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

from backend.core.config import Settings, get_settings
from backend.core.time import utcnow
from backend.db.base import Base
from backend.db.models import (
    IngestionJob,
    Instrument,
    MarketCandle,
    PipelineJob,
    PipelineJobLog,
)
from backend.db.session import get_db
from backend.main import app
from backend.services.ingestion import IngestionCancelled
from backend.services.market_calendar import MarketCalendar, parse_holidays
from backend.services.pipeline import (
    JOB_FULL_PIPELINE,
    JOB_SCAN,
    STATUS_CANCELLED,
    STATUS_COMPLETED,
    STATUS_FAILED,
    STATUS_PARTIALLY_COMPLETED,
    STATUS_PENDING,
    STATUS_RUNNING,
    TRIGGER_MANUAL,
    IngestionOutcome,
    PipelineExecutor,
    ScanOutcome,
    claim_next_job,
    recover_abandoned_jobs,
)
from backend.services.scanner import ScanCancelled
from backend.services.scheduler_settings import (
    compute_next_run,
    get_scheduler_settings,
)

IST = ZoneInfo("Asia/Kolkata")
HEADERS = {"X-Admin-Key": "test-admin-key"}


def _factory(tmp_path, name: str = "phase4.db") -> sessionmaker[Session]:
    engine = create_engine(
        f"sqlite+pysqlite:///{tmp_path / name}",
        connect_args={"check_same_thread": False},
    )
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def _make_job(
    factory: sessionmaker[Session],
    *,
    job_type: str = JOB_FULL_PIPELINE,
    status: str = STATUS_PENDING,
    cancellation: bool = False,
    heartbeat: datetime | None = None,
) -> int:
    db = factory()
    try:
        job = PipelineJob(
            job_type=job_type,
            trigger_source=TRIGGER_MANUAL,
            status=status,
            stage="QUEUED",
            cancellation_requested_at=utcnow() if cancellation else None,
            heartbeat_at=heartbeat,
            started_at=heartbeat or utcnow(),
        )
        db.add(job)
        db.commit()
        db.refresh(job)
        return job.id
    finally:
        db.close()


def _ingestion_ok(job, should_cancel, progress) -> IngestionOutcome:
    return IngestionOutcome(
        job_id=None,
        status=STATUS_COMPLETED,
        total=3,
        successful=3,
        failed=0,
        inserted=30,
        updated=2,
    )


def _scan_ok(job, should_cancel, progress) -> ScanOutcome:
    return ScanOutcome(
        scan_run_id=None,
        status=STATUS_COMPLETED,
        scanned=3,
        failed=0,
        matches=2,
    )


# ------------------------------------------------------------------ calendar
def test_calendar_handles_weekends_holidays_and_hours() -> None:
    saturday = datetime(2026, 11, 7, 10, 0, tzinfo=IST)
    monday = datetime(2026, 11, 9, 10, 0, tzinfo=IST)
    early = datetime(2026, 11, 9, 8, 0, tzinfo=IST)

    calendar = MarketCalendar()
    assert calendar.is_trading_day(saturday.date()) is False
    assert calendar.is_market_open(saturday) is False
    assert calendar.is_trading_day(monday.date()) is True
    assert calendar.is_market_open(monday) is True
    assert calendar.is_market_open(early) is False

    holiday_calendar = MarketCalendar(holidays=frozenset({monday.date()}))
    assert holiday_calendar.is_market_open(monday) is False


def test_invalid_calendar_config_raises() -> None:
    with pytest.raises(ValueError):
        parse_holidays(["not-a-date"])
    with pytest.raises(ValueError):
        MarketCalendar(open_time="9am").is_market_open(
            datetime(2026, 11, 9, 10, 0, tzinfo=IST)
        )


def test_compute_next_run_respects_pause() -> None:
    now = utcnow()
    assert compute_next_run(now, 56, True) == now + timedelta(minutes=56)
    assert compute_next_run(now, 56, False) is None


def test_scheduler_settings_singleton(tmp_path) -> None:
    factory = _factory(tmp_path)
    with factory() as db:
        first = get_scheduler_settings(db)
        second = get_scheduler_settings(db)
        assert first.id == 1
        assert second.id == 1
        assert first.scan_interval_minutes == 56
        assert first.scheduler_enabled is True


# ------------------------------------------------------------------ executor
def test_full_pipeline_runs_ingestion_before_scan(tmp_path) -> None:
    factory = _factory(tmp_path)
    job_id = _make_job(factory)
    order: list[str] = []

    def ingestion(job, should_cancel, progress):
        order.append("ingestion")
        return _ingestion_ok(job, should_cancel, progress)

    def scan(job, should_cancel, progress):
        order.append("scan")
        return _scan_ok(job, should_cancel, progress)

    executor = PipelineExecutor(
        factory, ingestion_runner=ingestion, scan_runner=scan
    )
    executor.execute(job_id)

    assert order == ["ingestion", "scan"]
    with factory() as db:
        job = db.get(PipelineJob, job_id)
        assert job.status == STATUS_COMPLETED
        assert job.processed_instruments == 3
        assert job.candles_inserted == 30
        assert job.candles_updated == 2


def test_partial_ingestion_marks_pipeline_partial(tmp_path) -> None:
    factory = _factory(tmp_path)
    job_id = _make_job(factory)

    def ingestion(job, should_cancel, progress):
        return IngestionOutcome(
            job_id=None,
            status=STATUS_PARTIALLY_COMPLETED,
            total=3,
            successful=2,
            failed=1,
            inserted=10,
            updated=0,
            error="AAA: timeout",
        )

    executor = PipelineExecutor(
        factory, ingestion_runner=ingestion, scan_runner=_scan_ok
    )
    executor.execute(job_id)

    with factory() as db:
        assert db.get(PipelineJob, job_id).status == STATUS_PARTIALLY_COMPLETED


def test_ingestion_failure_skips_scan(tmp_path) -> None:
    factory = _factory(tmp_path)
    job_id = _make_job(factory)
    scanned = {"called": False}

    def ingestion(job, should_cancel, progress):
        return IngestionOutcome(
            job_id=None,
            status=STATUS_FAILED,
            total=0,
            successful=0,
            failed=0,
            inserted=0,
            updated=0,
            error="auth expired",
        )

    def scan(job, should_cancel, progress):
        scanned["called"] = True
        return _scan_ok(job, should_cancel, progress)

    PipelineExecutor(
        factory, ingestion_runner=ingestion, scan_runner=scan
    ).execute(job_id)

    with factory() as db:
        job = db.get(PipelineJob, job_id)
        assert job.status == STATUS_FAILED
        assert "auth expired" in (job.error_summary or "")
    assert scanned["called"] is False


def test_cancellation_marks_job_cancelled_without_scan(tmp_path) -> None:
    factory = _factory(tmp_path)
    job_id = _make_job(factory, cancellation=True)

    called = {"scan": False}

    def scan(job, should_cancel, progress):
        called["scan"] = True
        return _scan_ok(job, should_cancel, progress)

    PipelineExecutor(factory, scan_runner=scan).execute(job_id)

    with factory() as db:
        job = db.get(PipelineJob, job_id)
        assert job.status == STATUS_CANCELLED
    assert called["scan"] is False


def test_cancellation_during_ingestion_is_honoured(tmp_path) -> None:
    factory = _factory(tmp_path)
    job_id = _make_job(factory)

    def ingestion(job, should_cancel, progress):
        if should_cancel():
            raise IngestionCancelled("stop")
        return _ingestion_ok(job, should_cancel, progress)

    # Flip cancellation after the executor's first probe is cached.
    executor = PipelineExecutor(factory, ingestion_runner=ingestion)
    with factory() as db:
        job = db.get(PipelineJob, job_id)
        job.cancellation_requested_at = utcnow()
        db.commit()

    executor.execute(job_id)
    with factory() as db:
        assert db.get(PipelineJob, job_id).status == STATUS_CANCELLED


def test_recovery_marks_stale_running_job_failed(tmp_path) -> None:
    factory = _factory(tmp_path)
    stale = _make_job(
        factory,
        status=STATUS_RUNNING,
        heartbeat=utcnow() - timedelta(hours=2),
    )
    healthy = _make_job(
        factory,
        status=STATUS_RUNNING,
        heartbeat=utcnow(),
    )

    recovered = recover_abandoned_jobs(factory, timeout_seconds=300)
    assert recovered == [stale]

    with factory() as db:
        assert db.get(PipelineJob, stale).status == STATUS_FAILED
        assert db.get(PipelineJob, healthy).status == STATUS_RUNNING


def test_claim_next_job_is_single_use(tmp_path) -> None:
    factory = _factory(tmp_path)
    first = _make_job(factory)
    second = _make_job(factory, job_type=JOB_SCAN)

    claimed_first = claim_next_job(factory, "w1")
    claimed_second = claim_next_job(factory, "w2")
    assert claimed_first == first
    assert claimed_second == second
    assert claim_next_job(factory, "w3") is None

    with factory() as db:
        assert db.get(PipelineJob, first).status == STATUS_RUNNING
        assert db.get(PipelineJob, second).status == STATUS_RUNNING


# ----------------------------------------------------------------------- API
@pytest.fixture()
def client(tmp_path, monkeypatch) -> Iterator[TestClient]:
    factory = _factory(tmp_path)

    def override_db() -> Iterator[Session]:
        session = factory()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db] = override_db
    monkeypatch.setenv("ADMIN_API_KEY", "test-admin-key")
    get_settings.cache_clear()
    with TestClient(app) as test_client:
        test_client.factory = factory  # type: ignore[attr-defined]
        yield test_client
    app.dependency_overrides.clear()
    get_settings.cache_clear()


def test_scheduler_endpoints_and_authorization(client: TestClient) -> None:
    assert client.get("/api/v1/admin/scheduler/status").status_code == 401

    status_response = client.get(
        "/api/v1/admin/scheduler/status", headers=HEADERS
    )
    assert status_response.status_code == 200
    body = status_response.json()
    assert body["settings"]["scheduler_enabled"] is True
    assert body["settings"]["scan_interval_minutes"] == 56

    paused = client.post("/api/v1/admin/scheduler/pause", headers=HEADERS)
    assert paused.status_code == 200
    assert paused.json()["scheduler_enabled"] is False
    assert paused.json()["next_run_at"] is None

    resumed = client.post("/api/v1/admin/scheduler/resume", headers=HEADERS)
    assert resumed.status_code == 200
    assert resumed.json()["scheduler_enabled"] is True
    assert resumed.json()["next_run_at"] is not None

    patched = client.patch(
        "/api/v1/admin/scheduler/settings",
        headers=HEADERS,
        json={"scan_interval_minutes": 30},
    )
    assert patched.status_code == 200
    assert patched.json()["scan_interval_minutes"] == 30

    invalid = client.patch(
        "/api/v1/admin/scheduler/settings",
        headers=HEADERS,
        json={"market_open_time": "25:00"},
    )
    assert invalid.status_code == 422


def test_manual_refresh_enqueues_once(client: TestClient) -> None:
    accepted = client.post("/api/v1/admin/pipeline/refresh", headers=HEADERS)
    assert accepted.status_code == 202
    body = accepted.json()
    assert body["status"] == STATUS_PENDING
    assert body["job_type"] == JOB_FULL_PIPELINE

    conflict = client.post("/api/v1/admin/pipeline/refresh", headers=HEADERS)
    assert conflict.status_code == 409, conflict.text

    cancelled = client.post(
        f"/api/v1/admin/pipeline/jobs/{body['id']}/cancel", headers=HEADERS
    )
    assert cancelled.status_code == 200, cancelled.text
    assert cancelled.json()["status"] == STATUS_CANCELLED


def test_manual_refresh_blocked_when_closed(client: TestClient) -> None:
    today = datetime.now(tz=IST).date().isoformat()
    patched = client.patch(
        "/api/v1/admin/scheduler/settings",
        headers=HEADERS,
        json={
            "allow_manual_outside_market_hours": False,
            "market_holidays": [today],
        },
    )
    assert patched.status_code == 200

    blocked = client.post("/api/v1/admin/pipeline/refresh", headers=HEADERS)
    assert blocked.status_code == 409
    assert "market" in blocked.json()["detail"].lower()


def _seed_candle(factory, hours_old: int) -> None:
    with factory() as db:
        instrument = Instrument(
            fyers_symbol="NSE:PHASE4TEST26NOVFUT",
            underlying_symbol="PHASE4",
            expiry_date=date.today() + timedelta(days=20),
            is_active=True,
        )
        db.add(instrument)
        db.flush()
        stamp = utcnow() - timedelta(hours=hours_old)
        db.add(
            MarketCandle(
                instrument_id=instrument.id,
                timeframe="60",
                timestamp=stamp,
                open=100,
                high=101,
                low=99,
                close=100,
                volume=1000,
            )
        )
        db.commit()


def test_run_scanner_requires_confirmation_for_stale_data(
    client: TestClient,
) -> None:
    _seed_candle(client.factory, hours_old=48)  # type: ignore[attr-defined]

    blocked = client.post("/api/v1/admin/pipeline/run-scanner", headers=HEADERS)
    assert blocked.status_code == 409
    assert "stale" in blocked.json()["detail"].lower()

    accepted = client.post(
        "/api/v1/admin/pipeline/run-scanner",
        headers=HEADERS,
        json={"confirm_stale": True},
    )
    assert accepted.status_code == 202, accepted.text
    assert accepted.json()["job_type"] == JOB_SCAN


def test_job_monitoring_endpoints(client: TestClient) -> None:
    factory = client.factory  # type: ignore[attr-defined]
    job_id = _make_job(factory, status=STATUS_COMPLETED)
    with factory() as db:
        db.add(
            PipelineJobLog(
                job_id=job_id,
                symbol="NSE:PHASE4TEST26NOVFUT",
                status="OK",
                candles_processed=10,
            )
        )
        db.commit()

    listing = client.get("/api/v1/admin/pipeline/jobs", headers=HEADERS)
    assert listing.status_code == 200
    assert listing.json()["total"] == 1

    filtered = client.get(
        "/api/v1/admin/pipeline/jobs",
        headers=HEADERS,
        params={"status": STATUS_COMPLETED, "job_type": JOB_FULL_PIPELINE},
    )
    assert filtered.json()["total"] == 1

    detail = client.get(
        f"/api/v1/admin/pipeline/jobs/{job_id}", headers=HEADERS
    )
    assert detail.status_code == 200

    logs = client.get(
        f"/api/v1/admin/pipeline/jobs/{job_id}/logs", headers=HEADERS
    )
    assert logs.status_code == 200
    assert logs.json()["total"] == 1
    assert logs.json()["items"][0]["symbol"] == "NSE:PHASE4TEST26NOVFUT"

    summary = client.get("/api/v1/admin/pipeline/summary", headers=HEADERS)
    assert summary.status_code == 200
    assert summary.json()["counts"][STATUS_COMPLETED] == 1

    missing = client.get(
        "/api/v1/admin/pipeline/jobs/9999", headers=HEADERS
    )
    assert missing.status_code == 404


def test_cancel_running_job_requests_cooperative_stop(
    client: TestClient,
) -> None:
    factory = client.factory  # type: ignore[attr-defined]
    job_id = _make_job(factory, status=STATUS_RUNNING, heartbeat=utcnow())

    response = client.post(
        f"/api/v1/admin/pipeline/jobs/{job_id}/cancel",
        headers=HEADERS,
        json={"reason": "admin stop"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == STATUS_RUNNING
    assert body["cancellation_requested_at"] is not None

    # Repeating on a completed job must not cancel history.
    with factory() as db:
        job = db.get(PipelineJob, job_id)
        job.status = STATUS_COMPLETED
        db.commit()

    rejected = client.post(
        f"/api/v1/admin/pipeline/jobs/{job_id}/cancel", headers=HEADERS
    )
    assert rejected.status_code == 409


def test_pipeline_executor_uses_ingestion_job_logs(tmp_path) -> None:
    factory = _factory(tmp_path)
    job_id = _make_job(factory)
    with factory() as db:
        ingestion = IngestionJob(
            job_type="MARKET_DATA",
            status=STATUS_COMPLETED,
            triggered_by="test",
        )
        db.add(ingestion)
        db.commit()
        ingestion_id = ingestion.id

    def ingestion_runner(job, should_cancel, progress):
        return IngestionOutcome(
            job_id=ingestion_id,
            status=STATUS_COMPLETED,
            total=1,
            successful=1,
            failed=0,
            inserted=1,
            updated=0,
        )

    PipelineExecutor(
        factory, ingestion_runner=ingestion_runner, scan_runner=_scan_ok
    ).execute(job_id)

    # The ingestion job has no per-instrument items here, so logs stay empty but
    # the link itself must be recorded.
    with factory() as db:
        job = db.get(PipelineJob, job_id)
        assert job.ingestion_job_id == ingestion_id


def test_scan_cancelled_outcome_marks_job_cancelled(tmp_path) -> None:
    factory = _factory(tmp_path)
    job_id = _make_job(factory, job_type=JOB_SCAN)

    def scan(job, should_cancel, progress):
        raise ScanCancelled("stop")

    PipelineExecutor(factory, scan_runner=scan).execute(job_id)

    with factory() as db:
        assert db.get(PipelineJob, job_id).status == STATUS_CANCELLED

def test_scheduler_gate_requires_due_time_and_open_market() -> None:
    from backend.scheduler_main import should_enqueue_scheduled

    calendar = MarketCalendar()
    monday_open = datetime(2026, 11, 9, 10, 0, tzinfo=IST)
    saturday = datetime(2026, 11, 7, 10, 0, tzinfo=IST)

    assert should_enqueue_scheduled(
        True, monday_open - timedelta(minutes=1), monday_open, calendar
    )
    assert not should_enqueue_scheduled(
        False, monday_open - timedelta(minutes=1), monday_open, calendar
    )
    assert not should_enqueue_scheduled(
        True, monday_open + timedelta(minutes=1), monday_open, calendar
    )
    assert not should_enqueue_scheduled(
        True, saturday - timedelta(minutes=1), saturday, calendar
    )
