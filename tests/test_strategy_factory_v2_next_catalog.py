from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

import pytest

from eba_trader.strategy_factory_v2_next_catalog import (
    CATALOG_SEED,
    EXPECTED_CATALOG_SHA256,
    candidate_catalog_sha256,
    generate_next_campaign_candidates,
    load_next_candidate_catalog_freeze,
    next_campaign_family_plans,
)

CATALOG_PATH = Path("config/sfv2_next_candidate_catalog_v1.json")


def test_catalog_freeze_replays_exact_128_candidate_manifest() -> None:
    freeze = load_next_candidate_catalog_freeze(CATALOG_PATH)
    assert freeze.authority == "CATALOG_FREEZE_ONLY"
    assert freeze.performance_evaluation_allowed is False
    assert freeze.dataset_window_frozen is False
    assert freeze.candidate_count == 128
    assert freeze.catalog_sha256 == EXPECTED_CATALOG_SHA256
    assert candidate_catalog_sha256() == EXPECTED_CATALOG_SHA256


def test_catalog_generation_is_deterministic_unique_and_balanced() -> None:
    first = generate_next_campaign_candidates()
    second = generate_next_campaign_candidates()
    first_ids = [candidate.candidate_id for candidate in first]
    second_ids = [candidate.candidate_id for candidate in second]
    assert first_ids == second_ids
    assert len(first_ids) == len(set(first_ids)) == 128
    assert first_ids[0] == "dc_7f7e02dae0be6aa9ed10fcce"
    assert first_ids[-1] == "dc_9088249832c8c601489f4b9b"

    counts = Counter(candidate.family_id for candidate in first)
    assert counts == {
        "mtf_trend_pullback_v1": 32,
        "breakout_retest_entry_v1": 32,
        "path_efficiency_persistence_v1": 32,
        "low_turnover_flow_persistence_v1": 32,
    }


def test_catalog_family_spaces_are_bounded_and_nonadaptive() -> None:
    plans = next_campaign_family_plans()
    assert len(plans) == 4
    assert all(plan.sample_count == 32 for plan in plans)
    assert all(plan.sample_count <= plan.family.parameter_combination_count for plan in plans)
    assert all(plan.family.parameter_combination_count <= 100_000 for plan in plans)


def test_catalog_preserves_structural_lower_turnover_constraints() -> None:
    candidates = generate_next_campaign_candidates()
    for candidate in candidates:
        params = candidate.parameters
        assert int(params["minimum_hold_minutes"]) >= 30
        assert int(params["cooldown_minutes"]) >= 15
        assert int(params["max_hold_minutes"]) > int(params["minimum_hold_minutes"])
        if candidate.family_id == "low_turnover_flow_persistence_v1":
            assert int(params["minimum_hold_minutes"]) >= 60
            assert int(params["cooldown_minutes"]) >= 30
            assert int(params["long_flow_lookback_minutes"]) > int(
                params["short_flow_lookback_minutes"]
            )


def test_catalog_seed_cannot_be_changed() -> None:
    with pytest.raises(ValueError, match="seed is frozen"):
        generate_next_campaign_candidates(seed=f"{CATALOG_SEED}-changed")


def test_freeze_cannot_enable_evaluation(tmp_path: Path) -> None:
    payload = json.loads(CATALOG_PATH.read_text(encoding="utf-8"))
    payload["performance_evaluation_allowed"] = True
    path = tmp_path / "catalog.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(ValueError, match="cannot authorize performance evaluation"):
        load_next_candidate_catalog_freeze(path)


def test_freeze_cannot_reallocate_family_budget(tmp_path: Path) -> None:
    payload = json.loads(CATALOG_PATH.read_text(encoding="utf-8"))
    payload["family_allocations"]["mtf_trend_pullback_v1"] = 31
    payload["family_allocations"]["breakout_retest_entry_v1"] = 33
    path = tmp_path / "catalog.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(ValueError, match="family allocation changed"):
        load_next_candidate_catalog_freeze(path)


def test_freeze_hash_cannot_be_rewritten(tmp_path: Path) -> None:
    payload = json.loads(CATALOG_PATH.read_text(encoding="utf-8"))
    payload["expected_catalog_sha256"] = "0" * 64
    path = tmp_path / "catalog.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(ValueError, match="catalog hash changed"):
        load_next_candidate_catalog_freeze(path)
