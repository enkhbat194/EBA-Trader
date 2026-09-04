from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from .research_evidence import canonical_json, sha256_text
from .strategy_discovery_v2 import DiscoveryCandidate
from .strategy_factory_v2_next_design import (
    EXPECTED_CANDIDATE_CAP_PER_FAMILY,
    EXPECTED_CAMPAIGN_ID,
    EXPECTED_FAMILY_IDS,
    EXPECTED_PRIOR_INSPECTED_CANDIDATES,
    EXPECTED_RAW_CANDIDATE_CAP,
)
from .strategy_factory_v2_next_families import (
    BreakoutRetestConfig,
    LowTurnoverFlowPersistenceConfig,
    MtfTrendPullbackConfig,
    PathEfficiencyConfig,
)
from .strategy_family_v2 import (
    ParameterAxis,
    StrategyDataPlane,
    StrategyFamilyV2,
    deterministic_quasi_random_candidates,
)

CATALOG_SCHEMA = "sfv2_next_candidate_catalog_v1"
CATALOG_AUTHORITY = "CATALOG_FREEZE_ONLY"
CATALOG_SEED = "sfv2-existing-data-low-turnover-v1-catalog-v1"
EXPECTED_CATALOG_SHA256 = (
    "0aa793ca70ba8719486ba6edae314c77803e1b87884665d17ec88019ec71654a"
)
EXPECTED_PLAN_COUNT = 4
EXPECTED_SAMPLE_PER_FAMILY = 32
EXPECTED_TOTAL_CANDIDATES = 128


@dataclass(frozen=True, slots=True)
class NextCatalogPlan:
    family: StrategyFamilyV2
    sample_count: int

    def __post_init__(self) -> None:
        if not 1 <= self.sample_count <= EXPECTED_CANDIDATE_CAP_PER_FAMILY:
            raise ValueError("next-campaign sample count exceeds the frozen per-family cap")
        if self.sample_count > self.family.parameter_combination_count:
            raise ValueError("sample count exceeds the declared family parameter space")


@dataclass(frozen=True, slots=True)
class NextCandidateCatalogFreeze:
    campaign_id: str
    seed: str
    candidate_count: int
    catalog_sha256: str
    authority: str = CATALOG_AUTHORITY
    performance_evaluation_allowed: bool = False
    dataset_window_frozen: bool = False


