from __future__ import annotations

import pandas as pd
import pytest

from data.historical_data import drop_incomplete_candles
from indicators.avwap import compute_contract_avwap
from indicators.vwap import compute_session_vwap

TZ = "Asia/Kolkata"


def _candles(prices, volumes=None, timestamps=None):
    volumes = volumes or [100.0] * len(prices)
    if timestamps is None:
        timestamps = pd.date_range(
            "2026-11-02 09:15", periods=len(prices), freq="h", tz=TZ
        )
    return pd.DataFrame(
        {
            "timestamp": timestamps,
            "open": prices,
            "high": prices,
            "low": prices,
            "close": prices,
            "volume": volumes,
        }
    )


def test_avwap_known_values():
    frame = _candles([10.0, 20.0], volumes=[100.0, 300.0])
    avwap = compute_contract_avwap(frame)
    assert avwap.iloc[0] == pytest.approx(10.0)
    assert avwap.iloc[1] == pytest.approx((10 * 100 + 20 * 300) / 400)


def test_avwap_uses_typical_price():
    frame = pd.DataFrame(
        {
            "timestamp": pd.date_range("2026-11-02 09:15", periods=1, freq="h", tz=TZ),
            "open": [9.0],
            "high": [12.0],
            "low": [8.0],
            "close": [10.0],
            "volume": [50.0],
        }
    )
    avwap = compute_contract_avwap(frame)
    assert avwap.iloc[0] == pytest.approx((12.0 + 8.0 + 10.0) / 3.0)


def test_contract_start_avwap_does_not_reset_daily():
    timestamps = pd.to_datetime(
        [
            "2026-11-02 09:15",
            "2026-11-02 10:15",
            "2026-11-03 09:15",
            "2026-11-03 10:15",
        ]
    ).tz_localize(TZ)
    frame = _candles([100.0, 100.0, 200.0, 200.0], timestamps=timestamps)

    contract_avwap = compute_contract_avwap(frame)
    session_vwap = compute_session_vwap(frame, TZ)

    assert contract_avwap.iloc[2] == pytest.approx(400.0 / 3.0)
    assert session_vwap.iloc[2] == pytest.approx(200.0)
    assert contract_avwap.iloc[2] != session_vwap.iloc[2]
    assert contract_avwap.iloc[3] == pytest.approx(150.0)


def test_avwap_anchor_index_skips_earlier_rows():
    frame = _candles([10.0, 20.0, 30.0, 40.0])
    avwap = compute_contract_avwap(frame, anchor_index=2)
    assert pd.isna(avwap.iloc[0])
    assert pd.isna(avwap.iloc[1])
    assert avwap.iloc[2] == pytest.approx(30.0)
    assert avwap.iloc[3] == pytest.approx(35.0)


def test_zero_volume_rows_do_not_change_avwap():
    frame = _candles([100.0, 110.0, 120.0], volumes=[0.0, 10.0, 10.0])
    avwap = compute_contract_avwap(frame)
    assert pd.isna(avwap.iloc[0])
    assert avwap.iloc[1] == pytest.approx(110.0)
    assert avwap.iloc[2] == pytest.approx(115.0)


def test_session_vwap_resets_each_day_while_avwap_does_not():
    timestamps = pd.to_datetime(
        [
            "2026-11-02 09:15",
            "2026-11-02 10:15",
            "2026-11-03 09:15",
            "2026-11-03 10:15",
        ]
    ).tz_localize(TZ)
    frame = _candles([100.0, 100.0, 200.0, 200.0], timestamps=timestamps)
    contract_avwap = compute_contract_avwap(frame)
    session_vwap = compute_session_vwap(frame, TZ)

    assert session_vwap.iloc[0] == pytest.approx(100.0)
    assert session_vwap.iloc[1] == pytest.approx(100.0)
    assert session_vwap.iloc[2] == pytest.approx(200.0)
    assert contract_avwap.iloc[2] == pytest.approx(400.0 / 3.0)


def test_drop_incomplete_candles_removes_forming_bar():
    now = pd.Timestamp("2026-11-04 09:15", tz=TZ)
    timestamps = pd.to_datetime(
        ["2026-11-04 07:15", "2026-11-04 08:15", "2026-11-04 09:15"]
    ).tz_localize(TZ)
    frame = _candles([100.0, 101.0, 102.0], timestamps=timestamps)

    completed = drop_incomplete_candles(frame, "60", now=now, timezone=TZ)
    assert len(completed) == 2
    assert completed["timestamp"].iloc[-1] == timestamps[1]


def test_final_short_session_candle_is_complete_after_market_close():
    timestamps = pd.to_datetime(
        ["2026-11-04 14:15", "2026-11-04 15:15"]
    ).tz_localize(TZ)
    frame = _candles([100.0, 101.0], timestamps=timestamps)

    before_close = drop_incomplete_candles(
        frame, "60", now=pd.Timestamp("2026-11-04 15:20", tz=TZ), timezone=TZ
    )
    after_close = drop_incomplete_candles(
        frame, "60", now=pd.Timestamp("2026-11-04 15:35", tz=TZ), timezone=TZ
    )
    assert len(before_close) == 1
    assert len(after_close) == 2
