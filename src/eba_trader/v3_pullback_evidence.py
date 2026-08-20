from __future__ import annotations

import argparse
import json
import math
from dataclasses import asdict, dataclass, replace
from pathlib import Path
from typing import Any

from .data_policy import allowed_source_close_times, allowed_source_gap_ranges
from .history import load_csv, parse_utc, validate_interval_window
from .provenance import collect_source_provenance
from .study_policy import (
    FIRST_CYCLE_INTERVAL,
    FIRST_CYCLE_SYMBOL,
    RESEARCH_END_EXCLUSIVE,
    RESEARCH_START,
    VALIDATION_END_EXCLUSIVE,
    VALIDATION_START,
)
from .v3_pullback import V3PullbackResult, run_v3_pullback_backtest
from .v3_pullback_policy import (
    BASELINE_V3_PULLBACK_CONFIG,
    COST_SCENARIOS,
    V3_RESEARCH_SHA256,
    V3_VALIDATION_SHA256,
    V3PullbackConfig,
    sha256_file,
    verify_v3_pullback_policy_freeze,
)

DAY_MS = 24 * 60 * 60 * 1000
NUMERIC_TOLERANCE = 1e-12


@dataclass(frozen=True, slots=True)
class GateResult:
    number: int
    section: str
    name: str
    status: str
    actual: Any
    requirement: str


@dataclass(frozen=True, slots=True)
class NeighborhoodResult:
    name: str
    base: V3PullbackResult
    severe: V3PullbackResult


@dataclass(frozen=True, slots=True)
class FoldResult:
    start_ms: int
    end_exclusive_ms: int
    result: V3PullbackResult


def _gate(
    number: int,
    section: str,
    name: str,
    passed: bool,
    actual: Any,
    requirement: str,
) -> GateResult:
    return GateResult(
        number=number,
        section=section,
        name=name,
        status="PASS" if passed else "FAIL",
        actual=actual,
        requirement=requirement,
    )


def _blocked_gate(number: int, name: str) -> GateResult:
    return GateResult(
        number=number,
        section="E",
        name=name,
        status="BLOCKED",
        actual="not_run",
        requirement="A-D must all pass before risk-sized evidence",
    )


def _profit_factor_passes_fold(result: V3PullbackResult) -> bool:
    if result.trade_count == 0:
        return False
    if math.isfinite(result.profit_factor):
        return result.profit_factor > 1.0
    pnl = [item.trade.pnl for item in result.trades]
    return any(value > 0 for value in pnl) and not any(value < 0 for value in pnl)


