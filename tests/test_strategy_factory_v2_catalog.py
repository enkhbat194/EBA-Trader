from __future__ import annotations

from collections import Counter

from eba_trader.atr_backtest import AtrTrailingConfig
from eba_trader.breakout_backtest import DonchianBreakoutConfig
from eba_trader.mean_reversion_backtest import MeanReversionConfig
from eba_trader.orderflow_impulse_backtest import OrderFlowDeltaImpulseConfig
from eba_trader.strategy_discovery_v2 import MAX_CANDIDATES_PER_FAMILY, MAX_RAW_CANDIDATES
from eba_trader.strategy_factory_v2_catalog import (
    generate_pilot_candidates,
    pilot_family_plans,
    planned_raw_candidate_count,
)


def test_pilot_catalog_uses_eight_families_without_forcing_full_cap() -> None:
    plans = pilot_family_plans()
    assert len(plans) == 8
    assert planned_raw_candidate_count() == 406
    assert planned_raw_candidate_count() < MAX_RAW_CANDIDATES == 500
    assert len({plan.family.family_id for plan in plans}) == len(plans)
    assert all(plan.sample_count <= MAX_CANDIDATES_PER_FAMILY for plan in plans)
    assert all(plan.sample_count <= plan.family.parameter_combination_count for plan in plans)


def test_pilot_generation_is_deterministic_unique_and_matches_family_allocations() -> None:
    first = generate_pilot_candidates(seed="catalog-test-seed")
    replay = generate_pilot_candidates(seed="catalog-test-seed")
    assert len(first) == 406
    assert [candidate.candidate_id for candidate in first] == [
        candidate.candidate_id for candidate in replay
    ]
    assert len({candidate.candidate_id for candidate in first}) == len(first)

    observed = Counter(candidate.family_id for candidate in first)
    expected = {plan.family.family_id: plan.sample_count for plan in pilot_family_plans()}
    assert dict(observed) == expected


def test_price_and_direct_orderflow_parameter_spaces_are_engine_valid() -> None:
    candidates = generate_pilot_candidates(seed="engine-validation-seed")
    for candidate in candidates:
        parameters = dict(candidate.parameters)
        if candidate.family_id == "atr_trailing_v1":
            AtrTrailingConfig(**parameters)
        elif candidate.family_id == "donchian_breakout_v1":
            DonchianBreakoutConfig(**parameters)
        elif candidate.family_id == "mean_reversion_z_v1":
            MeanReversionConfig(**parameters)
        elif candidate.family_id == "orderflow_delta_impulse_v1":
            OrderFlowDeltaImpulseConfig(**parameters)


def test_catalog_preserves_mechanism_and_data_plane_diversity() -> None:
    plans = pilot_family_plans()
    mechanisms = {plan.family.economic_mechanism for plan in plans}
    data_planes = {plan.family.data_plane.value for plan in plans}
    assert len(mechanisms) == len(plans)
    assert {"price_volume", "executed_order_flow", "hybrid"}.issubset(data_planes)
