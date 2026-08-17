from __future__ import annotations

import argparse
import hashlib
import json
from dataclasses import dataclass
from pathlib import Path

MIN_VALIDATION_TRADES = 20
MIN_NEIGHBORHOOD_POSITIVE_EXPECTANCY_FRACTION = 0.60
MIN_WALK_FORWARD_POSITIVE_TEST_FRACTION = 0.50
MIN_WALK_FORWARD_POSITIVE_EXPECTANCY_FRACTION = 0.50
MIN_WALK_FORWARD_DRAWDOWN_IMPROVEMENT_FRACTION = 0.50
MAX_DRAWDOWN_RATIO_IF_UNDERPERFORMING_BTC = 0.75


@dataclass(frozen=True, slots=True)
class GateResult:
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


def _as_float(value: object, name: str) -> float:
    if value is None:
        raise ValueError(f"Missing numeric metric: {name}")
    try:
        return float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"Invalid numeric metric: {name}") from exc


def _as_int(value: object, name: str) -> int:
    try:
        return int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"Invalid integer metric: {name}") from exc


def _drawdown_ratio(strategy_drawdown: float, benchmark_drawdown: float) -> float:
    benchmark_abs = abs(benchmark_drawdown)
    if benchmark_abs == 0:
        return 0.0 if strategy_drawdown == 0 else float("inf")
    return abs(strategy_drawdown) / benchmark_abs


def evaluate_development_report(report: dict[str, object]) -> tuple[GateResult, ...]:
    if report.get("phase") != "development_only":
        raise ValueError("Expected a development_only evidence report")
    if report.get("oos_2025") != "LOCKED_NOT_ACCESSED":
        raise ValueError("OOS must remain locked during development screening")
    if report.get("frozen_baseline") != {"fast_ema": 20, "slow_ema": 50}:
        raise ValueError("First-cycle frozen baseline must be EMA 20/50")

    try:
        validation = report["baseline"]["windows"]["validation"]["scenarios"]
        validation_base = validation["base"]
        validation_severe = validation["severe"]
        neighborhood = report["research_robustness"]["parameter_neighborhood"]
        walk_forward = report["research_robustness"]["walk_forward"]
    except (KeyError, TypeError) as exc:
        raise ValueError("Development report is missing required evidence sections") from exc

    trade_count = _as_int(validation_base["trade_count"], "validation.trade_count")
    total_return = _as_float(validation_base["total_return"], "validation.total_return")
    expectancy = _as_float(validation_base["expectancy"], "validation.expectancy")
    profit_factor = _as_float(validation_base["profit_factor"], "validation.profit_factor")
    severe_return = _as_float(validation_severe["total_return"], "validation.severe_return")
    relative_return = _as_float(
        validation_base["benchmark_relative_return"],
        "validation.benchmark_relative_return",
    )
    strategy_drawdown = _as_float(validation_base["max_drawdown"], "validation.max_drawdown")
    benchmark_drawdown = _as_float(
        validation_base["benchmark_max_drawdown"],
        "validation.benchmark_max_drawdown",
    )
    drawdown_ratio = _drawdown_ratio(strategy_drawdown, benchmark_drawdown)

    neighborhood_expectancy = _as_float(
        neighborhood["positive_expectancy_fraction"],
        "neighborhood.positive_expectancy_fraction",
    )
    wf_positive = _as_float(
        walk_forward["positive_test_fraction"],
        "walk_forward.positive_test_fraction",
    )
    wf_expectancy = _as_float(
        walk_forward["positive_expectancy_fraction"],
        "walk_forward.positive_expectancy_fraction",
    )
    wf_risk = _as_float(
        walk_forward["drawdown_improvement_fraction"],
        "walk_forward.drawdown_improvement_fraction",
    )

    return (
        GateResult(
            "validation_trade_count",
            trade_count >= MIN_VALIDATION_TRADES,
            trade_count,
            f">= {MIN_VALIDATION_TRADES}",
        ),
        GateResult(
            "validation_positive_return",
            total_return > 0,
            total_return,
            "> 0",
        ),
        GateResult(
            "validation_positive_expectancy",
            expectancy > 0,
            expectancy,
            "> 0 USD/trade",
        ),
        GateResult(
            "validation_profit_factor",
            profit_factor > 1.0,
            profit_factor,
            "> 1.0",
        ),
        GateResult(
            "validation_survives_severe_costs",
            severe_return > 0,
            severe_return,
            "> 0 total return under severe cost scenario",
        ),
        GateResult(
            "research_parameter_neighborhood",
            neighborhood_expectancy >= MIN_NEIGHBORHOOD_POSITIVE_EXPECTANCY_FRACTION,
            neighborhood_expectancy,
            f">= {MIN_NEIGHBORHOOD_POSITIVE_EXPECTANCY_FRACTION:.0%} positive expectancy",
        ),
        GateResult(
            "walk_forward_positive_tests",
            wf_positive >= MIN_WALK_FORWARD_POSITIVE_TEST_FRACTION,
            wf_positive,
            f">= {MIN_WALK_FORWARD_POSITIVE_TEST_FRACTION:.0%} positive test folds",
        ),
        GateResult(
            "walk_forward_positive_expectancy",
            wf_expectancy >= MIN_WALK_FORWARD_POSITIVE_EXPECTANCY_FRACTION,
            wf_expectancy,
            f">= {MIN_WALK_FORWARD_POSITIVE_EXPECTANCY_FRACTION:.0%} folds with positive expectancy",
        ),
        GateResult(
            "walk_forward_drawdown_advantage",
            wf_risk >= MIN_WALK_FORWARD_DRAWDOWN_IMPROVEMENT_FRACTION,
            wf_risk,
            f">= {MIN_WALK_FORWARD_DRAWDOWN_IMPROVEMENT_FRACTION:.0%} folds with shallower drawdown than BTC",
        ),
        GateResult(
            "validation_return_or_material_risk_advantage",
            relative_return >= 0
            or drawdown_ratio <= MAX_DRAWDOWN_RATIO_IF_UNDERPERFORMING_BTC,
            {
                "benchmark_relative_return": relative_return,
                "strategy_to_btc_drawdown_ratio": drawdown_ratio,
            },
            (
                ">= BTC return OR strategy max-drawdown magnitude <= "
                f"{MAX_DRAWDOWN_RATIO_IF_UNDERPERFORMING_BTC:.0%} of BTC drawdown"
            ),
        ),
    )