def next_campaign_family_plans() -> tuple[NextCatalogPlan, ...]:
    plans = (
        NextCatalogPlan(
            family=StrategyFamilyV2(
                family_id="mtf_trend_pullback_v1",
                economic_mechanism=(
                    "higher-timeframe directional regime with lower-timeframe pullback entry"
                ),
                data_plane=StrategyDataPlane.PRICE_VOLUME,
                timeframe="1m source / 5m+15m derived",
                features=(
                    "ohlcv",
                    "closed_5m_return",
                    "closed_15m_regime",
                    "causal_pullback_resume",
                ),
                parameter_axes=(
                    ParameterAxis("side", (-1, 1)),
                    ParameterAxis("regime_lookback_15m", (8, 12, 16, 24)),
                    ParameterAxis("pullback_lookback_5m", (3, 6, 9)),
                    ParameterAxis(
                        "minimum_regime_return",
                        (0.001, 0.002, 0.004),
                    ),
                    ParameterAxis(
                        "minimum_pullback_return",
                        (0.0005, 0.001, 0.002),
                    ),
                    ParameterAxis(
                        "minimum_resume_return",
                        (0.0, 0.0005, 0.001),
                    ),
                    ParameterAxis("minimum_hold_minutes", (30, 60, 120)),
                    ParameterAxis("max_hold_minutes", (180, 360, 720)),
                    ParameterAxis("cooldown_minutes", (15, 30, 60)),
                ),
            ),
            sample_count=EXPECTED_SAMPLE_PER_FAMILY,
        ),
        NextCatalogPlan(
            family=StrategyFamilyV2(
                family_id="breakout_retest_entry_v1",
                economic_mechanism=(
                    "range break followed by causal post-break retest entry"
                ),
                data_plane=StrategyDataPlane.PRICE_VOLUME,
                timeframe="1m source / 5m+15m derived",
                features=(
                    "ohlcv",
                    "closed_15m_range",
                    "closed_5m_breakout",
                    "later_closed_5m_retest",
                ),
                parameter_axes=(
                    ParameterAxis("side", (-1, 1)),
                    ParameterAxis("range_lookback_15m", (8, 12, 16, 24)),
                    ParameterAxis(
                        "minimum_breakout_bps",
                        (5.0, 10.0, 20.0),
                    ),
                    ParameterAxis(
                        "retest_tolerance_bps",
                        (5.0, 10.0, 20.0),
                    ),
                    ParameterAxis("max_retest_wait_5m", (3, 6, 12)),
                    ParameterAxis("minimum_hold_minutes", (30, 60, 120)),
                    ParameterAxis("max_hold_minutes", (180, 360, 720)),
                    ParameterAxis("cooldown_minutes", (15, 30, 60)),
                ),
            ),
            sample_count=EXPECTED_SAMPLE_PER_FAMILY,
        ),
        NextCatalogPlan(
            family=StrategyFamilyV2(
                family_id="path_efficiency_persistence_v1",
                economic_mechanism=(
                    "directional path-efficiency persistence relative to realized path noise"
                ),
                data_plane=StrategyDataPlane.PRICE_VOLUME,
                timeframe="1m source / 15m derived",
                features=(
                    "ohlcv",
                    "closed_15m_path",
                    "path_efficiency",
                    "directional_return",
                ),
                parameter_axes=(
                    ParameterAxis("side", (-1, 1)),
                    ParameterAxis("lookback_15m", (8, 12, 16, 24)),
                    ParameterAxis("minimum_efficiency", (0.30, 0.50, 0.70)),
                    ParameterAxis(
                        "minimum_directional_return",
                        (0.001, 0.002, 0.004),
                    ),
                    ParameterAxis("minimum_hold_minutes", (30, 60, 120)),
                    ParameterAxis("max_hold_minutes", (180, 360, 720)),
                    ParameterAxis("cooldown_minutes", (15, 30, 60)),
                ),
            ),
            sample_count=EXPECTED_SAMPLE_PER_FAMILY,
        ),
        NextCatalogPlan(
            family=StrategyFamilyV2(
                family_id="low_turnover_flow_persistence_v1",
                economic_mechanism=(
                    "multi-window executed-flow persistence with explicit cooldown and "
                    "minimum holding horizon"
                ),
                data_plane=StrategyDataPlane.HYBRID,
                timeframe="1m source / 15m decisions",
                features=(
                    "ohlcv",
                    "of_buy_volume",
                    "of_sell_volume",
                    "of_delta",
                    "short_long_flow_ratio",
                ),
                parameter_axes=(
                    ParameterAxis("side", (-1, 1)),
                    ParameterAxis(
                        "short_flow_lookback_minutes",
                        (15, 30, 45),
                    ),
                    ParameterAxis(
                        "long_flow_lookback_minutes",
                        (120, 240, 360),
                    ),
                    ParameterAxis("price_lookback_minutes", (30, 60, 120)),
                    ParameterAxis(
                        "minimum_short_flow_ratio",
                        (0.02, 0.05, 0.08),
                    ),
                    ParameterAxis(
                        "minimum_long_flow_ratio",
                        (0.01, 0.03, 0.05),
                    ),
                    ParameterAxis(
                        "minimum_directional_price_return",
                        (0.0, 0.001, 0.002),
                    ),
                    ParameterAxis("minimum_hold_minutes", (60, 120, 240)),
                    ParameterAxis("max_hold_minutes", (360, 720, 1440)),
                    ParameterAxis("cooldown_minutes", (30, 60, 120)),
                ),
            ),
            sample_count=EXPECTED_SAMPLE_PER_FAMILY,
        ),
    )
    _validate_plan(plans)
    return plans


def _validate_plan(plans: tuple[NextCatalogPlan, ...]) -> None:
    if len(plans) != EXPECTED_PLAN_COUNT:
        raise ValueError("next-campaign catalog must contain exactly four family plans")
    ids = tuple(plan.family.family_id for plan in plans)
    if ids != EXPECTED_FAMILY_IDS:
        raise ValueError("next-campaign catalog family order/identity changed")
    if sum(plan.sample_count for plan in plans) != EXPECTED_TOTAL_CANDIDATES:
        raise ValueError("next-campaign planned candidate count changed")
    if EXPECTED_TOTAL_CANDIDATES > EXPECTED_RAW_CANDIDATE_CAP:
        raise ValueError("next-campaign catalog exceeds its frozen raw-candidate cap")


def _validate_candidate_parameters(candidate: DiscoveryCandidate) -> None:
    params = dict(candidate.parameters)
    if candidate.family_id == "mtf_trend_pullback_v1":
        MtfTrendPullbackConfig(**params)
    elif candidate.family_id == "breakout_retest_entry_v1":
        BreakoutRetestConfig(**params)
    elif candidate.family_id == "path_efficiency_persistence_v1":
        PathEfficiencyConfig(**params)
    elif candidate.family_id == "low_turnover_flow_persistence_v1":
        LowTurnoverFlowPersistenceConfig(**params)
    else:
        raise ValueError("candidate family is outside the next-campaign freeze")


