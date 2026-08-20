from __future__ import annotations

from dataclasses import replace

from eba_trader.v3_pullback import V3PullbackResult
from eba_trader.v3_pullback_evidence import (
    FoldResult,
    NeighborhoodResult,
    blocked_risk_gates,
    evaluate_risk_gates,
    evaluate_signal_gates,
)


def _result(**changes) -> V3PullbackResult:
    values = {
        "layer": "signal_allocation",
        "initial_cash": 1000.0,
        "final_equity": 1100.0,
        "total_return": 0.10,
        "annualized_return": 0.10,
        "benchmark_return": 0.20,
        "benchmark_max_drawdown": -0.30,
        "benchmark_relative_return": -0.10,
        "max_drawdown": -0.10,
        "trade_count": 25,
        "win_rate": 0.50,
        "profit_factor": 1.20,
        "expectancy": 1.0,
        "average_win": 2.0,
        "average_loss": -1.0,
        "sharpe": 1.0,
        "sortino": 1.0,
        "time_exposure": 0.20,
        "average_notional_fraction": 0.20,
        "max_notional_fraction": 0.50,
        "max_planned_risk_fraction": 0.0035,
        "total_cost": 100.0,
        "stop_out_count": 1,
        "target_exit_count": 1,
        "time_exit_count": 1,
        "regime_exit_count": 1,
        "daily_halt_count": 0,
        "max_drawdown_halted": False,
        "entry_invariant_violations": 0,
        "veto_entry_violations": 0,
        "effective_start_ms": 0,
        "effective_end_exclusive_ms": 1,
        "trades": (),
    }
    values.update(changes)
    return V3PullbackResult(**values)


def test_all_21_signal_gates_pass_on_qualifying_fixture() -> None:
    validation = _result()
    severe = _result(total_return=0.05, expectancy=0.5)
    control = _result(
        expectancy=0.5,
        profit_factor=1.20,
        max_drawdown=-0.10,
        total_cost=100.0,
    )
    neighborhood = tuple(
        NeighborhoodResult(f"variant_{index}", _result(), severe)
        for index in range(9)
    )
    folds = tuple(FoldResult(index, index + 1, _result()) for index in range(10))

    gates = evaluate_signal_gates(validation, severe, control, neighborhood, folds)

    assert len(gates) == 21
    assert [gate.number for gate in gates] == list(range(1, 22))
    assert all(gate.status == "PASS" for gate in gates)


def test_zero_trade_folds_fail_all_temporal_stability_gates() -> None:
    validation = _result()
    severe = _result()
    control = _result(expectancy=0.5)
    neighborhood = tuple(
        NeighborhoodResult(f"variant_{index}", _result(), severe)
        for index in range(9)
    )
    zero = _result(
        final_equity=1000.0,
        total_return=0.0,
        max_drawdown=0.0,
        trade_count=0,
        profit_factor=0.0,
        expectancy=0.0,
    )
    folds = tuple(FoldResult(index, index + 1, zero) for index in range(10))

    gates = evaluate_signal_gates(validation, severe, control, neighborhood, folds)
    statuses = {gate.number: gate.status for gate in gates}

    assert statuses[18] == "FAIL"
    assert statuses[19] == "FAIL"
    assert statuses[20] == "FAIL"
    assert statuses[21] == "FAIL"


def test_control_tie_semantics_match_frozen_contract() -> None:
    validation = _result(expectancy=1.0, profit_factor=1.20, total_cost=100.0)
    severe = _result()
    control = _result(expectancy=0.5, profit_factor=1.20, total_cost=100.0)
    neighborhood = tuple(
        NeighborhoodResult(f"variant_{index}", _result(), severe)
        for index in range(9)
    )
    folds = tuple(FoldResult(index, index + 1, _result()) for index in range(10))

    gates = evaluate_signal_gates(validation, severe, control, neighborhood, folds)
    statuses = {gate.number: gate.status for gate in gates}

    assert statuses[11] == "PASS"
    assert statuses[12] == "PASS"
    assert statuses[14] == "PASS"


def test_risk_gates_and_blocked_gate_numbering_are_complete() -> None:
    base = _result(layer="risk_sized", max_drawdown=-0.079)
    severe = replace(base, total_return=0.01, expectancy=0.1, profit_factor=1.01)

    risk_gates = evaluate_risk_gates(base, severe)
    blocked = blocked_risk_gates()

    assert [gate.number for gate in risk_gates] == list(range(22, 35))
    assert all(gate.status == "PASS" for gate in risk_gates)
    assert [gate.number for gate in blocked] == list(range(22, 35))
    assert all(gate.status == "BLOCKED" for gate in blocked)
