from __future__ import annotations

import hashlib
import json
import math
from dataclasses import dataclass
from pathlib import Path

from .execution_policy import (
    FIRST_CYCLE_MAX_DRAWDOWN_HALT,
    FIRST_CYCLE_RISK_FRACTION,
)

MIN_OOS_TRADES = 20
RISK_TOLERANCE = 1e-9


@dataclass(frozen=True, slots=True)
class OosGate:
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
        raise ValueError(f"Missing OOS metric: {name}")
    try:
        return float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"Invalid OOS metric: {name}") from exc


def _profit_factor(base: dict[str, object]) -> float:
    raw = base.get("profit_factor")
    if raw is not None:
        return _number(raw, "oos.profit_factor")
    if (
        int(base["trade_count"]) > 0
        and _number(base.get("average_win"), "oos.average_win") > 0
        and _number(base.get("average_loss"), "oos.average_loss") == 0
    ):
        return math.inf
    raise ValueError("Null OOS profit factor lacks a valid no-loss explanation")


def evaluate_final_oos_report(report: dict[str, object]) -> tuple[OosGate, ...]:
    if report.get("phase") != "final_frozen_risk_execution_oos":
        raise ValueError("Expected final frozen risk execution OOS report")
    if report.get("retuning_after_open") != "forbidden":
        raise ValueError("OOS report does not preserve retuning prohibition")
    if report.get("rerun") != "forbidden":
        raise ValueError("OOS report does not preserve one-shot policy")

    try:
        scenarios = report["window"]["scenarios"]
        base = scenarios["base"]
        severe = scenarios["severe"]
    except (KeyError, TypeError) as exc:
        raise ValueError("OOS report is missing required scenarios") from exc

    trade_count = int(base["trade_count"])
    total_return = _number(base["total_return"], "oos.total_return")
    expectancy = _number(base["expectancy"], "oos.expectancy")
    profit_factor = _profit_factor(base)
    max_drawdown = _number(base["max_drawdown"], "oos.max_drawdown")
    max_risk = _number(base["max_planned_risk_fraction"], "oos.max_planned_risk_fraction")
    average_notional = _number(base["average_notional_fraction"], "oos.average_notional_fraction")
    severe_return = _number(severe["total_return"], "oos.severe_return")
    severe_drawdown = _number(severe["max_drawdown"], "oos.severe_drawdown")

    pf_observed: float | str = "infinity" if math.isinf(profit_factor) else profit_factor
    return (
        OosGate(
            "oos_trade_count",
            trade_count >= MIN_OOS_TRADES,
            trade_count,
            f">= {MIN_OOS_TRADES}",
        ),
        OosGate("oos_positive_return", total_return > 0, total_return, "> 0"),
        OosGate("oos_positive_expectancy", expectancy > 0, expectancy, "> 0 USD/trade"),
        OosGate("oos_profit_factor", profit_factor > 1.0, pf_observed, "> 1.0"),
        OosGate(
            "oos_risk_cap",
            max_risk <= FIRST_CYCLE_RISK_FRACTION + RISK_TOLERANCE,
            max_risk,
            f"<= {FIRST_CYCLE_RISK_FRACTION:.3%} planned equity risk per trade",
        ),
        OosGate(
            "oos_no_leverage",
            average_notional <= 1.0 + RISK_TOLERANCE,
            average_notional,
            "average invested notional <= 100% equity",
        ),
        OosGate(
            "oos_no_hard_drawdown_halt",
            base["max_drawdown_halted"] is False
            and max_drawdown > -FIRST_CYCLE_MAX_DRAWDOWN_HALT,
            {"max_drawdown": max_drawdown, "halted": base["max_drawdown_halted"]},
            f"must not reach {-FIRST_CYCLE_MAX_DRAWDOWN_HALT:.1%} hard halt",
        ),
        OosGate(
            "oos_survives_severe_costs",
            severe_return > 0,
            severe_return,
            "> 0 total return under severe cost scenario",
        ),
        OosGate(
            "oos_severe_no_hard_drawdown_halt",
            severe["max_drawdown_halted"] is False
            and severe_drawdown > -FIRST_CYCLE_MAX_DRAWDOWN_HALT,
            {"max_drawdown": severe_drawdown, "halted": severe["max_drawdown_halted"]},
            f"severe-cost OOS must not reach {-FIRST_CYCLE_MAX_DRAWDOWN_HALT:.1%} hard halt",
        ),
    )


def write_final_oos_verdict(
    *,
    oos_report_path: str | Path = "artifacts/m2_final_oos_2025.json",
    verdict_path: str | Path = "artifacts/m2_final_oos_verdict.json",
) -> dict[str, object]:
    report_path = Path(oos_report_path)
    if not report_path.is_file():
        raise FileNotFoundError("Final OOS report does not exist")
    report = json.loads(report_path.read_text(encoding="utf-8"))
    gates = evaluate_final_oos_report(report)
    passed = all(gate.passed for gate in gates)
    payload: dict[str, object] = {
        "screening_version": 1,
        "purpose": "frozen_oos_screen_before_forward_paper_not_live_approval",
        "oos_report": str(report_path),
        "oos_report_sha256": _sha256(report_path),
        "status": "ELIGIBLE_FOR_FORWARD_PAPER" if passed else "REJECT_HISTORICAL_CYCLE",
        "all_gates_passed": passed,
        "live_trading_approved": False,
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
    verdict = write_final_oos_verdict()
    print(f"final_oos_verdict={verdict['status']}")
    for gate in verdict["gates"]:
        state = "PASS" if gate["passed"] else "FAIL"
        print(f"{state} {gate['name']}: observed={gate['observed']} rule={gate['rule']}")
    print("live_trading_approved=FALSE")
    print("next_if_pass=FORWARD_PAPER")
    print("report=artifacts/m2_final_oos_verdict.json")
    if verdict["all_gates_passed"] is not True:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
