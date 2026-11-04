from __future__ import annotations

from datetime import date, timedelta

import pandas as pd
import pytest

from config import Settings
from data.cache import HistoricalCache
from data.historical_data import HistoricalDataService, NoMarketDataError
from tests.helpers import make_instrument

TZ = "Asia/Kolkata"
END_DATE = date(2026, 11, 4)


class FakeHistoryApi:
    def __init__(self, empty: bool = False) -> None:
        self.empty = empty
        self.payloads: list[dict[str, object]] = []

    def history(
        self,
        symbol: str,
        resolution: str,
        range_from: date,
        range_to: date,
        cont_flag: int,
    ) -> list[list[float]]:
        self.payloads.append(
            {
                "symbol": symbol,
                "resolution": resolution,
                "range_from": range_from,
                "range_to": range_to,
                "cont_flag": cont_flag,
            }
        )
        if self.empty:
            return []

        rows: list[list[float]] = []
        cursor = range_from
        while cursor <= range_to:
            if cursor.weekday() < 5:
                start = pd.Timestamp(f"{cursor.isoformat()} 09:15:00", tz=TZ)
                rows.append([int(start.timestamp()), 100.0, 101.0, 99.0, 100.5, 1000.0])
            cursor += timedelta(days=1)
        return rows


def _settings(tmp_path, lookback: int = 10, chunk_days: int = 60) -> Settings:
    return Settings(
        cache_dir=tmp_path / "cache",
        log_dir=tmp_path / "logs",
        history_cache_ttl_seconds=3600,
        history_chunk_days=chunk_days,
        contract_lookback_days=lookback,
        history_cont_flag=0,
        request_rate_per_sec=0.0,
        timezone=TZ,
    )


def _service(tmp_path, api: FakeHistoryApi, lookback: int = 10, chunk_days: int = 60):
    settings = _settings(tmp_path, lookback=lookback, chunk_days=chunk_days)
    cache = HistoricalCache(
        settings.cache_dir,
        settings.history_cache_ttl_seconds,
        settings.timezone,
    )
    return HistoricalDataService(api, cache, settings), cache


def test_fetch_uses_individual_contract_flag_and_reuses_cache(tmp_path):
    api = FakeHistoryApi()
    service, _ = _service(tmp_path, api)
    instrument = make_instrument(expiry=date(2026, 12, 31))

    first = service.fetch(instrument, "60", end_date=END_DATE)
    assert not first.empty
    assert len(api.payloads) == 1
    assert api.payloads[0]["cont_flag"] == 0
    assert api.payloads[0]["resolution"] == "60"
    assert api.payloads[0]["range_from"] == END_DATE - timedelta(days=10)
    assert api.payloads[0]["range_to"] == END_DATE

    second = service.fetch(instrument, "60", end_date=END_DATE)
    assert len(api.payloads) == 1
    assert first["timestamp"].tolist() == second["timestamp"].tolist()


def test_fetch_chunks_long_lookbacks(tmp_path):
    api = FakeHistoryApi()
    service, _ = _service(tmp_path, api, lookback=130, chunk_days=60)
    instrument = make_instrument(expiry=date(2026, 12, 31))

    frame = service.fetch(instrument, "60", end_date=END_DATE)
    assert not frame.empty
    assert len(api.payloads) == 3
    for payload in api.payloads:
        span = payload["range_to"] - payload["range_from"]
        assert span <= timedelta(days=59)
        assert payload["cont_flag"] == 0


def test_fetch_raises_when_no_completed_candles(tmp_path):
    api = FakeHistoryApi(empty=True)
    service, _ = _service(tmp_path, api)
    instrument = make_instrument(expiry=date(2026, 12, 31))

    with pytest.raises(NoMarketDataError):
        service.fetch(instrument, "60", end_date=END_DATE)
