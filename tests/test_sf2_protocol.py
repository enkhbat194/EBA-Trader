from __future__ import annotations

import json
from pathlib import Path

import pytest

from eba_trader.m5_study_policy import (
    DEFAULT_M5_DEVELOPMENT_CORPUS,
    DEFAULT_M5_STUDY_POLICY,
)
from eba_trader.sf2_protocol import (
    ACTIVE_CANDIDATE_COUNT,
    ADJUSTED_ALPHA_MAX,
    FEE_BPS,
    MINIMUM_BASELINE_BEATING_WINDOWS,
    MINIMUM_TOTAL_TRADES,
    PLANNED_MULTIPLE_TESTING_BUDGET,
    SLIPPAGE_BPS,
    load_sf2_protocol,
)

ROOT = Path(__file__).resolve().parents[1]
PROTOCOL = ROOT / "config/sf2_research_protocol_v1.json"


def _overlap(start_a: int, end_a: int, start_b: int, end_b: int) -> bool:
    return start_a < end_b and end_a > start_b


def test_sf2_protocol_is_fresh_strict_and_preregistered() -> None:
    protocol = load_sf2_protocol(PROTOCOL)

    assert protocol.planned_candidate_budget == PLANNED_MULTIPLE_TESTING_BUDGET == 48
    assert len(protocol.candidates) == ACTIVE_CANDIDATE_COUNT == 24
    assert len(protocol.corpus.windows) == 12
    assert protocol.corpus.policy_id == DEFAULT_M5_STUDY_POLICY.policy_id
    assert protocol.protocol_id.startswith("sf2protocol_")

    for fresh in protocol.corpus.windows:
        assert DEFAULT_M5_STUDY_POLICY.development_start_ms <= fresh.start_ms
        assert fresh.end_ms <= DEFAULT_M5_STUDY_POLICY.development_end_ms
        assert not _overlap(
            fresh.start_ms,
            fresh.end_ms,
            DEFAULT_M5_STUDY_POLICY.frozen_oos_start_ms,
            DEFAULT_M5_STUDY_POLICY.frozen_oos_end_ms,
        )
        for sf1 in DEFAULT_M5_DEVELOPMENT_CORPUS.windows:
            assert not _overlap(fresh.start_ms, fresh.end_ms, sf1.start_ms, sf1.end_ms)


def test_sf2_protocol_keeps_user_quality_gate_unchanged() -> None:
    payload = json.loads(PROTOCOL.read_text(encoding="utf-8"))
    execution = payload["execution"]
    qualification = payload["qualification"]

    assert execution["fee_bps"] == FEE_BPS == 4.0
    assert execution["slippage_bps"] == SLIPPAGE_BPS == 1.5
    assert execution["signal_to_execution_delay_bars"] == 1
    assert qualification["minimum_mean_return_exclusive"] == 0.0
    assert qualification["minimum_mean_expectancy_exclusive"] == 0.0
    assert qualification["minimum_total_trades"] == MINIMUM_TOTAL_TRADES == 30
    assert qualification["minimum_baseline_beating_windows"] == (
        MINIMUM_BASELINE_BEATING_WINDOWS
    ) == 9
    assert qualification["adjusted_alpha_max"] == ADJUSTED_ALPHA_MAX == 0.05
    assert qualification["multiple_testing_method"] == "bonferroni"
    assert qualification["permutation_count"] == 4096


def test_sf2_protocol_allocates_four_independent_candidate_families() -> None:
    protocol = load_sf2_protocol(PROTOCOL)
    families: dict[str, int] = {}
    for candidate in protocol.candidates:
        families[candidate.family] = families.get(candidate.family, 0) + 1

    assert families == {
        "divergence_reversal_v1": 6,
        "absorption_reversal_v1": 6,
        "stacked_delta_continuation_v1": 6,
        "flow_price_continuation_v1": 6,
    }


def test_sf2_loader_rejects_reusing_an_sf1_window(tmp_path: Path) -> None:
    payload = json.loads(PROTOCOL.read_text(encoding="utf-8"))
    payload["development_windows"][0] = {
        "name": "bad-reuse",
        "start": "2026-07-02T00:00:00Z",
        "end": "2026-07-02T04:00:00Z",
    }
    path = tmp_path / "protocol.json"
    path.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(ValueError, match="reuses SF1 evidence"):
        load_sf2_protocol(path)


def test_sf2_loader_rejects_lowering_multiple_testing_budget(tmp_path: Path) -> None:
    payload = json.loads(PROTOCOL.read_text(encoding="utf-8"))
    payload["planned_candidate_budget"] = 24
    path = tmp_path / "protocol.json"
    path.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(ValueError, match="budget must remain 48"):
        load_sf2_protocol(path)


def test_sf2_loader_rejects_lowering_trade_requirement(tmp_path: Path) -> None:
    payload = json.loads(PROTOCOL.read_text(encoding="utf-8"))
    payload["qualification"]["minimum_total_trades"] = 20
    path = tmp_path / "protocol.json"
    path.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(ValueError, match="qualification gate was changed"):
        load_sf2_protocol(path)
