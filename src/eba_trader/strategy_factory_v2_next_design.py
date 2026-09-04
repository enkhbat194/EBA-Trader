from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

DESIGN_SCHEMA = "sfv2_next_campaign_design_v1"
DESIGN_AUTHORITY = "DESIGN_ONLY"
EXPECTED_DESIGN_ID = "sfv2-next-existing-data-v1"
EXPECTED_CAMPAIGN_ID = "sfv2-existing-data-low-turnover-v1"
EXPECTED_PRIOR_CAMPAIGN_ID = "sfv2-discovery-pilot-v1"
EXPECTED_PRIOR_INSPECTED_CANDIDATES = 406
EXPECTED_RAW_CANDIDATE_CAP = 128
EXPECTED_CANDIDATE_CAP_PER_FAMILY = 32
EXPECTED_SURVIVOR_CAP = 12
EXPECTED_FAMILY_IDS = (
    "mtf_trend_pullback_v1",
    "breakout_retest_entry_v1",
    "path_efficiency_persistence_v1",
    "low_turnover_flow_persistence_v1",
)
EXPECTED_CURRENT_DATA_PLANES = (
    "usd_m_candles",
    "volume",
    "executed_orderflow",
)


@dataclass(frozen=True, slots=True)
class NextCampaignDesign:
    design_id: str
    campaign_id_reserved: str
    raw_candidate_cap: int
    candidate_cap_per_family: int
    survivor_cap: int
    family_ids: tuple[str, ...]
    authority: str = DESIGN_AUTHORITY
    enabled_for_evaluation: bool = False


