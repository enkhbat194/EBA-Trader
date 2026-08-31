from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .strategy_discovery_v2 import (
    DISCOVERY_AUTHORITY,
    MAX_CANDIDATES_PER_FAMILY,
    MAX_RAW_CANDIDATES,
    MAX_SURVIVORS,
    DiscoveryCampaignPolicy,
)

DEFAULT_FACTORY_V2_PILOT_CONFIG = Path("config/strategy_factory_v2_pilot_v1.json")


@dataclass(frozen=True, slots=True)
class FactoryV2PilotContract:
    policy: DiscoveryCampaignPolicy
    behavioral_similarity_threshold: float
    target_family_count_min: int
    target_family_count_max: int
    discovery_zone: str
    hidden_confirmation_zone: str
    robustness_zone: str
    frozen_oos_zone: str
    definition: Mapping[str, object]


def load_factory_v2_pilot_contract(
    path: str | Path = DEFAULT_FACTORY_V2_PILOT_CONFIG,
) -> FactoryV2PilotContract:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("factory v2 pilot config must be a JSON object")
    return factory_v2_pilot_contract_from_mapping(payload)


def factory_v2_pilot_contract_from_mapping(
    payload: Mapping[str, Any],
) -> FactoryV2PilotContract:
    if payload.get("schema") != "strategy_factory_v2_pilot_v1":
        raise ValueError("unsupported Strategy Factory v2 pilot schema")
    if payload.get("authority") != DISCOVERY_AUTHORITY:
        raise ValueError("Strategy Factory v2 pilot authority must remain DISCOVERY_ONLY")

    budget = _mapping(payload, "budget")
    raw_cap = _integer(budget, "raw_candidate_cap")
    family_cap = _integer(budget, "candidate_cap_per_family")
    survivor_cap = _integer(budget, "survivor_cap")
    if raw_cap > MAX_RAW_CANDIDATES:
        raise ValueError("pilot raw candidate cap exceeds hard safety maximum")
    if family_cap > MAX_CANDIDATES_PER_FAMILY:
        raise ValueError("pilot per-family cap exceeds hard safety maximum")
    if survivor_cap > MAX_SURVIVORS:
        raise ValueError("pilot survivor cap exceeds hard safety maximum")

    target_min = _integer(budget, "target_family_count_min")
    target_max = _integer(budget, "target_family_count_max")
    if target_min < 1 or target_max < target_min:
        raise ValueError("invalid target family count range")

    selection = _mapping(payload, "selection")
    threshold = _number(selection, "behavioral_similarity_threshold")
    if not 0.0 < threshold <= 1.0:
        raise ValueError("behavioral similarity threshold must be in (0, 1]")
    _require_true(selection, "structural_deduplication_required")
    _require_true(selection, "behavioral_deduplication_required")
    _require_false(selection, "discovery_priority_has_promotion_authority")

    zones = _mapping(payload, "data_zones")
    discovery_zone = _exact(zones, "discovery_corpus", "D0")
    confirmation_zone = _exact(zones, "hidden_confirmation", "D1")
    robustness_zone = _exact(zones, "robustness_reserve", "D2")
    frozen_zone = _exact(zones, "frozen_oos", "D3")
    _require_true(zones, "confirmation_must_be_hidden_until_survivor_freeze")
    _require_false(zones, "frozen_oos_allowed")

    evidence = _mapping(payload, "evidence")
    _require_true(evidence, "all_trials_must_be_ledgered")
    _require_true(evidence, "full_immutable_strategy_evidence_required_for_confirmation_survivors")
    _require_true(evidence, "dataset_hash_required")
    _require_true(evidence, "source_code_sha_required")
    _require_true(evidence, "candidate_spec_hash_required")

    safety = _mapping(payload, "safety")
    for key in (
        "may_transition_strategy_lifecycle",
        "may_open_frozen_oos",
        "may_enable_real_execution",
        "may_call_development_ranking_verified",
        "may_use_demo_as_verification_shortcut",
    ):
        _require_false(safety, key)
    _require_true(safety, "current_eba_verification_pipeline_must_remain_unchanged")

    search = _mapping(payload, "search")
    if search.get("primary_parameter_sampler") != "deterministic_quasi_random":
        raise ValueError("pilot sampler must remain deterministic_quasi_random")
    _require_false(search, "bayesian_optimization_authority")
    _require_false(search, "genetic_programming_authority")
    _require_false(search, "unrestricted_ai_code_generation_authority")

    policy = DiscoveryCampaignPolicy(
        campaign_id=str(payload.get("campaign_id") or ""),
        raw_candidate_cap=raw_cap,
        candidate_cap_per_family=family_cap,
        survivor_cap=survivor_cap,
        authority=str(payload.get("authority")),
    )
    return FactoryV2PilotContract(
        policy=policy,
        behavioral_similarity_threshold=threshold,
        target_family_count_min=target_min,
        target_family_count_max=target_max,
        discovery_zone=discovery_zone,
        hidden_confirmation_zone=confirmation_zone,
        robustness_zone=robustness_zone,
        frozen_oos_zone=frozen_zone,
        definition=dict(payload),
    )


def _mapping(payload: Mapping[str, Any], key: str) -> Mapping[str, Any]:
    value = payload.get(key)
    if not isinstance(value, Mapping):
        raise ValueError(f"{key} must be an object")
    return value


def _integer(payload: Mapping[str, Any], key: str) -> int:
    value = payload.get(key)
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"{key} must be an integer")
    return value


def _number(payload: Mapping[str, Any], key: str) -> float:
    value = payload.get(key)
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{key} must be numeric")
    return float(value)


def _exact(payload: Mapping[str, Any], key: str, expected: str) -> str:
    value = payload.get(key)
    if value != expected:
        raise ValueError(f"{key} must remain {expected}")
    return expected


def _require_true(payload: Mapping[str, Any], key: str) -> None:
    if payload.get(key) is not True:
        raise ValueError(f"{key} must remain true")


def _require_false(payload: Mapping[str, Any], key: str) -> None:
    if payload.get(key) is not False:
        raise ValueError(f"{key} must remain false")
