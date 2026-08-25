import pytest

from eba_trader.research_gates import (
    GateOperator,
    GateRule,
    GateSet,
    evaluate_gate_set,
)


def test_gate_set_evaluates_numeric_thresholds() -> None:
    gate_set = GateSet(
        name="development",
        version=1,
        rules=(
            GateRule("trades", "trade_count", GateOperator.GTE, 10),
            GateRule("drawdown", "max_drawdown", GateOperator.GTE, -0.20),
            GateRule("return", "total_return", GateOperator.GT, 0.0),
        ),
    )

    evaluation = evaluate_gate_set(
        gate_set,
        {"trade_count": 12, "max_drawdown": -0.12, "total_return": 0.08},
    )

    assert evaluation.passed is True
    assert all(result.passed for result in evaluation.results)
    assert gate_set.gate_set_id.startswith("gset_")
    assert len(gate_set.definition_sha256) == 64


def test_missing_or_non_finite_metric_fails_closed() -> None:
    gate_set = GateSet(
        name="development",
        version=1,
        rules=(
            GateRule("pf", "profit_factor", GateOperator.GTE, 1.1),
            GateRule("trades", "trade_count", GateOperator.GTE, 5),
        ),
    )

    missing = evaluate_gate_set(gate_set, {"trade_count": 10})
    non_finite = evaluate_gate_set(
        gate_set,
        {"profit_factor": float("inf"), "trade_count": 10},
    )

    assert missing.passed is False
    assert missing.results[0].reason == "metric_missing_or_non_numeric"
    assert non_finite.passed is False
    assert non_finite.results[0].reason == "metric_non_finite"


def test_gate_set_mapping_is_fail_closed() -> None:
    gate_set = GateSet.from_mapping(
        {
            "name": "development",
            "version": 2,
            "rules": [
                {
                    "name": "trades",
                    "metric": "trade_count",
                    "operator": "gte",
                    "threshold": 20,
                }
            ],
        }
    )
    assert gate_set.version == 2
    assert gate_set.rules[0].operator is GateOperator.GTE

    with pytest.raises(ValueError, match="Unsupported gate set fields"):
        GateSet.from_mapping(
            {
                "name": "development",
                "version": 2,
                "rules": [],
                "unexpected": True,
            }
        )
