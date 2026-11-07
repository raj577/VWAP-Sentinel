"""Phase 1 backend tests: app wiring and health probes.

The database is overridden with SQLite so tests never require PostgreSQL.
"""

from __future__ import annotations

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, sessionmaker

from backend.main import app
from backend.db.session import get_db


@pytest.fixture()
def client() -> Iterator[TestClient]:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
    )
    session_factory = sessionmaker(bind=engine)

    def override_get_db() -> Iterator[Session]:
        session = session_factory()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
    engine.dispose()


def test_liveness_is_ok(client: TestClient) -> None:
    response = client.get("/api/v1/health/live")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["version"]
    assert body["environment"]
    assert body["time_utc"].endswith(("Z", "+00:00"))


def test_readiness_reports_database_ok(client: TestClient) -> None:
    response = client.get("/api/v1/health/ready")
    assert response.status_code == 200
    assert response.json()["database"] == "ok"


def test_readiness_returns_503_when_database_fails(client: TestClient) -> None:
    class BrokenSession:
        def execute(self, *args: object, **kwargs: object) -> None:
            raise SQLAlchemyError("connection refused")

    def broken_db() -> Iterator[BrokenSession]:
        yield BrokenSession()

    app.dependency_overrides[get_db] = broken_db
    response = client.get("/api/v1/health/ready")
    assert response.status_code == 503
    assert response.json()["detail"]["database"] == "unavailable"


def test_api_index_and_openapi(client: TestClient) -> None:
    index = client.get("/api/v1/")
    assert index.status_code == 200
    assert index.json()["version"] == "v1"

    schema = client.get("/api/v1/openapi.json")
    assert schema.status_code == 200
    assert "/api/v1/health/live" in schema.json()["paths"]


def test_sqlite_session_can_execute_select() -> None:
    """Sanity check that the test database contract works like production."""

    engine = create_engine("sqlite+pysqlite:///:memory:")
    with engine.connect() as connection:
        assert connection.execute(text("SELECT 1")).scalar_one() == 1
    engine.dispose()