def evaluate_signal_gates(
    validation: V3PullbackResult,
    severe: V3PullbackResult,
    control: V3PullbackResult,
    neighborhood: tuple[NeighborhoodResult, ...],
    folds: tuple[FoldResult, ...],
) -> tuple[GateResult, ...]:
    gates: list[GateResult] = []
    drawdown_comparison_passes = (
        validation.total_return >= validation.benchmark_return
        or abs(validation.max_drawdown)
        <= 0.60 * abs(validation.benchmark_max_drawdown) + NUMERIC_TOLERANCE
    )
    gates.extend(
        (
            _gate(
                1,
                "A",
                "validation_trade_count",
                validation.trade_count >= 25,
                validation.trade_count,
                ">= 25",
            ),
            _gate(
                2,
                "A",
                "validation_base_return",
                validation.total_return > 0,
                validation.total_return,
                "> 0",
            ),
            _gate(
                3,
                "A",
                "validation_base_expectancy",
                validation.expectancy > 0,
                validation.expectancy,
                "> 0 USD",
            ),
            _gate(
                4,
                "A",
                "validation_base_profit_factor",
                validation.profit_factor >= 1.15,
                validation.profit_factor,
                ">= 1.15",
            ),
            _gate(
                5,
                "A",
                "validation_severe_return",
                severe.total_return > 0,
                severe.total_return,
                "> 0",
            ),
            _gate(
                6,
                "A",
                "validation_severe_expectancy",
                severe.expectancy > 0,
                severe.expectancy,
                "> 0 USD",
            ),
            _gate(
                7,
                "A",
                "validation_max_drawdown",
                abs(validation.max_drawdown) <= 0.20 + NUMERIC_TOLERANCE,
                validation.max_drawdown,
                "magnitude <= 20%",
            ),
            _gate(
                8,
                "A",
                "validation_time_exposure",
                validation.time_exposure <= 0.40 + NUMERIC_TOLERANCE,
                validation.time_exposure,
                "<= 40%",
            ),
            _gate(
                9,
                "A",
                "validation_benchmark_drawdown_condition",
                drawdown_comparison_passes,
                {
                    "strategy_return": validation.total_return,
                    "btc_return": validation.benchmark_return,
                    "strategy_drawdown": validation.max_drawdown,
                    "btc_drawdown": validation.benchmark_max_drawdown,
                },
                "if strategy return < BTC, |strategy DD| <= 60% of |BTC DD|",
            ),
            _gate(
                10,
                "A",
                "signal_invariants",
                validation.entry_invariant_violations == 0,
                validation.entry_invariant_violations,
                "entry/exit/data invariant violations == 0; data failures abort the study",
            ),
        )
    )

    gates.extend(
        (
            _gate(
                11,
                "B",
                "pullback_filter_expectancy_value",
                validation.expectancy > control.expectancy,
                {"v3": validation.expectancy, "control": control.expectancy},
                "V3 > REGIME_ONLY_RECOVERY_CONTROL",
            ),
            _gate(
                12,
                "B",
                "pullback_filter_profit_factor_value",
                validation.profit_factor + NUMERIC_TOLERANCE >= control.profit_factor,
                {"v3": validation.profit_factor, "control": control.profit_factor},
                "V3 >= control",
            ),
            _gate(
                13,
                "B",
                "pullback_filter_drawdown_value",
                abs(validation.max_drawdown)
                <= abs(control.max_drawdown) + NUMERIC_TOLERANCE,
                {"v3": validation.max_drawdown, "control": control.max_drawdown},
                "|V3 DD| <= |control DD|",
            ),
            _gate(
                14,
                "B",
                "pullback_filter_cost_value",
                validation.total_cost <= control.total_cost + NUMERIC_TOLERANCE,
                {"v3": validation.total_cost, "control": control.total_cost},
                "V3 trading cost <= control",
            ),
        )
    )

    positive_base_expectancy = sum(item.base.expectancy > 0 for item in neighborhood)
    base_pf_above_one = sum(item.base.profit_factor > 1.0 for item in neighborhood)
    positive_severe_expectancy = sum(item.severe.expectancy > 0 for item in neighborhood)
    gates.extend(
        (
            _gate(
                15,
                "C",
                "neighborhood_positive_base_expectancy",
                positive_base_expectancy >= 6,
                positive_base_expectancy,
                ">= 6 of 9",
            ),
            _gate(
                16,
                "C",
                "neighborhood_base_profit_factor",
                base_pf_above_one >= 6,
                base_pf_above_one,
                ">= 6 of 9 > 1.0",
            ),
            _gate(
                17,
                "C",
                "neighborhood_positive_severe_expectancy",
                positive_severe_expectancy >= 5,
                positive_severe_expectancy,
                ">= 5 of 9",
            ),
        )
    )

    fold_count = len(folds)
    trade_folds = sum(item.result.trade_count > 0 for item in folds)
    positive_return_folds = sum(
        item.result.trade_count > 0 and item.result.total_return > 0 for item in folds
    )
    positive_expectancy_folds = sum(
        item.result.trade_count > 0 and item.result.expectancy > 0 for item in folds
    )
    passing_pf_folds = sum(_profit_factor_passes_fold(item.result) for item in folds)

    def fraction(count: int) -> float:
        return count / fold_count if fold_count else 0.0

    gates.extend(
        (
            _gate(
                18,
                "D",
                "rolling_folds_with_trades",
                fraction(trade_folds) >= 0.80,
                {"passing": trade_folds, "total": fold_count, "fraction": fraction(trade_folds)},
                ">= 80%",
            ),
            _gate(
                19,
                "D",
                "rolling_positive_return",
                fraction(positive_return_folds) >= 0.60,
                {
                    "passing": positive_return_folds,
                    "total": fold_count,
                    "fraction": fraction(positive_return_folds),
                },
                ">= 60%",
            ),
            _gate(
                20,
                "D",
                "rolling_positive_expectancy",
                fraction(positive_expectancy_folds) >= 0.60,
                {
                    "passing": positive_expectancy_folds,
                    "total": fold_count,
                    "fraction": fraction(positive_expectancy_folds),
                },
                ">= 60%",
            ),
            _gate(
                21,
                "D",
                "rolling_profit_factor",
                fraction(passing_pf_folds) >= 0.60,
                {
                    "passing": passing_pf_folds,
                    "total": fold_count,
                    "fraction": fraction(passing_pf_folds),
                },
                ">= 60%",
            ),
        )
    )
    return tuple(gates)


