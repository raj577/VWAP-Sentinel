from __future__ import annotations

import json

import pytest

from scanner.models import PATTERN_TYPES, PatternConfig
from scanner.presets import PresetError, PresetStore, ScannerPreset


def _config() -> PatternConfig:
    return PatternConfig(
        max_close_above_pct=0.0075,
        max_close_below_pct=0.0025,
        max_low_below_pct=0.0035,
        max_body_ratio=0.30,
        min_candles=2,
        max_candles=4,
        max_window_range_pct=0.015,
        max_candle_range_atr=1.5,
        consolidation_range_pct=0.008,
        allowed_patterns=(PATTERN_TYPES[0], PATTERN_TYPES[2]),
    )


def test_preset_roundtrip(tmp_path):
    store = PresetStore(tmp_path / "presets" / "scanner.json")
    preset = ScannerPreset.from_config("  Tight setup  ", "120", _config())
    store.save(preset)

    loaded = store.get("Tight setup")
    assert loaded is not None
    assert loaded.name == "Tight setup"
    assert loaded.timeframe == "120"
    assert loaded.config.min_candles == 2
    assert loaded.config.max_candles == 4
    assert loaded.config.max_close_above_pct == pytest.approx(0.0075)
    assert loaded.config.max_window_range_pct == pytest.approx(0.015)
    assert loaded.config.max_candle_range_atr == pytest.approx(1.5)
    assert loaded.config.allowed_patterns == (PATTERN_TYPES[0], PATTERN_TYPES[2])


def test_preset_without_atr_cap_roundtrips(tmp_path):
    store = PresetStore(tmp_path / "scanner.json")
    config = PatternConfig(max_candle_range_atr=None)
    store.save(ScannerPreset.from_config("No ATR", "60", config))

    loaded = store.get("No ATR")
    assert loaded is not None
    assert loaded.config.max_candle_range_atr is None


def test_presets_sort_and_overwrite(tmp_path):
    store = PresetStore(tmp_path / "scanner.json")
    store.save(ScannerPreset.from_config("Zulu", "60", _config()))
    store.save(ScannerPreset.from_config("alpha", "60", _config()))
    assert [preset.name for preset in store.list()] == ["alpha", "Zulu"]

    updated = PatternConfig(max_body_ratio=0.2, min_candles=1, max_candles=3)
    store.save(ScannerPreset.from_config("alpha", "240", updated))
    loaded = store.get("alpha")
    assert loaded is not None
    assert loaded.timeframe == "240"
    assert loaded.config.max_body_ratio == pytest.approx(0.2)
    assert len(store.list()) == 2


def test_close_filters_roundtrip(tmp_path):
    store = PresetStore(tmp_path / "scanner.json")
    config = PatternConfig(
        require_close_above_avwap=True,
        require_close_above_vwap=True,
    )
    store.save(ScannerPreset.from_config("Above both", "60", config))

    loaded = store.get("Above both")
    assert loaded is not None
    assert loaded.config.require_close_above_avwap is True
    assert loaded.config.require_close_above_vwap is True


def test_legacy_preset_defaults_close_filters_off():
    raw = ScannerPreset.from_config("Old", "60", _config()).to_dict()
    raw.pop("require_close_above_avwap")
    raw.pop("require_close_above_vwap")
    preset = ScannerPreset.from_dict("Old", raw)
    assert preset.config.require_close_above_avwap is False
    assert preset.config.require_close_above_vwap is False


def test_delete_preset(tmp_path):
    store = PresetStore(tmp_path / "scanner.json")
    store.save(ScannerPreset.from_config("Delete me", "60", _config()))
    assert store.delete("Delete me") is True
    assert store.delete("Delete me") is False
    assert store.list() == []


def test_corrupt_preset_file_raises(tmp_path):
    path = tmp_path / "scanner.json"
    path.write_text("{not-json", encoding="utf-8")
    store = PresetStore(path)
    with pytest.raises(PresetError):
        store.list()


def test_invalid_preset_values_raise(tmp_path):
    path = tmp_path / "scanner.json"
    path.write_text(
        json.dumps(
            {
                "version": 1,
                "presets": {
                    "broken": {
                        "timeframe": "60",
                        "min_candles": 5,
                        "max_candles": 1,
                        "max_close_above_pct": 0.5,
                        "max_close_below_pct": 0.2,
                        "max_low_below_pct": 0.3,
                        "max_body_ratio": 0.35,
                        "max_window_range_pct": 2.0,
                        "use_atr": True,
                        "atr_multiple": 2.0,
                        "consolidation_range_pct": 1.0,
                        "allowed_patterns": list(PATTERN_TYPES),
                    }
                },
            }
        ),
        encoding="utf-8",
    )
    store = PresetStore(path)
    with pytest.raises(PresetError, match="invalid"):
        store.list()


def test_empty_preset_name_is_rejected():
    with pytest.raises(PresetError):
        ScannerPreset.from_config("   ", "60", _config())
