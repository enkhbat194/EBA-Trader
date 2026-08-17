from __future__ import annotations

import hashlib
import json
import math
from dataclasses import dataclass
from pathlib import Path

from .execution_policy import (
    EXECUTION_POLICY_NAME,
    EXECUTION_POLICY_VERSION,
    FIRST_CYCLE_ATR_MULTIPLIER,
    FIRST_CYCLE_ATR_PERIOD,
    FIRST_CYCLE_DAILY_LOSS_LIMIT,
    FIRST_CYCLE_MAX_DRAWDOWN_HALT,
    FIRST_CYCLE_RISK_FRACTION,
)
from .study_policy import (
    FIRST_CYCLE_FAST_EMA,
    FIRST_CYCLE_INITIAL_CASH,
    FIRST_CYCLE_INTERVAL,
    FIRST_CYCLE_SLOW_EMA,
    FIRST_CYCLE_SYMBOL,
)

MIN_VALIDATION_TRADES = 20
MAX_RISK_TOLERANCE = 1e-9


@dataclass(frozen=True, slots=True)
class RiskGate:
    name: str
    passed: bool
    observed: object
    rule: str


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _number(value: object, name: str) -> float:
    if value is None:
        raise ValueError(f"Missing numeric risk metric: {name}")
    try:
        return float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"Invalid numeric risk metric: {name}") from exc


def _profit_factor(base: dict[str, object]) -> float:
    raw = base.get("profit_factor")
    if raw is not None:
        return _number(raw, "validation.profit_factor")
    trade_count = int(base["trade_count"])
    average_win = _number(base.get("average_win"), "validation.average_win")
    average_loss = _number(base.get("average_loss"), "validation.average_loss")
    if trade_count > 0 and average_win > 0 and average_loss == 0:
        return math.inf
    raise ValueError("Null profit factor lacks a valid no-loss explanation")


def _assert_policy_snapshot(report: dict[str, object]) -> None:
    if report.get("phase") != "risk_execution_development":
        raise ValueError("Expected risk_execution_development evidence")
    if report.get("oos_2025") != "LOCKED_NOT_ACCESSED":
        raise ValueError("Risk execution development must not access 2025 OOS")
    if str(report.get("symbol", "")).upper() != FIRST_CYCLE_SYMBOL:
        raise ValueError("Risk execution symbol must remain BTCUSDT")
    if str(report.get("interval", "")) != FIRST_CYCLE_INTERVAL:
        raise ValueError("Risk execution interval must remain 15m")
    if float(report.get("initial_cash", 0.0)) != FIRST_CYCLE_INITIAL_CASH:
        raise ValueError("Risk execution normalized cash must remain $1000")
    if report.get("strategy") != {
        "fast_ema": FIRST_CYCLE_FAST_EMA,
        "slow_ema": FIRST_CYCLE_SLOW_EMA,
    }:
        raise ValueError("Risk execution strategy must remain EMA20/50")

    policy = report.get("execution_policy")
    if not isinstance(policy, dict):
        raise ValueError("Risk execution policy snapshot is missing")
    expected = {
        "version": EXECUTION_POLICY_VERSION,
        "name": EXECUTION_POLICY_NAME,
        "atr_period": FIRST_CYCLE_ATR_PERIOD,
        "atr_multiplier": FIRST_CYCLE_ATR_MULTIPLIER,
        "risk_fraction": FIRST_CYCLE_RISK_FRACTION,
        "daily_loss_limit": FIRST_CYCLE_DAILY_LOSS_LIMIT,
        "max_drawdown_halt": FIRST_CYCLE_MAX_DRAWDOWN_HALT,
        "spot_only": True,
        "leverage": 1.0,
        "take_profit": None,
        "normal_exit": "EMA cross-down at next bar open",
        "protective_exit": "ATR stop; adverse gaps execute at available bar open",
    }
    if policy != expected:
        raise ValueError("Risk execution policy no longer matches the predeclared snapshot")

    provenance = report.get("source_provenance")
    if not isinstance(provenance, dict):
        raise ValueError("Risk execution source provenance is missing")
    if provenance.get("tracked_working_tree_clean") is not True:
        raise ValueError("Risk execution evidence was produced from a dirty tracked tree")
    if len(str(provenance.get("git_commit", ""))) < 7:
        raise ValueError("Risk execution evidence lacks a Git commit")