def evaluate_risk_gates(
    base: V3PullbackResult,
    severe: V3PullbackResult,
) -> tuple[GateResult, ...]:
    return (
        _gate(22, "E", "risk_trade_count", base.trade_count >= 25, base.trade_count, ">= 25"),
        _gate(23, "E", "risk_base_return", base.total_return > 0, base.total_return, "> 0"),
        _gate(24, "E", "risk_base_expectancy", base.expectancy > 0, base.expectancy, "> 0 USD"),
        _gate(
            25,
            "E",
            "risk_base_profit_factor",
            base.profit_factor >= 1.10,
            base.profit_factor,
            ">= 1.10",
        ),
        _gate(
            26,
            "E",
            "risk_per_trade_cap",
            base.max_planned_risk_fraction <= 0.0035 + NUMERIC_TOLERANCE,
            base.max_planned_risk_fraction,
            "<= 0.35% + numeric tolerance",
        ),
        _gate(
            27,
            "E",
            "entry_notional_cap",
            base.max_notional_fraction <= 0.50 + NUMERIC_TOLERANCE,
            base.max_notional_fraction,
            "<= 50% + numeric tolerance",
        ),
        _gate(
            28,
            "E",
            "base_no_drawdown_halt",
            not base.max_drawdown_halted,
            base.max_drawdown_halted,
            "false",
        ),
        _gate(
            29,
            "E",
            "risk_base_max_drawdown",
            base.max_drawdown > -0.08,
            base.max_drawdown,
            "> -8%",
        ),
        _gate(30, "E", "risk_severe_return", severe.total_return > 0, severe.total_return, "> 0"),
        _gate(
            31,
            "E",
            "risk_severe_expectancy",
            severe.expectancy > 0,
            severe.expectancy,
            "> 0 USD",
        ),
        _gate(
            32,
            "E",
            "risk_severe_profit_factor",
            severe.profit_factor > 1.0,
            severe.profit_factor,
            "> 1.0",
        ),
        _gate(
            33,
            "E",
            "severe_no_drawdown_halt",
            not severe.max_drawdown_halted,
            severe.max_drawdown_halted,
            "false",
        ),
        _gate(
            34,
            "E",
            "risk_entry_veto_invariants",
            base.entry_invariant_violations == 0
            and base.veto_entry_violations == 0
            and severe.entry_invariant_violations == 0
            and severe.veto_entry_violations == 0,
            {
                "base_entry": base.entry_invariant_violations,
                "base_veto": base.veto_entry_violations,
                "severe_entry": severe.entry_invariant_violations,
                "severe_veto": severe.veto_entry_violations,
            },
            "all violation counts == 0",
        ),
    )


RISK_GATE_NAMES = (
    "risk_trade_count",
    "risk_base_return",
    "risk_base_expectancy",
    "risk_base_profit_factor",
    "risk_per_trade_cap",
    "entry_notional_cap",
    "base_no_drawdown_halt",
    "risk_base_max_drawdown",
    "risk_severe_return",
    "risk_severe_expectancy",
    "risk_severe_profit_factor",
    "severe_no_drawdown_halt",
    "risk_entry_veto_invariants",
)


def blocked_risk_gates() -> tuple[GateResult, ...]:
    return tuple(
        _blocked_gate(number, name)
        for number, name in zip(range(22, 35), RISK_GATE_NAMES, strict=True)
    )


def _with_cost(config: V3PullbackConfig, scenario: str) -> V3PullbackConfig:
    costs = COST_SCENARIOS[scenario]
    return replace(
        config,
        fee_bps=costs["fee_bps"],
        slippage_bps=costs["slippage_bps"],
    )


def _summary(result: V3PullbackResult) -> dict[str, Any]:
    payload = asdict(result)
    payload.pop("trades")
    return payload


def _json_safe(value: Any) -> Any:
    if isinstance(value, float) and not math.isfinite(value):
        return "Infinity" if value > 0 else "-Infinity"
    if isinstance(value, dict):
        return {key: _json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(item) for item in value]
    return value


