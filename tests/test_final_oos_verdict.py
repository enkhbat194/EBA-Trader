from __future__ import annotations

from eba_trader.final_oos_verdict import evaluate_final_oos_report


def passing_report() -> dict[str, object]:
    base = {
        "trade_count": 30,
        "total_return": 0.05,
        "expectancy": 1.5,
        "profit_factor": 1.2,
        "average_win": 6.0,
        "average_loss": -4.0,
        "max_drawdown": -0.045,
        "max_planned_risk_fraction": 0.005,
        "average_notional_fraction": 0.30,
        "max_drawdown_halted": False,
    }
    severe = dict(base)
    severe.update({"total_return": 0.015, "max_drawdown": -0.06})
    return {
        "phase": "final_frozen_risk_execution_oos",
        "retuning_after_open": "forbidden",
        "rerun": "forbidden",
        "window": {"scenarios": {"base": base, "severe": severe}},
    }


def test_passing_oos_is_only_eligible_for_forward_paper() -> None:
    gates = evaluate_final_oos_report(passing_report())
    assert all(gate.passed for gate in gates)


def test_oos_loss_is_rejected() -> None:
    report = passing_report()
    report["window"]["scenarios"]["base"]["total_return"] = -0.01
    failed = {gate.name for gate in evaluate_final_oos_report(report) if not gate.passed}
    assert "oos_positive_return" in failed


def test_oos_hard_drawdown_halt_is_rejected() -> None:
    report = passing_report()
    base = report["window"]["scenarios"]["base"]
    base["max_drawdown"] = -0.081
    base["max_drawdown_halted"] = True
    failed = {gate.name for gate in evaluate_final_oos_report(report) if not gate.passed}
    assert "oos_no_hard_drawdown_halt" in failed


def test_oos_severe_cost_loss_is_rejected() -> None:
    report = passing_report()
    report["window"]["scenarios"]["severe"]["total_return"] = -0.001
    failed = {gate.name for gate in evaluate_final_oos_report(report) if not gate.passed}
    assert "oos_survives_severe_costs" in failed
