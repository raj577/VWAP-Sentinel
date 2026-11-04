from __future__ import annotations

import pandas as pd
import pytest

from scanner.models import (
    PATTERN_CONSOLIDATION,
    PATTERN_HUGGING,
    PATTERN_RECLAIM,
    PATTERN_TOUCH,
    PatternConfig,
)
from scanner.pattern_detector import PatternDetector, small_candle_mask
from tests.helpers import add_indicators, make_frame


@pytest.mark.parametrize("count", [1, 2, 3, 4, 5])
def test_pattern_is_detected_with_one_to_five_candles(count):
    frame = add_indicators(make_frame(pattern_count=count))
    pattern = PatternDetector().detect(frame)
    assert pattern is not None
    assert pattern.candle_count == count
    assert pattern.distance_pct < 0.5


def test_one_candle_touch_classification():
    frame = add_indicators(make_frame(pattern_count=1))
    pattern = PatternDetector().detect(frame)
    assert pattern is not None
    assert pattern.touched is True
    assert pattern.pattern_type == PATTERN_TOUCH


def test_two_candle_pattern_is_hugging():
    frame = add_indicators(make_frame(pattern_count=2))
    pattern = PatternDetector().detect(frame)
    assert pattern is not None
    assert pattern.candle_count == 2
    assert pattern.pattern_type == PATTERN_HUGGING


def test_three_candle_pattern_is_consolidation():
    frame = add_indicators(make_frame(pattern_count=3))
    pattern = PatternDetector().detect(frame)
    assert pattern is not None
    assert pattern.pattern_type == PATTERN_CONSOLIDATION
    assert pattern.window_range_pct <= 0.01


def test_price_too_far_above_avwap_is_rejected():
    far_candle = {
        "open": 100.90,
        "high": 101.20,
        "low": 100.70,
        "close": 101.00,
        "volume": 1000.0,
    }
    frame = add_indicators(make_frame(pattern_candles=[far_candle]))
    assert PatternDetector().detect(frame) is None


def test_price_below_avwap_beyond_tolerance_is_rejected():
    below_candle = {
        "open": 99.60,
        "high": 99.80,
        "low": 99.30,
        "close": 99.50,
        "volume": 1000.0,
    }
    frame = add_indicators(make_frame(pattern_candles=[below_candle]))
    assert PatternDetector().detect(frame) is None


def test_candle_low_touching_avwap_is_touch():
    touching = {
        "open": 100.05,
        "high": 100.35,
        "low": 99.90,
        "close": 100.12,
        "volume": 1000.0,
    }
    frame = add_indicators(make_frame(pattern_candles=[touching]))
    pattern = PatternDetector().detect(frame)
    assert pattern is not None
    assert pattern.touched is True
    assert pattern.pattern_type == PATTERN_TOUCH


def test_small_candle_body_ratio_detection():
    frame = pd.DataFrame(
        {
            "open": [100.00, 100.00],
            "high": [100.25, 100.25],
            "low": [99.95, 99.95],
            "close": [100.20, 100.05],
            "volume": [1.0, 1.0],
        }
    )
    mask = small_candle_mask(frame, max_body_ratio=0.35, max_range_atr=None)
    assert bool(mask.iloc[0]) is False
    assert bool(mask.iloc[1]) is True


def test_atr_range_cap_rejects_large_range_small_body_candle():
    frame = add_indicators(make_frame(pattern_count=1))
    frame.loc[frame.index[-1], "atr"] = 0.05
    assert PatternDetector().detect(frame) is None


def test_avwap_reclaim_is_classified():
    reclaim_candles = [
        {
            "open": 100.08,
            "high": 100.15,
            "low": 99.88,
            "close": 100.00,
            "volume": 1000.0,
        },
        {
            "open": 100.10,
            "high": 100.35,
            "low": 100.00,
            "close": 100.20,
            "volume": 1000.0,
        },
    ]
    frame = add_indicators(make_frame(pattern_candles=reclaim_candles))
    pattern = PatternDetector().detect(frame)
    assert pattern is not None
    assert pattern.candle_count == 2
    assert pattern.pattern_type == PATTERN_RECLAIM


def test_missing_data_returns_none():
    detector = PatternDetector()
    assert detector.detect(pd.DataFrame()) is None
    frame = add_indicators(make_frame(pattern_count=1))
    assert PatternDetector(PatternConfig(min_candles=2)).detect(frame.iloc[-1:]) is None


def test_missing_avwap_column_raises():
    frame = add_indicators(make_frame(pattern_count=1)).drop(columns=["avwap"])
    with pytest.raises(ValueError):
        PatternDetector().detect(frame)


def test_classification_filter_can_exclude_matches():
    frame = add_indicators(make_frame(pattern_count=2))
    config = PatternConfig(allowed_patterns=(PATTERN_CONSOLIDATION,))
    assert PatternDetector(config).detect(frame) is None
