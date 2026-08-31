from __future__ import annotations

import json
from pathlib import Path

import pytest

from eba_trader.m5_study_policy import DEFAULT_M5_DEVELOPMENT_CORPUS
from eba_trader.sf2_protocol import load_sf2_protocol
from eba_trader.sf3_protocol import load_sf3_protocol

SF2_PATH = Path("config/sf2_research_protocol_v1.json")
SF3_PATH = Path("config/sf3_research_protocol_v1.json")


def _overlap(start_a: int, end_a: int, start_b: int, end_b: int) -> bool:
    return start_a < end_b and end_a > start_b


def _write_mutated(tmp_path: Path, payload: dict[str, object]) -> Path:
    sf2_target = tmp_path / SF2_PATH.name
    sf2_target.write_text(SF2_PATH.read_text(encoding="utf-8"), encoding="utf-8")
    sf3_target = tmp_path / SF3_PATH.name
    sf3_target.write_text(json.dumps(payload), encoding="utf-8")
    return sf3_target


def test_sf3_protocol_is_fresh_locked_and_conservative() -> None:
    sf3 = load_sf3_protocol(SF3_PATH)
    sf2 = load_sf2_protocol(SF2_PATH)

    assert sf3.phase_id == "sf3_fresh_development_v1"
    assert sf3.source_phase == "sf2_fresh_development_v1"
    assert sf3.planned_candidate_budget == 48
    assert sf3.warmup_bars == 96
    assert len(sf3.candidates) == 24
    assert len(sf3.corpus.windows) == 12

    prior = DEFAULT_M5_DEVELOPMENT_CORPUS.windows + sf2.corpus.windows
    for window in sf3.corpus.windows:
        for used in prior:
            assert not _overlap(
                window.start_ms,
                window.end_ms,
                used.start_ms,
                used.end_ms,
            )

    families: dict[str, int] = {}
    for candidate in sf3.candidates:
        families[candidate.family] = families.get(candidate.family, 0) + 1
    assert families == {
        "rolling_flow_trend_v1": 6,
        "volume_shock_momentum_v1": 6,
        "vwap_reversion_flow_v1": 6,
        "compression_expansion_v1": 6,
    }


def test_sf3_rejects_weakened_quality_gate(tmp_path: Path) -> None:
    payload = json.loads(SF3_PATH.read_text(encoding="utf-8"))
    payload["qualification"]["minimum_total_trades"] = 20
    path = _write_mutated(tmp_path, payload)

    with pytest.raises(ValueError, match="qualification gate was changed"):
        load_sf3_protocol(path)


def test_sf3_rejects_sf2_window_reuse(tmp_path: Path) -> None:
    payload = json.loads(SF3_PATH.read_text(encoding="utf-8"))
    sf2_payload = json.loads(SF2_PATH.read_text(encoding="utf-8"))
    payload["development_windows"][0] = dict(sf2_payload["development_windows"][0])
    payload["development_windows"][0]["name"] = "sf3-reused-sf2"
    path = _write_mutated(tmp_path, payload)

    with pytest.raises(ValueError, match="reuses prior phase evidence"):
        load_sf3_protocol(path)


def test_sf3_rejects_original_smoke_day(tmp_path: Path) -> None:
    payload = json.loads(SF3_PATH.read_text(encoding="utf-8"))
    payload["development_windows"][7] = {
        "name": "sf3-smoke-reuse",
        "start": "2026-08-01T04:00:00Z",
        "end": "2026-08-01T08:00:00Z",
    }
    path = _write_mutated(tmp_path, payload)

    with pytest.raises(ValueError, match="original smoke day"):
        load_sf3_protocol(path)


def test_sf3_rejects_frozen_oos_window(tmp_path: Path) -> None:
    payload = json.loads(SF3_PATH.read_text(encoding="utf-8"))
    payload["development_windows"][11] = {
        "name": "sf3-oos-reuse",
        "start": "2026-08-15T00:00:00Z",
        "end": "2026-08-15T04:00:00Z",
    }
    path = _write_mutated(tmp_path, payload)

    with pytest.raises(RuntimeError, match="sealed M5 frozen OOS"):
        load_sf3_protocol(path)
