import pytest

from eba_trader.m5_factory import (
    MAX_PARAMETER_VARIANTS,
    ParameterFamily,
    StrategyCandidateFactory,
    deduplicate_hypotheses,
)
from eba_trader.m5_features import DEFAULT_FEATURE_REGISTRY
from eba_trader.m5_hypothesis import (
    ComparisonOperator,
    Condition,
    StrategyHypothesis,
    TradeDirection,
    hypothesis_from_mapping,
)


def _hypothesis(*, rationale: str = "test") -> StrategyHypothesis:
    return StrategyHypothesis(
        family="momentum_orderflow",
        version=1,
        direction=TradeDirection.LONG,
        timeframe="1m",
        features=("ema_fast", "ema_slow", "of_delta_ratio"),
        entry_all=(
            Condition("of_delta_ratio", ComparisonOperator.GT, 0.2),
            Condition("ema_fast", ComparisonOperator.GT, 0.0),
        ),
        rationale=rationale,
    )


def test_enabled_orderflow_features_are_allowed_and_future_features_fail_closed() -> None:
    assert DEFAULT_FEATURE_REGISTRY.require("of_delta").enabled is True
    with pytest.raises(ValueError, match="not enabled"):
        DEFAULT_FEATURE_REGISTRY.require("of_absorption")
    with pytest.raises(ValueError, match="unsupported feature"):
        DEFAULT_FEATURE_REGISTRY.require("magic_whale_detector")


def test_hypothesis_requires_declared_approved_features() -> None:
    hypothesis = _hypothesis()
    hypothesis.validate()

    invalid = StrategyHypothesis(
        family="bad",
        version=1,
        direction=TradeDirection.LONG,
        timeframe="1m",
        features=("ema_fast",),
        entry_all=(Condition("of_delta", ComparisonOperator.GT, 0.0),),
    )
    with pytest.raises(ValueError, match="not declared"):
        invalid.validate()


def test_mapping_parser_rejects_arbitrary_fields_and_disabled_features() -> None:
    payload = {
        "family": "flow",
        "version": 1,
        "direction": "long",
        "timeframe": "1m",
        "features": ["of_absorption"],
        "entry_all": [{"feature": "of_absorption", "operator": "gt", "value": 0.5}],
    }
    with pytest.raises(ValueError, match="not enabled"):
        hypothesis_from_mapping(payload)

    payload["python_code"] = "import os"
    with pytest.raises(ValueError, match="unsupported hypothesis fields"):
        hypothesis_from_mapping(payload)


def test_rationale_does_not_change_structural_fingerprint() -> None:
    first = _hypothesis(rationale="AI explanation A")
    second = _hypothesis(rationale="different prose")
    assert first.fingerprint == second.fingerprint
    assert deduplicate_hypotheses((first, second)) == (first,)


def test_parameter_family_expands_deterministically() -> None:
    family = ParameterFamily(
        {
            "delta_threshold": (0.1, 0.2),
            "ema_fast": (8, 13),
        }
    )
    first = StrategyCandidateFactory().expand(_hypothesis(), family)
    second = StrategyCandidateFactory().expand(_hypothesis(), family)

    assert first == second
    assert family.variant_count == 4
    assert [candidate.parameters for candidate in first] == [
        {"delta_threshold": 0.1, "ema_fast": 8},
        {"delta_threshold": 0.1, "ema_fast": 13},
        {"delta_threshold": 0.2, "ema_fast": 8},
        {"delta_threshold": 0.2, "ema_fast": 13},
    ]
    assert len({candidate.candidate_id for candidate in first}) == 4


def test_parameter_family_rejects_duplicate_values_and_excessive_fanout() -> None:
    with pytest.raises(ValueError, match="duplicate parameter candidates"):
        ParameterFamily({"x": (1, 1)})

    too_many = tuple(range(MAX_PARAMETER_VARIANTS + 1))
    with pytest.raises(ValueError, match="hard cap"):
        ParameterFamily({"x": too_many})