def _load_frozen_development_data(data_dir: Path):
    research_path = data_dir / "btcusdt_15m_research.csv"
    validation_path = data_dir / "btcusdt_15m_validation.csv"
    if sha256_file(research_path) != V3_RESEARCH_SHA256:
        raise RuntimeError("V3 research data hash mismatch")
    if sha256_file(validation_path) != V3_VALIDATION_SHA256:
        raise RuntimeError("V3 validation data hash mismatch")

    gaps = allowed_source_gap_ranges(FIRST_CYCLE_SYMBOL, FIRST_CYCLE_INTERVAL)
    close_times = allowed_source_close_times(FIRST_CYCLE_SYMBOL, FIRST_CYCLE_INTERVAL)
    research = validate_interval_window(
        load_csv(research_path),
        FIRST_CYCLE_INTERVAL,
        parse_utc(RESEARCH_START),
        parse_utc(RESEARCH_END_EXCLUSIVE),
        allowed_missing_ranges=gaps,
        allowed_close_times=close_times,
    )
    validation = validate_interval_window(
        load_csv(validation_path),
        FIRST_CYCLE_INTERVAL,
        parse_utc(VALIDATION_START),
        parse_utc(VALIDATION_END_EXCLUSIVE),
        allowed_missing_ranges=gaps,
        allowed_close_times=close_times,
    )
    return research, validation


def _run_neighborhood(research) -> tuple[NeighborhoodResult, ...]:
    baseline = BASELINE_V3_PULLBACK_CONFIG
    configurations = (
        ("baseline", baseline),
        ("min_pullback_0_50", replace(baseline, min_pullback_depth_atr=0.50)),
        ("min_pullback_1_00", replace(baseline, min_pullback_depth_atr=1.00)),
        ("max_pullback_1_75", replace(baseline, max_pullback_depth_atr=1.75)),
        ("max_pullback_2_75", replace(baseline, max_pullback_depth_atr=2.75)),
        ("recovery_high_2", replace(baseline, recovery_high_lookback=2)),
        ("recovery_high_4", replace(baseline, recovery_high_lookback=4)),
        ("target_1_50r", replace(baseline, target_r=1.50)),
        ("target_2_50r", replace(baseline, target_r=2.50)),
    )
    return tuple(
        NeighborhoodResult(
            name=name,
            base=run_v3_pullback_backtest(research, _with_cost(config, "base")),
            severe=run_v3_pullback_backtest(research, _with_cost(config, "severe")),
        )
        for name, config in configurations
    )


def _run_rolling_folds(research) -> tuple[FoldResult, ...]:
    research_start = parse_utc(RESEARCH_START)
    research_end = parse_utc(RESEARCH_END_EXCLUSIVE)
    context_ms = 180 * DAY_MS
    test_ms = 30 * DAY_MS
    step_ms = 30 * DAY_MS
    test_start = research_start + context_ms
    folds: list[FoldResult] = []
    while test_start + test_ms <= research_end:
        test_end = test_start + test_ms
        context_start = test_start - context_ms
        context = [
            bar for bar in research if context_start <= bar.open_time_ms < test_end
        ]
        result = run_v3_pullback_backtest(
            context,
            _with_cost(BASELINE_V3_PULLBACK_CONFIG, "base"),
            evaluation_start_ms=test_start,
            evaluation_end_exclusive_ms=test_end,
        )
        folds.append(FoldResult(test_start, test_end, result))
        test_start += step_ms
    return tuple(folds)