def _object(value: object, *, name: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        raise ValueError(f"{name} must be an object")
    return value


def load_next_campaign_design(path: str | Path) -> NextCampaignDesign:
    """Load the versioned next-campaign design without granting evaluation authority.

    This loader intentionally accepts only the current design-only contract. Dataset-window
    freeze and exact candidate-catalog freeze remain separate prerequisites. Merely loading this
    file cannot register candidates, inspect performance, open D1/OOS, access SF4 prospective
    evidence or enable exchange execution.
    """

    try:
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError("cannot read Strategy Factory next-campaign design") from exc
    if not isinstance(payload, dict):
        raise ValueError("next-campaign design must be a JSON object")

    required = {
        "schema",
        "design_id",
        "authority",
        "enabled_for_evaluation",
        "campaign_id_reserved",
        "search_history",
        "budget",
        "family_slots",
        "horizon_policy",
        "data_policy",
        "excluded_post_hoc_extensions",
        "safety",
    }
    if set(payload) != required:
        raise ValueError("next-campaign design fields changed")
    if payload["schema"] != DESIGN_SCHEMA:
        raise ValueError("unsupported next-campaign design schema")
    if payload["design_id"] != EXPECTED_DESIGN_ID:
        raise ValueError("next-campaign design identity changed")
    if payload["authority"] != DESIGN_AUTHORITY:
        raise ValueError("next-campaign design must remain DESIGN_ONLY")
    if payload["enabled_for_evaluation"] is not False:
        raise ValueError("next-campaign design cannot authorize evaluation")
    if payload["campaign_id_reserved"] != EXPECTED_CAMPAIGN_ID:
        raise ValueError("reserved next-campaign identity changed")

    history = _object(payload["search_history"], name="search_history")
    if history.get("prior_campaign_id") != EXPECTED_PRIOR_CAMPAIGN_ID:
        raise ValueError("prior Strategy Factory campaign accounting changed")
    if history.get("prior_inspected_candidate_count") != EXPECTED_PRIOR_INSPECTED_CANDIDATES:
        raise ValueError("prior inspected candidate count changed")
    if history.get("prior_survivor_count") != 0:
        raise ValueError("first Strategy Factory survivor outcome changed")
    if history.get("prior_candidates_remain_in_multiple_testing_history") is not True:
        raise ValueError("prior inspected candidates must remain in search history")

    budget = _object(payload["budget"], name="budget")
    expected_budget = {
        "raw_candidate_cap": EXPECTED_RAW_CANDIDATE_CAP,
        "candidate_cap_per_family": EXPECTED_CANDIDATE_CAP_PER_FAMILY,
        "survivor_cap": EXPECTED_SURVIVOR_CAP,
        "unused_capacity_is_not_reallocatable_post_hoc": True,
    }
    if dict(budget) != expected_budget:
        raise ValueError("next-campaign search budget changed")

    slots = payload["family_slots"]
    if not isinstance(slots, list) or len(slots) != len(EXPECTED_FAMILY_IDS):
        raise ValueError("next-campaign family slots changed")
    family_ids: list[str] = []
    for item in slots:
        slot = _object(item, name="family slot")
        if set(slot) != {"family_id", "mechanism", "novelty_vs_failed_pilot", "data_planes"}:
            raise ValueError("next-campaign family-slot fields changed")
        family_id = str(slot["family_id"])
        mechanism = str(slot["mechanism"]).strip()
        novelty = str(slot["novelty_vs_failed_pilot"]).strip()
        data_planes = slot["data_planes"]
        if not mechanism or not novelty:
            raise ValueError("next-campaign family mechanism/novelty is required")
        if not isinstance(data_planes, list) or not data_planes:
            raise ValueError("next-campaign family data planes are required")
        if any(str(value) not in EXPECTED_CURRENT_DATA_PLANES for value in data_planes):
            raise ValueError("next-campaign family requests an unavailable data plane")
        family_ids.append(family_id)
    if tuple(family_ids) != EXPECTED_FAMILY_IDS:
        raise ValueError("next-campaign family identities changed")

    horizon = _object(payload["horizon_policy"], name="horizon_policy")
    if horizon.get("source_interval") != "1m":
        raise ValueError("next-campaign source interval changed")
    if horizon.get("causal_derived_intervals") != ["5m", "15m", "60m"]:
        raise ValueError("next-campaign causal derived intervals changed")
    if horizon.get("one_minute_impulse_reentry_prohibited") is not True:
        raise ValueError("next-campaign must prohibit one-minute impulse re-entry")
    if horizon.get("target_lower_turnover_than_first_d0") is not True:
        raise ValueError("next-campaign must retain the lower-turnover objective")

    data = _object(payload["data_policy"], name="data_policy")
    if data.get("allowed_current_planes") != list(EXPECTED_CURRENT_DATA_PLANES):
        raise ValueError("next-campaign allowed current data planes changed")
    for unavailable in (
        "historical_funding_available",
        "historical_open_interest_available",
        "historical_basis_available",
        "historical_resting_order_book_available",
    ):
        if data.get(unavailable) is not False:
            raise ValueError(f"{unavailable} cannot be claimed available by this design")
    if data.get("new_dataset_window_frozen") is not False:
        raise ValueError("dataset window is not frozen in the design package")
    if data.get("candidate_catalog_frozen") is not False:
        raise ValueError("candidate catalog is not frozen in the design package")
    if data.get("performance_evaluation_before_both_freezes") is not False:
        raise ValueError("performance evaluation must wait for both freezes")

    excluded = payload["excluded_post_hoc_extensions"]
    if not isinstance(excluded, list) or len(excluded) != 8:
        raise ValueError("failed-family post-hoc exclusion list changed")

    safety = _object(payload["safety"], name="safety")
    expected_safety = {
        "fresh_confirmation_evidence": False,
        "verification_authority": False,
        "d1_opened": False,
        "frozen_oos_opened": False,
        "sf4_data_access_allowed": False,
        "demo_promotion_allowed": False,
        "live_execution_allowed": False,
        "real_execution_allowed": False,
    }
    if dict(safety) != expected_safety:
        raise ValueError("next-campaign design safety boundary changed")

    return NextCampaignDesign(
        design_id=EXPECTED_DESIGN_ID,
        campaign_id_reserved=EXPECTED_CAMPAIGN_ID,
        raw_candidate_cap=EXPECTED_RAW_CANDIDATE_CAP,
        candidate_cap_per_family=EXPECTED_CANDIDATE_CAP_PER_FAMILY,
        survivor_cap=EXPECTED_SURVIVOR_CAP,
        family_ids=EXPECTED_FAMILY_IDS,
    )
