from __future__ import annotations

from datetime import date

import pytest

from config import Settings
from data.fyers_client import (
    ApiError,
    AuthenticationError,
    FyersClient,
)


class FakeApi:
    def __init__(self, history_responses=None, profile_response=None) -> None:
        self.history_responses = list(history_responses or [])
        self.profile_response = profile_response or {"s": "ok", "data": {"display_name": "T"}}
        self.history_calls = 0

    def get_profile(self):
        return self.profile_response

    def history(self, payload):
        self.history_calls += 1
        if not self.history_responses:
            return {"s": "ok", "candles": []}
        return self.history_responses.pop(0)


def _settings(tmp_path) -> Settings:
    return Settings(
        client_id="client",
        secret_key="secret",
        redirect_uri="http://localhost:8501",
        token_file=tmp_path / "token.txt",
        token_meta_file=tmp_path / "meta.json",
        cache_dir=tmp_path / "cache",
        log_dir=tmp_path / "logs",
        request_rate_per_sec=0.0,
        request_max_retries=2,
        retry_base_seconds=0.001,
    )


def test_profile_authentication_error_is_detected(tmp_path):
    api = FakeApi(
        profile_response={
            "s": "error",
            "code": -8,
            "message": "Could not authenticate the user",
        }
    )
    client = FyersClient(_settings(tmp_path), "token", api=api)
    with pytest.raises(AuthenticationError):
        client.verify_connection()


def test_profile_success(tmp_path):
    client = FyersClient(_settings(tmp_path), "token", api=FakeApi())
    assert client.verify_connection()["display_name"] == "T"


def test_rate_limit_is_retried(tmp_path):
    api = FakeApi(
        history_responses=[
            {"s": "error", "code": 429, "message": "request limit reached"},
            {"s": "ok", "candles": [[1_700_000_000, 1, 2, 0.5, 1.5, 100]]},
        ]
    )
    client = FyersClient(_settings(tmp_path), "token", api=api)
    candles = client.history(
        "NSE:TEST26NOVFUT", "60", date(2026, 11, 1), date(2026, 11, 4), 0
    )
    assert api.history_calls == 2
    assert candles == [[1_700_000_000, 1, 2, 0.5, 1.5, 100]]


def test_invalid_symbol_is_not_retried(tmp_path):
    api = FakeApi(
        history_responses=[
            {"s": "error", "code": -300, "message": "Invalid symbol"},
        ]
    )
    client = FyersClient(_settings(tmp_path), "token", api=api)
    with pytest.raises(ApiError):
        client.history(
            "NSE:BAD26NOVFUT", "60", date(2026, 11, 1), date(2026, 11, 4), 0
        )
    assert api.history_calls == 1


def test_missing_history_data_returns_empty_list(tmp_path):
    client = FyersClient(_settings(tmp_path), "token", api=FakeApi())
    candles = client.history(
        "NSE:TEST26NOVFUT", "60", date(2026, 11, 1), date(2026, 11, 4), 0
    )
    assert candles == []
