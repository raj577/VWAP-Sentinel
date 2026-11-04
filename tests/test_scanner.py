from __future__ import annotations

from datetime import date, timedelta

import pandas as pd
import pytest

from config import Settings
from data.cache import HistoricalCache
from data.historical_data import NoMarketDataError, normalize_candles
from data.instrument_master import (
    InstrumentMasterError,
    parse_instrument_master,
    select_active_futures,
)
from scanner.models import PatternConfig
from scanner.scan_engine import ScanEngine
from tests.helpers import make_frame, make_instrument

TZ = "Asia/Kolkata"


class FakeHistoryService:
    def __init__(self, frames: dict[str, pd.DataFrame]) -> None:
        self.frames = frames

    def fetch(
        self,
        instrument,
        resolution: str | None = None,
        end_date: date | None = None,
        force_refresh: bool = False,
    ) -> pd.DataFrame:
        if instrument.symbol not in self.frames:
            raise NoMarketDataError(f"No historical candles for {instrument.symbol}")
        return self.frames[instrument.symbol].copy()


def _settings(tmp_path) -> Settings:
    return Settings(
        client_id="test-client",
        secret_key="test-secret",
        redirect_uri="http://localhost:8501",
        token_file=tmp_path / "access_token.txt",
        token_meta_file=tmp_path / "token_meta.json",
        cache_dir=tmp_path / "cache",
        log_dir=tmp_path / "logs",
        request_rate_per_sec=0.0,
        request_max_retries=0,
        history_cache_ttl_seconds=60,
    )


def test_scan_engine_finds_match_and_handles_errors(tmp_path):
    today = pd.Timestamp.now(tz=TZ).date()
    valid = make_instrument(
        "NSE:AAAA26NOVFUT", "AAAA", expiry=today + timedelta(days=20)
    )
    missing = make_instrument(
        "NSE:BBBB26NOVFUT", "BBBB", expiry=today + timedelta(days=20)
    )
    expired = make_instrument(
        "NSE:CCCC26NOVFUT", "CCCC", expiry=today - timedelta(days=1)
    )

    frame = make_frame(pattern_count=3)
    engine = ScanEngine(
        FakeHistoryService({valid.symbol: frame}),
        _settings(tmp_path),
    )
    report = engine.scan([valid, missing, expired], PatternConfig(), as_of=today)

    assert report.scanned_count == 3
    assert len(report.matches) == 1
    assert report.matches[0].symbol == valid.symbol
    assert len(report.errors) == 2
    assert report.summary()["matches"] == 1
    assert {"avwap", "session_vwap", "atr"}.issubset(
        report.histories[valid.symbol].columns
    )

    reasons = {error.symbol: error.message.lower() for error in report.errors}
    assert "expired" in reasons[expired.symbol]
    assert "no historical" in reasons[missing.symbol]


def test_scan_sorts_matches_closest_first(tmp_path):
    today = pd.Timestamp.now(tz=TZ).date()
    closer = make_instrument(
        "NSE:AAAA26NOVFUT", "AAAA", expiry=today + timedelta(days=20)
    )
    farther = make_instrument(
        "NSE:BBBB26NOVFUT", "BBBB", expiry=today + timedelta(days=20)
    )
    farther_pattern = {
        "open": 100.25,
        "high": 100.50,
        "low": 100.05,
        "close": 100.35,
        "volume": 1000.0,
    }
    frames = {
        closer.symbol: make_frame(pattern_count=2),
        farther.symbol: make_frame(pattern_candles=[farther_pattern]),
    }
    report = ScanEngine(FakeHistoryService(frames), _settings(tmp_path)).scan(
        [farther, closer], PatternConfig(), as_of=today
    )

    assert len(report.matches) == 2
    distances = [abs(match.pattern.distance_pct) for match in report.sorted_matches()]
    assert distances == sorted(distances)


