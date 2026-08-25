import pytest

from eba_trader.m5_factory import ParameterFamily
from eba_trader.m5_family import EMA_MOMENTUM, EMA_ORDERFLOW_MOMENTUM
from eba_trader.m5_hypothesis import (
    ComparisonOperator,
    Condition,
    StrategyHypothesis,
    TradeDirection,
)
from eba_trader.m5_selection import (
    CheapScreenPolicy,
    cheap_screen,
    rank_survivors,
)
from eba_trader.m5_similarity import hypothesis_similarity, remove_near_duplicates


def test_approved_family_templates_are_bounded_and_valid() -> None:
    baseline = EMA_MOMENTUM.build(
        version=1,
        direction=TradeDirection.LONG,
        timeframe="1m",
    )
    flow = EMA_ORDERFLOW_MOMENTUM.build(
        version=1,
        direction=TradeDirection.LONG,
        timeframe="1m",
    )
    baseline.validate()
    flow.validate()

    assert EMA_MOMENTUM.parameter_family.variant_count == 18
    assert EMA_ORDERFLOW_MOMENTUM.parameter_family.variant_count == 18
    assert all(not name.startswith("of_") for name in baseline.features)
    assert any(name.startswith("of_") for name in flow.features)


def test_near_duplicate_guard_ignores_threshold_only_variation() -> None:
    first = StrategyHypothesis(
        family="flow",
        version=1,
        direction=TradeDirection.LONG,
        timeframe="1m",
        features=("of_delta_ratio", "rsi"),
        entry_all=(
            Condition("of_delta_ratio", ComparisonOperator.GT, 0.1),
            Condition("rsi", ComparisonOperator.GT, 50.0),
        ),
    )
    second = StrategyHypothesis(
        family="flow",
        version=1,
        direction=TradeDirection.LONG,
        timeframe="1m",
        features=("of_delta_ratio", "rsi"),
        entry_all=(
            Condition("of_delta_ratio", ComparisonOperator.GT, 0.2),
            Condition("rsi", ComparisonOperator.GT, 55.0),
        ),
    )

    result = hypothesis_similarity(first, second)
    assert result.score == pytest.approx(1.0)
    assert result.near_duplicate is True
    assert remove_near_duplicates((first, second)) == (first,)


def test_different_direction_or_family_is_not_near_duplicate() -> None:
    long = EMA_ORDERFLOW_MOMENTUM.build(
        version=1,
        direction=TradeDirection.LONG,
        timeframe="1m",
    )
    short = EMA_ORDERFLOW_MOMENTUM.build(
        version=1,
        direction=TradeDirection.SHORT,
        timeframe="1m",
    )
    assert hypothesis_similarity(long, short).near_duplicate is False


def test_cheap_screen_blocks_excessive_parameter_fanout() -> None:
    hypothesis = EMA_MOMENTUM.build(
        version=1,
        direction=TradeDirection.LONG,
        timeframe="1m",
    )
    family = ParameterFamily({"x": tuple(range(30)), "y": tuple(range(10))})

    verdict = cheap_screen(
        hypothesis,
        family,
        policy=CheapScreenPolicy(max_parameter_variants=200),
    )
    assert verdict.passed is False
    assert verdict.reasons == ("too_many_parameter_variants",)


def test_survivor_ranking_is_deterministic_and_fail_closed() -> None:
    experiments = [
        {
            "experiment_id": "exp_b",
            "status": "passed",
            "metrics": {
                "profit_factor": 1.4,
                "expectancy": 0.3,
                "max_drawdown": -0.10,
                "trade_count": 50,
            },
        },
        {
            "experiment_id": "exp_a",
            "status": "passed",
            "metrics": {
                "profit_factor": 1.6,
                "expectancy": 0.2,
                "max_drawdown": -0.08,
                "trade_count": 40,
            },
        },
        {
            "experiment_id": "missing_metric",
            "status": "passed",
            "metrics": {"profit_factor": 99.0},
        },
        {
            "experiment_id": "failed",
            "status": "failed",
            "metrics": {
                "profit_factor": 100.0,
                "expectancy": 100.0,
                "max_drawdown": 0.0,
                "trade_count": 1000,
            },
        },
    ]

    ranked = rank_survivors(experiments)
    assert [item.experiment_id for item in ranked] == ["exp_a", "exp_b"]
    assert ranked[0].score > ranked[1].score
