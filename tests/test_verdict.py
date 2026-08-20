from __future__ import annotations

import json

from eba_trader.verdict import evaluate_development_report, write_development_verdict


def passing_report() -> dict[str, object]:
    return {
        "phase": "development_only",
        "oos_2025": "LOCKED_NOT_ACCESSED",
        "frozen_baseline": {"fast_ema": 20, "slow_ema": 50},
        "baseline": {
            "windows": {
                "validation": {
                    "scenarios": {
                        "base": {
                            "trade_count": 40,
                            "total_return": 0.15,
                            "expectancy": 4.0,
                            "profit_factor": 1.25,
                            "benchmark_relative_return": -0.05,
                            "max_drawdown": -0.15,
                            "benchmark_max_drawdown": -0.25,
                        },
                        "severe": {"total_return": 0.04},
                    }
                }
            }
        },
        "research_robustness": {
            "parameter_neighborhood": {"positive_expectancy_fraction": 0.67},
            "walk_forward": {
                "positive_test_fraction": 0.60,
                "positive_expectancy_fraction": 0.60,
                "drawdown_improvement_fraction": 0.70,
            },
        },
    }


def test_passing_report_is_eligible() -> None:
    gates = evaluate_development_report(passing_report())
    assert gates
    assert all(gate.passed for gate in gates)


def test_severe_cost_failure_rejects_cycle() -> None:
    report = passing_report()
    report["baseline"]["windows"]["validation"]["scenarios"]["severe"]["total_return"] = -0.01
    gates = evaluate_development_report(report)
    failed = {gate.name for gate in gates if not gate.passed}
    assert "validation_survives_severe_costs" in failed


def test_underperformance_requires_material_drawdown_advantage() -> None:
    report = passing_report()
    base = report["baseline"]["windows"]["validation"]["scenarios"]["base"]
    base["benchmark_relative_return"] = -0.20
    base["max_drawdown"] = -0.23
    base["benchmark_max_drawdown"] = -0.25
    gates = evaluate_development_report(report)
    failed = {gate.name for gate in gates if not gate.passed}
    assert "validation_return_or_material_risk_advantage" in failed


def test_beating_btc_return_satisfies_tradeoff_even_without_drawdown_advantage() -> None:
    report = passing_report()
    base = report["baseline"]["windows"]["validation"]["scenarios"]["base"]
    base["benchmark_relative_return"] = 0.01
    base["max_drawdown"] = -0.30
    base["benchmark_max_drawdown"] = -0.25
    gates = evaluate_development_report(report)
    tradeoff = next(
        gate
        for gate in gates
        if gate.name == "validation_return_or_material_risk_advantage"
    )
    assert tradeoff.passed is True


def test_verdict_file_records_report_hash_and_status(tmp_path) -> None:
    development = tmp_path / "development.json"
    development.write_text(json.dumps(passing_report(), sort_keys=True), encoding="utf-8")
    verdict_path = tmp_path / "verdict.json"
    verdict = write_development_verdict(
        development_report_path=development,
        verdict_path=verdict_path,
    )
    assert verdict["status"] == "ELIGIBLE_FOR_FROZEN_OOS"
    assert verdict["all_gates_passed"] is True
    assert verdict_path.exists()
