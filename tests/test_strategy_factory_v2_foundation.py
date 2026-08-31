import json
from pathlib import Path

import pytest

from eba_trader.strategy_factory_v2_config import (
    factory_v2_pilot_contract_from_mapping,
    load_factory_v2_pilot_contract,
)
from eba_trader.strategy_family_v2 import (
    ParameterAxis,
    StrategyDataPlane,
    StrategyFamilyRegistryV2,
    StrategyFamilyV2,
    deterministic_quasi_random_candidates,
)


def _family() -> StrategyFamilyV2:
    return StrategyFamilyV2(
        family_id="compression_expansion_v2",
        economic_mechanism="volatility compression followed by directional expansion",
        data_plane=StrategyDataPlane.PRICE_VOLUME,
        timeframe="5m",
        features=("realized_vol_short", "realized_vol_long", "price_return"),
        parameter_axes=(
            ParameterAxis("short_lookback", (8, 12, 16)),
            ParameterAxis("long_lookback", (32, 48, 64)),
            ParameterAxis("compression_ratio", (0.55, 0.65, 0.75)),
            ParameterAxis("minimum_price_return", (0.001, 0.0015)),
        ),
    )


def test_checked_in_pilot_contract_is_fail_closed() -> None:
    contract = load_factory_v2_pilot_contract()

    assert contract.policy.authority == "DISCOVERY_ONLY"
    assert contract.policy.raw_candidate_cap == 500
    assert contract.policy.candidate_cap_per_family == 64
    assert contract.policy.survivor_cap == 30
    assert contract.discovery_zone == "D0"
    assert contract.hidden_confirmation_zone == "D1"
    assert contract.robustness_zone == "D2"
    assert contract.frozen_oos_zone == "D3"


def test_pilot_contract_rejects_weakened_safety(tmp_path: Path) -> None:
    path = Path("config/strategy_factory_v2_pilot_v1.json")
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["safety"]["may_open_frozen_oos"] = True

    with pytest.raises(ValueError, match="may_open_frozen_oos"):
        factory_v2_pilot_contract_from_mapping(payload)

    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["budget"]["raw_candidate_cap"] = 501
    with pytest.raises(ValueError, match="raw candidate cap"):
        factory_v2_pilot_contract_from_mapping(payload)

    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["data_zones"]["hidden_confirmation"] = "D0"
    with pytest.raises(ValueError, match="hidden_confirmation"):
        factory_v2_pilot_contract_from_mapping(payload)


def test_family_registry_is_immutable() -> None:
    registry = StrategyFamilyRegistryV2()
    family = _family()
    registry.register(family)
    registry.register(family)
    assert registry.require(family.family_id) == family

    changed = StrategyFamilyV2(
        family_id=family.family_id,
        economic_mechanism=family.economic_mechanism,
        data_plane=family.data_plane,
        timeframe=family.timeframe,
        features=family.features,
        parameter_axes=(ParameterAxis("short_lookback", (5, 10)),),
    )
    with pytest.raises(ValueError, match="immutable"):
        registry.register(changed)


def test_deterministic_sampler_replays_without_performance_feedback() -> None:
    family = _family()
    first = deterministic_quasi_random_candidates(family, count=20, seed="pilot-seed")
    replay = deterministic_quasi_random_candidates(family, count=20, seed="pilot-seed")
    different_seed = deterministic_quasi_random_candidates(family, count=20, seed="other-seed")

    assert tuple(candidate.candidate_id for candidate in first) == tuple(
        candidate.candidate_id for candidate in replay
    )
    assert len({candidate.candidate_id for candidate in first}) == 20
    assert tuple(candidate.candidate_id for candidate in first) != tuple(
        candidate.candidate_id for candidate in different_seed
    )


def test_sampler_never_exceeds_declared_discrete_space() -> None:
    family = StrategyFamilyV2(
        family_id="tiny",
        economic_mechanism="test mechanism",
        data_plane=StrategyDataPlane.PRICE_VOLUME,
        timeframe="1m",
        features=("price_return",),
        parameter_axes=(
            ParameterAxis("a", (1, 2)),
            ParameterAxis("b", (10, 20)),
        ),
    )

    candidates = deterministic_quasi_random_candidates(family, count=64, seed="seed")

    assert len(candidates) == 4
    assert len({candidate.candidate_id for candidate in candidates}) == 4


def test_family_rejects_unbounded_parameter_space() -> None:
    with pytest.raises(ValueError, match="combination cap"):
        StrategyFamilyV2(
            family_id="too-large",
            economic_mechanism="test mechanism",
            data_plane=StrategyDataPlane.PRICE_VOLUME,
            timeframe="1m",
            features=("price_return",),
            parameter_axes=(
                ParameterAxis("a", tuple(range(500))),
                ParameterAxis("b", tuple(range(500))),
            ),
        )