def evaluate_risk_execution_report(report: dict[str, object]) -> tuple[RiskGate, ...]:
    _assert_policy_snapshot(report)
    try:
        validation = report["windows"]["validation"]["scenarios"]
        base = validation["base"]
        severe = validation["severe"]
    except (KeyError, TypeError) as exc:
        raise ValueError("Risk execution report lacks validation scenarios") from exc

    trade_count = int(base["trade_count"])
    total_return = _number(base["total_return"], "validation.total_return")
    expectancy = _number(base["expectancy"], "validation.expectancy")
    profit_factor = _profit_factor(base)
    max_drawdown = _number(base["max_drawdown"], "validation.max_drawdown")
    max_planned_risk = _number(
        base["max_planned_risk_fraction"],
        "validation.max_planned_risk_fraction",
    )
    average_notional = _number(
        base["average_notional_fraction"],
        "validation.average_notional_fraction",
    )
    severe_return = _number(severe["total_return"], "validation.severe_return")
    severe_drawdown = _number(severe["max_drawdown"], "validation.severe_drawdown")

    profit_factor_observed: float | str = (
        "infinity" if math.isinf(profit_factor) else profit_factor
    )
    return (
        RiskGate(
            "validation_trade_count",
            trade_count >= MIN_VALIDATION_TRADES,
            trade_count,
            f">= {MIN_VALIDATION_TRADES}",
        ),
        RiskGate("validation_positive_return", total_return > 0, total_return, "> 0"),
        RiskGate(
            "validation_positive_expectancy",
            expectancy > 0,
            expectancy,
            "> 0 USD/trade",
        ),
        RiskGate(
            "validation_profit_factor",
            profit_factor > 1.0,
            profit_factor_observed,
            "> 1.0",
        ),
        RiskGate(
            "validation_planned_risk_cap",
            max_planned_risk <= FIRST_CYCLE_RISK_FRACTION + MAX_RISK_TOLERANCE,
            max_planned_risk,
            f"<= {FIRST_CYCLE_RISK_FRACTION:.3%} planned equity risk per trade",
        ),
        RiskGate(
            "validation_spot_notional_cap",
            average_notional <= 1.0 + MAX_RISK_TOLERANCE,
            average_notional,
            "average invested notional <= 100% equity; no leverage",
        ),
        RiskGate(
            "validation_no_hard_drawdown_halt",
            base["max_drawdown_halted"] is False
            and max_drawdown > -FIRST_CYCLE_MAX_DRAWDOWN_HALT,
            {
                "max_drawdown": max_drawdown,
                "halted": base["max_drawdown_halted"],
            },
            f"must not reach {-FIRST_CYCLE_MAX_DRAWDOWN_HALT:.1%} hard halt",
        ),
        RiskGate(
            "validation_survives_severe_costs",
            severe_return > 0,
            severe_return,
            "> 0 total return under severe cost scenario",
        ),
        RiskGate(
            "severe_cost_no_hard_drawdown_halt",
            severe["max_drawdown_halted"] is False
            and severe_drawdown > -FIRST_CYCLE_MAX_DRAWDOWN_HALT,
            {
                "max_drawdown": severe_drawdown,
                "halted": severe["max_drawdown_halted"],
            },
            f"severe-cost run must not reach {-FIRST_CYCLE_MAX_DRAWDOWN_HALT:.1%} hard halt",
        ),
    )


def write_risk_execution_verdict(
    *,
    evidence_path: str | Path = "artifacts/m2_risk_execution_evidence.json",
    verdict_path: str | Path = "artifacts/m2_risk_execution_verdict.json",
) -> dict[str, object]:
    path = Path(evidence_path)
    if not path.is_file():
        raise FileNotFoundError("Risk execution evidence does not exist")
    report = json.loads(path.read_text(encoding="utf-8"))
    gates = evaluate_risk_execution_report(report)
    passed = all(gate.passed for gate in gates)
    payload: dict[str, object] = {
        "screening_version": 1,
        "purpose": "predeclared_risk_execution_screening_not_profit_guarantee",
        "risk_execution_evidence": str(path),
        "risk_execution_evidence_sha256": _sha256(path),
        "status": (
            "ELIGIBLE_FOR_FINAL_FROZEN_OOS"
            if passed
            else "REJECT_RISK_EXECUTION_MODEL"
        ),
        "all_gates_passed": passed,
        "gates": [
            {
                "name": gate.name,
                "passed": gate.passed,
                "observed": gate.observed,
                "rule": gate.rule,
            }
            for gate in gates
        ],
    }
    output = Path(verdict_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    return payload


def main() -> None:
    verdict = write_risk_execution_verdict()
    print(f"risk_execution_verdict={verdict['status']}")
    for gate in verdict["gates"]:
        state = "PASS" if gate["passed"] else "FAIL"
        print(f"{state} {gate['name']}: observed={gate['observed']} rule={gate['rule']}")
    print("report=artifacts/m2_risk_execution_verdict.json")
    if verdict["all_gates_passed"] is not True:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