def test_expired_futures_are_excluded_and_current_expiry_is_preferred():
    today = date(2026, 11, 4)
    master = pd.DataFrame(
        [
            {
                "symbol": "NSE:AAAA26NOVFUT",
                "underlying": "AAAA",
                "expiry": today - timedelta(days=1),
                "is_index": False,
            },
            {
                "symbol": "NSE:AAAA26NOVFUT2",
                "underlying": "AAAA",
                "expiry": today + timedelta(days=10),
                "is_index": False,
            },
            {
                "symbol": "NSE:AAAA26DECFUT",
                "underlying": "AAAA",
                "expiry": today + timedelta(days=40),
                "is_index": False,
            },
            {
                "symbol": "NSE:BBBB26NOVFUT",
                "underlying": "BBBB",
                "expiry": today + timedelta(days=5),
                "is_index": False,
            },
            {
                "symbol": "NSE:NIFTY26NOVFUT",
                "underlying": "NIFTY",
                "expiry": today + timedelta(days=3),
                "is_index": True,
            },
        ]
    )

    active = select_active_futures(
        master, as_of=today, current_expiry_only=True, include_index=False
    )
    assert len(active) == 2
    assert set(active["underlying"]) == {"AAAA", "BBBB"}
    assert set(active["expiry"]) == {today + timedelta(days=10), today + timedelta(days=5)}
    assert (active["expiry"] >= today).all()
    assert active["is_current_expiry"].all()

    with_index = select_active_futures(
        master, as_of=today, current_expiry_only=True, include_index=True
    )
    assert "NIFTY" in set(with_index["underlying"])


def _master_row(symbol: str, underlying: str, expiry_epoch: int, description: str) -> str:
    row = ["0"] * 21
    row[1] = description
    row[2] = "1"
    row[8] = str(expiry_epoch)
    row[9] = symbol
    row[13] = underlying
    return ",".join(row)


def test_parse_master_rejects_options_bad_symbols_and_duplicates():
    expiry = int(
        pd.Timestamp("2026-11-23 15:40", tz=TZ).timestamp()
    )
    text = "\n".join(
        [
            _master_row("NSE:AAAA26NOVFUT", "AAAA", expiry, "AAAA 23 Nov 26 FUT"),
            _master_row("NSE:AAAA26NOVFUT", "AAAA", expiry, "AAAA 23 Nov 26 FUT"),
            _master_row("NSE:AAAA26NOV100CE", "AAAA", expiry, "AAAA 100 CE"),
            _master_row("NSE:BBBB26NOVFUT", "CCCC", expiry, "BBBB 23 Nov 26 FUT"),
        ]
    )
    parsed = parse_instrument_master(text, timezone=TZ)
    assert len(parsed) == 1
    assert parsed.iloc[0]["symbol"] == "NSE:AAAA26NOVFUT"
    assert parsed.iloc[0]["expiry"] == date(2026, 11, 23)
    assert bool(parsed.iloc[0]["is_index"]) is False


def test_parse_master_with_no_futures_raises():
    text = _master_row("NSE:AAAA26NOV100CE", "AAAA", 1_795_428_600, "AAAA 100 CE")
    with pytest.raises(InstrumentMasterError):
        parse_instrument_master(text, timezone=TZ)


def test_historical_cache_roundtrip_preserves_timestamps(tmp_path):
    frame = make_frame(pattern_count=2)
    cache = HistoricalCache(tmp_path / "cache", ttl_seconds=3600, timezone=TZ)
    cache.store(
        "NSE:TEST26NOVFUT",
        "60",
        0,
        frame,
        requested_from=date(2026, 1, 1),
        requested_to=date(2026, 12, 31),
    )
    loaded = cache.load("NSE:TEST26NOVFUT", "60", 0)
    assert loaded is not None
    cached_frame, meta = loaded
    restored = normalize_candles(cached_frame, TZ)
    assert len(restored) == len(frame)
    assert list(restored["timestamp"]) == list(frame["timestamp"])
    assert meta["rows"] == len(frame)