def write_development_verdict(
    *,
    development_report_path: str | Path = "artifacts/m2_development_evidence.json",
    verdict_path: str | Path = "artifacts/m2_development_verdict.json",
) -> dict[str, object]:
    report_path = Path(development_report_path)
    if not report_path.is_file():
        raise FileNotFoundError("Development evidence report does not exist")
    report = json.loads(report_path.read_text(encoding="utf-8"))
    gates = evaluate_development_report(report)
    passed = all(gate.passed for gate in gates)

    payload: dict[str, object] = {
        "screening_version": 1,
        "purpose": "predeclared_screening_not_profit_guarantee",
        "development_report": str(report_path),
        "development_report_sha256": _sha256(report_path),
        "status": "ELIGIBLE_FOR_FROZEN_OOS" if passed else "REJECT_DEVELOPMENT_CYCLE",
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


def development_verdict_cli() -> None:
    parser = argparse.ArgumentParser(
        description="Apply predeclared M2 development gates before frozen OOS eligibility"
    )
    parser.parse_args()
    verdict = write_development_verdict()
    print(f"development_verdict={verdict['status']}")
    for gate in verdict["gates"]:
        state = "PASS" if gate["passed"] else "FAIL"
        print(f"{state} {gate['name']}: observed={gate['observed']} rule={gate['rule']}")
    print("report=artifacts/m2_development_verdict.json")
    if verdict["all_gates_passed"] is not True:
        raise SystemExit(2)
