"""Tests for the owner-level FYERS login flow started from the admin panel."""

from __future__ import annotations

import time
from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from backend.core.config import Settings as BackendSettings
from backend.core.config import get_settings
from backend.main import app
from backend.services.fyers_auth import (
    FyersAuthError,
    FyersAuthService,
    FyersLoginUrl,
    get_fyers_auth_service,
)
from config import Settings as LegacySettings


def _service() -> FyersAuthService:
    backend = BackendSettings(
        admin_api_key="unit-test-key",
        fyers_backend_redirect_uri="http://localhost:8000/api/v1/fyers/callback",
        fyers_login_state_ttl_seconds=600,
    )
    legacy = LegacySettings(
        client_id="TESTCLIENT",
        secret_key="TESTSECRET",
        redirect_uri="http://localhost:8501",
    )
    return FyersAuthService(backend, legacy)


def test_state_signature_roundtrip_and_tampering() -> None:
    service = _service()
    state = service.create_state()
    assert service._verify(state) is True
    assert service._verify(state + "x") is False
    assert service._verify("") is False
    assert service._verify("garbage") is False


def test_expired_state_is_rejected() -> None:
    service = _service()
    state = service.create_state()
    future = time.time() + service.settings.fyers_login_state_ttl_seconds + 5
    assert service._verify(state, now=future) is False


def test_login_url_carries_backend_redirect_and_state() -> None:
    result = _service().create_login_url()
    assert result.redirect_uri.endswith("/api/v1/fyers/callback")
    assert result.login_url.startswith("https://")
    assert "client_id=TESTCLIENT" in result.login_url
    assert "state=" in result.login_url
    assert "redirect_uri=" in result.login_url
    assert result.state_expires_at > time.time()


class _FakeAuthService:
    def __init__(self) -> None:
        self.exchanged: list[tuple[str, str]] = []

    def create_login_url(self) -> FyersLoginUrl:
        return FyersLoginUrl(
            login_url="https://api-t1.fyers.in/api/v3/generate-authcode?state=abc",
            redirect_uri="http://localhost:8000/api/v1/fyers/callback",
            state_expires_at=time.time() + 600,
        )

    def exchange(self, auth_code: str, state: str) -> None:
        if state != "good-state":
            raise FyersAuthError("Invalid or expired OAuth state.")
        self.exchanged.append((auth_code, state))


@pytest.fixture()
def client(monkeypatch) -> Iterator[TestClient]:
    fake = _FakeAuthService()
    app.dependency_overrides[get_fyers_auth_service] = lambda: fake
    monkeypatch.setenv("ADMIN_API_KEY", "test-admin-key")
    get_settings.cache_clear()
    with TestClient(app) as test_client:
        test_client.fake_auth = fake  # type: ignore[attr-defined]
        yield test_client
    app.dependency_overrides.clear()
    get_settings.cache_clear()


def test_login_url_endpoint_requires_admin_key(client: TestClient) -> None:
    denied = client.get("/api/v1/admin/fyers/login-url")
    assert denied.status_code == 401

    allowed = client.get(
        "/api/v1/admin/fyers/login-url",
        headers={"X-Admin-Key": "test-admin-key"},
    )
    assert allowed.status_code == 200
    assert allowed.json()["login_url"].startswith("https://")


def test_callback_rejects_bad_state(client: TestClient) -> None:
    response = client.get(
        "/api/v1/fyers/callback",
        params={"auth_code": "abc123", "state": "bad-state"},
    )
    assert response.status_code == 400
    assert "FYERS login failed" in response.text


def test_callback_stores_token_on_success(client: TestClient) -> None:
    response = client.get(
        "/api/v1/fyers/callback",
        params={"auth_code": "abc123", "state": "good-state"},
    )
    assert response.status_code == 200
    assert "FYERS connected" in response.text
    assert client.fake_auth.exchanged == [("abc123", "good-state")]  # type: ignore[attr-defined]


def test_callback_without_code_fails(client: TestClient) -> None:
    response = client.get(
        "/api/v1/fyers/callback", params={"state": "good-state"}
    )
    assert response.status_code == 400
    assert "No authorization code" in response.text