def generate_next_campaign_candidates(
    *,
    seed: str = CATALOG_SEED,
) -> tuple[DiscoveryCandidate, ...]:
    if seed != CATALOG_SEED:
        raise ValueError("next-campaign catalog seed is frozen")
    candidates: list[DiscoveryCandidate] = []
    for plan in next_campaign_family_plans():
        family_seed = f"{seed}:{plan.family.family_id}"
        generated = deterministic_quasi_random_candidates(
            plan.family,
            count=plan.sample_count,
            seed=family_seed,
        )
        for candidate in generated:
            _validate_candidate_parameters(candidate)
        candidates.extend(generated)

    ids = tuple(candidate.candidate_id for candidate in candidates)
    if len(ids) != EXPECTED_TOTAL_CANDIDATES:
        raise RuntimeError("next-campaign deterministic catalog count changed")
    if len(ids) != len(set(ids)):
        raise RuntimeError("next-campaign deterministic catalog contains duplicate ids")
    return tuple(candidates)


def candidate_catalog_payload() -> dict[str, object]:
    candidates = generate_next_campaign_candidates()
    return {
        "schema": CATALOG_SCHEMA,
        "seed": CATALOG_SEED,
        "candidates": [
            {
                "candidate_id": candidate.candidate_id,
                **candidate.specification,
            }
            for candidate in candidates
        ],
    }


def candidate_catalog_sha256() -> str:
    digest = sha256_text(canonical_json(candidate_catalog_payload()))
    if digest != EXPECTED_CATALOG_SHA256:
        raise RuntimeError("next-campaign candidate catalog hash changed")
    return digest


def load_next_candidate_catalog_freeze(
    path: str | Path,
) -> NextCandidateCatalogFreeze:
    try:
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError("cannot read next-campaign catalog freeze") from exc
    if not isinstance(payload, dict):
        raise ValueError("next-campaign catalog freeze must be an object")

    expected_fields = {
        "schema",
        "design_id",
        "campaign_id",
        "authority",
        "seed",
        "family_allocations",
        "prior_inspected_candidate_count",
        "planned_raw_candidate_count",
        "cumulative_search_history_count_after_run",
        "expected_catalog_sha256",
        "dataset_window_frozen",
        "performance_evaluation_allowed",
        "safety",
    }
    if set(payload) != expected_fields:
        raise ValueError("next-campaign catalog freeze fields changed")
    if payload["schema"] != CATALOG_SCHEMA:
        raise ValueError("unsupported next-campaign catalog freeze schema")
    if payload["design_id"] != "sfv2-next-existing-data-v1":
        raise ValueError("next-campaign design identity changed")
    if payload["campaign_id"] != EXPECTED_CAMPAIGN_ID:
        raise ValueError("next-campaign identity changed")
    if payload["authority"] != CATALOG_AUTHORITY:
        raise ValueError("candidate catalog freeze cannot grant evaluation authority")
    if payload["seed"] != CATALOG_SEED:
        raise ValueError("candidate catalog seed changed")

    expected_allocations = {
        family_id: EXPECTED_SAMPLE_PER_FAMILY for family_id in EXPECTED_FAMILY_IDS
    }
    if payload["family_allocations"] != expected_allocations:
        raise ValueError("candidate family allocation changed")
    if payload["prior_inspected_candidate_count"] != EXPECTED_PRIOR_INSPECTED_CANDIDATES:
        raise ValueError("prior inspected candidate accounting changed")
    if payload["planned_raw_candidate_count"] != EXPECTED_TOTAL_CANDIDATES:
        raise ValueError("planned raw candidate count changed")
    expected_cumulative = EXPECTED_PRIOR_INSPECTED_CANDIDATES + EXPECTED_TOTAL_CANDIDATES
    if payload["cumulative_search_history_count_after_run"] != expected_cumulative:
        raise ValueError("cumulative search-history accounting changed")
    if payload["expected_catalog_sha256"] != EXPECTED_CATALOG_SHA256:
        raise ValueError("frozen candidate catalog hash changed")
    if payload["dataset_window_frozen"] is not False:
        raise ValueError("catalog freeze cannot claim the dataset window is frozen")
    if payload["performance_evaluation_allowed"] is not False:
        raise ValueError("catalog freeze cannot authorize performance evaluation")

    expected_safety = {
        "d1_opened": False,
        "frozen_oos_opened": False,
        "sf4_data_access_allowed": False,
        "demo_promotion_allowed": False,
        "live_execution_allowed": False,
        "real_execution_allowed": False,
    }
    if payload["safety"] != expected_safety:
        raise ValueError("candidate catalog safety boundary changed")

    catalog_hash = candidate_catalog_sha256()
    return NextCandidateCatalogFreeze(
        campaign_id=EXPECTED_CAMPAIGN_ID,
        seed=CATALOG_SEED,
        candidate_count=EXPECTED_TOTAL_CANDIDATES,
        catalog_sha256=catalog_hash,
    )
