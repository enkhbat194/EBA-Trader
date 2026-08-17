from __future__ import annotations

import json

import pytest

from eba_trader.execution_policy import EXECUTION_POLICY_NAME, EXECUTION_POLICY_VERSION
from eba_trader.risk_verdict import evaluate_risk_execution_report, write_risk_execution_verdict

COSTS = {
    "base": {"fee_bps": 10.0, "slippage_bps": 5.0},
    "adverse": {"fee_bps": 10.0, "slippage_bps": 10.0},
    "severe": {"fee_bps": 15.0, "slippage_bps": 20.0},
}


def passing_report() -> dict[str, object]:
    base = {
        "trade_count": 40,
        "total_return": 0.08,
        "expectancy": 2.0,
        "profit_factor": 1.3,
        "average_win": 7.0,
        "average_loss": -4.0,
        "max_drawdown": -0.04,
        "max_planned_risk_fraction": 0.005,
        "average_notional_fraction": 0.35,
        "max_drawdown_halted": False,
    }
    severe = dict(base)
    severe.update({"total_return": 0.025, "max_drawdown": -0.055})
    return {
        "phase": "risk_execution_development",
        "oos_2025": "LOCKED_NOT_ACCESSED",
        "source_provenance": {
            "git_commit": "0123456789abcdef0123456789abcdef01234567",
            "tracked_working_tree_clean": True,
        },
        "symbol": "BTCUSDT",
        "interval": "15m",
        "initial_cash": 1000.0,
        "strategy": {"fast_ema": 20, "slow_ema": 50},
        "execution_policy": {
            "version": EXECUTION_POLICY_VERSION,
            "name": EXECUTION_POLICY_NAME,
            "atr_period": 14,
            "atr_multiplier": 2.0,
            "risk_fraction": 0.005,
            "daily_loss_limit": 0.02,
            "max_drawdown_halt": 0.08,
            "spot_only": True,
            "leverage": 1.0,
            "take_profit": None,
            "normal_exit": "EMA cross-down at next bar open",
            "protective_exit": "ATR stop; adverse gaps execute at available bar open",
        },
        "cost_scenarios": COSTS,
        "windows": {
            "validation": {
                "scenarios": {
                    "base": base,
                    "severe": severe,
                }
            }
        },
    }


def test_passing_risk_report_is_eligible() -> None:
    gates = evaluate_risk_execution_report(passing_report())
    assert gates
    assert all(gate.passed for gate in gates)


def test_risk_above_half_percent_rejects() -> None:
    report = passing_report()
    report["windows"]["validation"]["scenarios"]["base"]["max_planned_risk_fraction"] = 0.0051
    failed = {
        gate.name for gate in evaluate_risk_execution_report(report) if not gate.passed
    }
    assert "validation_planned_risk_cap" in failed


def test_hard_drawdown_halt_rejects_even_if_return_positive() -> None:
    report = passing_report()
    base = report["windows"]["validation"]["scenarios"]["base"]
    base["max_drawdown"] = -0.081
    base["max_drawdown_halted"] = True
    failed = {
        gate.name for gate in evaluate_risk_execution_report(report) if not gate.passed
    }
    assert "validation_no_hard_drawdown_halt" in failed


def test_severe_cost_loss_rejects() -> None:
    report = passing_report()
    severe = report["windows"]["validation"]["scenarios"]["severe"]
    severe["total_return"] = -0.01
    failed = {
        gate.name for gate in evaluate_risk_execution_report(report) if not gate.passed
    }
    assert "validation_survives_severe_costs" in failed


def test_execution_policy_mutation_rejects_before_metrics() -> None:
    report = passing_report()
    report["execution_policy"]["risk_fraction"] = 0.01
    with pytest.raises(ValueError, match="predeclared snapshot"):
        evaluate_risk_execution_report(report)


def test_risk_verdict_records_evidence_hash(tmp_path) -> None:
    evidence = tmp_path / "risk.json"
    evidence.write_text(json.dumps(passing_report(), sort_keys=True), encoding="utf-8")
    verdict_path = tmp_path / "verdict.json"
    verdict = write_risk_execution_verdict(
        evidence_path=evidence,
        verdict_path=verdict_path,
    )
    assert verdict["status"] == "ELIGIBLE_FOR_FINAL_FROZEN_OOS"
    assert verdict["all_gates_passed"] is True
    assert verdict_path.exists()