def run_v3_pullback_development_evidence(
    *,
    data_dir: str | Path = "data/cache/m2",
    report_path: str | Path = "artifacts/m4_v3_pullback_development_evidence.json",
) -> dict[str, Any]:
    manifest = verify_v3_pullback_policy_freeze()
    provenance = collect_source_provenance(require_clean=True)
    research, validation = _load_frozen_development_data(Path(data_dir))
    combined = [*research, *validation]
    validation_start = parse_utc(VALIDATION_START)
    validation_end = parse_utc(VALIDATION_END_EXCLUSIVE)

    validation_results = {
        scenario: run_v3_pullback_backtest(
            combined,
            _with_cost(BASELINE_V3_PULLBACK_CONFIG, scenario),
            evaluation_start_ms=validation_start,
            evaluation_end_exclusive_ms=validation_end,
        )
        for scenario in COST_SCENARIOS
    }
    control = run_v3_pullback_backtest(
        combined,
        _with_cost(BASELINE_V3_PULLBACK_CONFIG, "base"),
        evaluation_start_ms=validation_start,
        evaluation_end_exclusive_ms=validation_end,
        filters_enabled=False,
    )
    neighborhood = _run_neighborhood(research)
    folds = _run_rolling_folds(research)
    signal_gates = evaluate_signal_gates(
        validation_results["base"],
        validation_results["severe"],
        control,
        neighborhood,
        folds,
    )

    signal_pass = all(item.status == "PASS" for item in signal_gates)
    risk_results: dict[str, V3PullbackResult] = {}
    if signal_pass:
        risk_results = {
            scenario: run_v3_pullback_backtest(
                combined,
                _with_cost(BASELINE_V3_PULLBACK_CONFIG, scenario),
                evaluation_start_ms=validation_start,
                evaluation_end_exclusive_ms=validation_end,
                risk_sized=True,
            )
            for scenario in ("base", "severe")
        }
        risk_gates = evaluate_risk_gates(
            risk_results["base"],
            risk_results["severe"],
        )
    else:
        risk_gates = blocked_risk_gates()

    gates = (*signal_gates, *risk_gates)
    all_pass = all(item.status == "PASS" for item in gates)
    if not signal_pass:
        decision = "REJECT_V3_SIGNAL_CYCLE"
        reported = validation_results["base"]
    elif not all_pass:
        decision = "REJECT_V3_EXECUTION_CYCLE"
        reported = risk_results["base"]
    else:
        decision = "ELIGIBLE_FOR_V3_FINAL_FREEZE_REVIEW"
        reported = risk_results["base"]

    report: dict[str, Any] = {
        "phase": "development_only",
        "cycle": "v3_bull_pullback_recovery",
        "decision": decision,
        "policy_freeze": manifest,
        "source_provenance": provenance,
        "data_boundary": {
            "research": f"{RESEARCH_START}/{RESEARCH_END_EXCLUSIVE}",
            "validation": f"{VALIDATION_START}/{VALIDATION_END_EXCLUSIVE}",
            "oos_2025": "LOCKED_NOT_ACCESSED",
        },
        "ai_module": "excluded",
        "parameter_changes_after_result": "forbidden",
        "validation_signal": {
            name: _summary(result) for name, result in validation_results.items()
        },
        "controls": {
            "cash": {"total_return": 0.0, "max_drawdown": 0.0, "trade_count": 0},
            "regime_only_recovery_control_base": _summary(control),
            "trend_v1_historical_context": {
                "validation_total_return": -0.4507,
                "validation_max_drawdown": -0.5060,
                "validation_profit_factor": 0.770,
                "validation_trade_count": 337,
                "role": "historical_context_only",
            },
            "trend_v2_historical_context": {
                "validation_total_return": -0.1753,
                "validation_max_drawdown": -0.2290,
                "validation_profit_factor": 0.612,
                "validation_trade_count": 101,
                "role": "historical_context_only",
            },
        },
        "research_neighborhood": [
            {
                "name": item.name,
                "base": _summary(item.base),
                "severe": _summary(item.severe),
            }
            for item in neighborhood
        ],
        "research_rolling_folds": [
            {
                "start_ms": item.start_ms,
                "end_exclusive_ms": item.end_exclusive_ms,
                "base": _summary(item.result),
            }
            for item in folds
        ],
        "risk_execution": {
            "status": "RUN" if signal_pass else "BLOCKED_BY_SIGNAL_GATES",
            "results": {name: _summary(result) for name, result in risk_results.items()},
        },
        "gates": [asdict(item) for item in gates],
        "gate_summary": {
            "pass": sum(item.status == "PASS" for item in gates),
            "fail": sum(item.status == "FAIL" for item in gates),
            "blocked": sum(item.status == "BLOCKED" for item in gates),
            "total": len(gates),
        },
        "reported_result": _summary(reported),
    }
    safe_report = _json_safe(report)
    output = Path(report_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(safe_report, indent=2, sort_keys=True, allow_nan=False),
        encoding="utf-8",
    )
    return safe_report


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run frozen V3 pullback evidence on 2021-2024 development data only"
    )
    parser.add_argument(
        "--report",
        default="artifacts/m4_v3_pullback_development_evidence.json",
    )
    args = parser.parse_args()
    report = run_v3_pullback_development_evidence(report_path=args.report)
    result = report["reported_result"]
    summary = report["gate_summary"]
    failed = [str(item["number"]) for item in report["gates"] if item["status"] == "FAIL"]
    print(f"decision={report['decision']}")
    print(
        f"return={result['total_return']:.2%} drawdown={result['max_drawdown']:.2%} "
        f"trades={result['trade_count']} profit_factor={result['profit_factor']}"
    )
    print(
        f"gates_pass={summary['pass']} gates_fail={summary['fail']} "
        f"gates_blocked={summary['blocked']} failed={','.join(failed) or 'none'}"
    )
    print("oos_2025=LOCKED_NOT_ACCESSED")
    print(f"report={args.report}")


if __name__ == "__main__":
    main()
