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
from .trend_v2 import TrendV2Result, run_trend_v2_backtest
from .trend_v2_policy import (
    BASELINE_TREND_V2_CONFIG,
    COST_SCENARIOS,
    TREND_V2_RESEARCH_SHA256,
    TREND_V2_VALIDATION_SHA256,
    TrendV2Config,
    sha256_file,
    verify_trend_v2_policy_freeze,
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
    base: TrendV2Result
    severe: TrendV2Result


@dataclass(frozen=True, slots=True)
class FoldResult:
    start_ms: int
    end_exclusive_ms: int
    result: TrendV2Result


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


def _profit_factor_passes_fold(result: TrendV2Result) -> bool:
    if result.trade_count == 0:
        return False
    if math.isfinite(result.profit_factor):
        return result.profit_factor > 1.0
    pnl = [item.trade.pnl for item in result.trades]
    return any(value > 0 for value in pnl) and not any(value < 0 for value in pnl)


def evaluate_signal_gates(
    validation: TrendV2Result,
    severe: TrendV2Result,
    control: TrendV2Result,
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
            _gate(1, "A", "validation_trade_count", validation.trade_count >= 20,
                  validation.trade_count, ">= 20"),
            _gate(2, "A", "validation_base_return", validation.total_return > 0,
                  validation.total_return, "> 0"),
            _gate(3, "A", "validation_base_expectancy", validation.expectancy > 0,
                  validation.expectancy, "> 0 USD"),
            _gate(4, "A", "validation_base_profit_factor",
                  validation.profit_factor >= 1.15, validation.profit_factor, ">= 1.15"),
            _gate(5, "A", "validation_severe_return", severe.total_return > 0,
                  severe.total_return, "> 0"),
            _gate(6, "A", "validation_severe_expectancy", severe.expectancy > 0,
                  severe.expectancy, "> 0 USD"),
            _gate(7, "A", "validation_max_drawdown",
                  abs(validation.max_drawdown) <= 0.25 + NUMERIC_TOLERANCE,
                  validation.max_drawdown, "magnitude <= 25%"),
            _gate(8, "A", "validation_time_exposure",
                  0.05 <= validation.time_exposure <= 0.60,
                  validation.time_exposure, "5% <= exposure <= 60%"),
            _gate(9, "A", "validation_benchmark_drawdown_condition",
                  drawdown_comparison_passes,
                  {
                      "strategy_return": validation.total_return,
                      "btc_return": validation.benchmark_return,
                      "strategy_drawdown": validation.max_drawdown,
                      "btc_drawdown": validation.benchmark_max_drawdown,
                  },
                  "if strategy return < BTC, |strategy DD| <= 60% of |BTC DD|"),
            _gate(10, "A", "entry_invariants",
                  validation.entry_invariant_violations == 0,
                  validation.entry_invariant_violations, "== 0"),
        )
    )

    gates.extend(
        (
            _gate(11, "B", "filtered_expectancy_value",
                  validation.expectancy > control.expectancy,
                  {"filtered": validation.expectancy, "control": control.expectancy},
                  "filtered > unfiltered control"),
            _gate(12, "B", "filtered_profit_factor_value",
                  validation.profit_factor > control.profit_factor,
                  {"filtered": validation.profit_factor, "control": control.profit_factor},
                  "filtered > unfiltered control"),
            _gate(13, "B", "filtered_drawdown_value",
                  abs(validation.max_drawdown) <= abs(control.max_drawdown) + NUMERIC_TOLERANCE,
                  {"filtered": validation.max_drawdown, "control": control.max_drawdown},
                  "|filtered DD| <= |control DD|"),
            _gate(14, "B", "filtered_cost_reduction",
                  control.trade_count >= 20
                  and validation.total_cost <= 0.75 * control.total_cost + NUMERIC_TOLERANCE,
                  {
                      "filtered_cost": validation.total_cost,
                      "control_cost": control.total_cost,
                      "control_trades": control.trade_count,
                  },
                  "control trades >= 20 and filtered cost <= 75% of control"),
        )
    )

    positive_base_expectancy = sum(item.base.expectancy > 0 for item in neighborhood)
    base_pf_above_one = sum(item.base.profit_factor > 1.0 for item in neighborhood)
    positive_severe_expectancy = sum(item.severe.expectancy > 0 for item in neighborhood)
    baseline = neighborhood[0]
    others = neighborhood[1:]
    baseline_sole_best_both = (
        all(baseline.base.total_return > item.base.total_return for item in others)
        and all(baseline.base.expectancy > item.base.expectancy for item in others)
    )
    gates.extend(
        (
            _gate(15, "C", "neighborhood_positive_base_expectancy",
                  positive_base_expectancy >= 6, positive_base_expectancy, ">= 6 of 9"),
            _gate(16, "C", "neighborhood_base_profit_factor",
                  base_pf_above_one >= 6, base_pf_above_one, ">= 6 of 9 > 1.0"),
            _gate(17, "C", "neighborhood_positive_severe_expectancy",
                  positive_severe_expectancy >= 5, positive_severe_expectancy, ">= 5 of 9"),
            _gate(18, "C", "baseline_anti_peak",
                  not baseline_sole_best_both,
                  {"baseline_is_sole_best_return_and_expectancy": baseline_sole_best_both},
                  "baseline is not sole best on both return and expectancy"),
        )
    )

    fold_count = len(folds)
    trade_folds = sum(item.result.trade_count > 0 for item in folds)
    positive_return_folds = sum(item.result.total_return > 0 for item in folds)
    positive_expectancy_folds = sum(
        item.result.trade_count > 0 and item.result.expectancy > 0 for item in folds
    )
    passing_pf_folds = sum(_profit_factor_passes_fold(item.result) for item in folds)
    shallower_drawdown_folds = sum(
        item.result.max_drawdown > item.result.benchmark_max_drawdown for item in folds
    )

    def fraction(count: int) -> float:
        return count / fold_count if fold_count else 0.0

    gates.extend(
        (
            _gate(19, "D", "rolling_folds_with_trades", fraction(trade_folds) >= 0.80,
                  {"passing": trade_folds, "total": fold_count, "fraction": fraction(trade_folds)},
                  ">= 80%"),
            _gate(20, "D", "rolling_positive_return", fraction(positive_return_folds) >= 0.60,
                  {"passing": positive_return_folds, "total": fold_count,
                   "fraction": fraction(positive_return_folds)}, ">= 60%"),
            _gate(21, "D", "rolling_positive_expectancy",
                  fraction(positive_expectancy_folds) >= 0.60,
                  {"passing": positive_expectancy_folds, "total": fold_count,
                   "fraction": fraction(positive_expectancy_folds)}, ">= 60%"),
            _gate(22, "D", "rolling_profit_factor", fraction(passing_pf_folds) >= 0.60,
                  {"passing": passing_pf_folds, "total": fold_count,
                   "fraction": fraction(passing_pf_folds)}, ">= 60%"),
            _gate(23, "D", "rolling_drawdown_vs_btc",
                  fraction(shallower_drawdown_folds) >= 0.60,
                  {"passing": shallower_drawdown_folds, "total": fold_count,
                   "fraction": fraction(shallower_drawdown_folds)}, ">= 60%"),
        )
    )
    return tuple(gates)


def evaluate_risk_gates(
    base: TrendV2Result,
    severe: TrendV2Result,
) -> tuple[GateResult, ...]:
    return (
        _gate(24, "E", "risk_trade_count", base.trade_count >= 20, base.trade_count, ">= 20"),
        _gate(25, "E", "risk_base_return", base.total_return > 0,
              base.total_return, "> 0"),
        _gate(26, "E", "risk_base_expectancy", base.expectancy > 0,
              base.expectancy, "> 0 USD"),
        _gate(27, "E", "risk_base_profit_factor", base.profit_factor >= 1.10,
              base.profit_factor, ">= 1.10"),
        _gate(28, "E", "risk_per_trade_cap",
              base.max_planned_risk_fraction <= 0.0035 + NUMERIC_TOLERANCE,
              base.max_planned_risk_fraction, "<= 0.35% + numeric tolerance"),
        _gate(29, "E", "entry_notional_cap",
              base.max_notional_fraction <= 0.50 + NUMERIC_TOLERANCE,
              base.max_notional_fraction, "<= 50% + numeric tolerance"),
        _gate(30, "E", "base_no_drawdown_halt", not base.max_drawdown_halted,
              base.max_drawdown_halted, "false"),
        _gate(31, "E", "risk_base_max_drawdown", base.max_drawdown > -0.08,
              base.max_drawdown, "> -8%"),
        _gate(32, "E", "risk_severe_return", severe.total_return > 0,
              severe.total_return, "> 0"),
        _gate(33, "E", "risk_severe_expectancy", severe.expectancy > 0,
              severe.expectancy, "> 0 USD"),
        _gate(34, "E", "risk_severe_profit_factor", severe.profit_factor > 1.0,
              severe.profit_factor, "> 1.0"),
        _gate(35, "E", "severe_no_drawdown_halt", not severe.max_drawdown_halted,
              severe.max_drawdown_halted, "false"),
        _gate(36, "E", "risk_entry_veto_invariants",
              base.entry_invariant_violations == 0
              and base.veto_entry_violations == 0
              and severe.entry_invariant_violations == 0
              and severe.veto_entry_violations == 0,
              {
                  "base_entry": base.entry_invariant_violations,
                  "base_veto": base.veto_entry_violations,
                  "severe_entry": severe.entry_invariant_violations,
                  "severe_veto": severe.veto_entry_violations,
              }, "all violation counts == 0"),
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
        for number, name in zip(range(24, 37), RISK_GATE_NAMES, strict=True)
    )


def _with_cost(config: TrendV2Config, scenario: str) -> TrendV2Config:
    costs = COST_SCENARIOS[scenario]
    return replace(
        config,
        fee_bps=costs["fee_bps"],
        slippage_bps=costs["slippage_bps"],
    )


def _summary(result: TrendV2Result) -> dict[str, Any]:
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
    if sha256_file(research_path) != TREND_V2_RESEARCH_SHA256:
        raise RuntimeError("Trend V2 research data hash mismatch")
    if sha256_file(validation_path) != TREND_V2_VALIDATION_SHA256:
        raise RuntimeError("Trend V2 validation data hash mismatch")

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
    baseline = BASELINE_TREND_V2_CONFIG
    configurations = (
        ("baseline", baseline),
        ("donchian_16", replace(baseline, donchian_lookback=16)),
        ("donchian_24", replace(baseline, donchian_lookback=24)),
        ("adx_20", replace(baseline, adx_entry_threshold=20.0)),
        ("adx_30", replace(baseline, adx_entry_threshold=30.0)),
        ("max_relative_atr_1_50", replace(baseline, max_relative_atr=1.50)),
        ("max_relative_atr_2_10", replace(baseline, max_relative_atr=2.10)),
        ("min_relative_atr_0_50", replace(baseline, min_relative_atr=0.50)),
        ("min_relative_atr_0_70", replace(baseline, min_relative_atr=0.70)),
    )
    return tuple(
        NeighborhoodResult(
            name=name,
            base=run_trend_v2_backtest(research, _with_cost(config, "base")),
            severe=run_trend_v2_backtest(research, _with_cost(config, "severe")),
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
        result = run_trend_v2_backtest(
            context,
            _with_cost(BASELINE_TREND_V2_CONFIG, "base"),
            evaluation_start_ms=test_start,
            evaluation_end_exclusive_ms=test_end,
        )
        folds.append(FoldResult(test_start, test_end, result))
        test_start += step_ms
    return tuple(folds)


def run_trend_v2_development_evidence(
    *,
    data_dir: str | Path = "data/cache/m2",
    report_path: str | Path = "artifacts/m3_trend_v2_development_evidence.json",
) -> dict[str, Any]:
    manifest = verify_trend_v2_policy_freeze()
    provenance = collect_source_provenance(require_clean=True)
    research, validation = _load_frozen_development_data(Path(data_dir))
    combined = [*research, *validation]
    validation_start = parse_utc(VALIDATION_START)
    validation_end = parse_utc(VALIDATION_END_EXCLUSIVE)

    validation_results = {
        scenario: run_trend_v2_backtest(
            combined,
            _with_cost(BASELINE_TREND_V2_CONFIG, scenario),
            evaluation_start_ms=validation_start,
            evaluation_end_exclusive_ms=validation_end,
        )
        for scenario in COST_SCENARIOS
    }
    control = run_trend_v2_backtest(
        combined,
        _with_cost(BASELINE_TREND_V2_CONFIG, "base"),
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
    risk_results: dict[str, TrendV2Result] = {}
    if signal_pass:
        risk_results = {
            scenario: run_trend_v2_backtest(
                combined,
                _with_cost(BASELINE_TREND_V2_CONFIG, scenario),
                evaluation_start_ms=validation_start,
                evaluation_end_exclusive_ms=validation_end,
                risk_sized=True,
            )
            for scenario in ("base", "severe")
        }
        risk_gates = evaluate_risk_gates(risk_results["base"], risk_results["severe"])
    else:
        risk_gates = blocked_risk_gates()

    gates = (*signal_gates, *risk_gates)
    all_pass = all(item.status == "PASS" for item in gates)
    if not signal_pass:
        decision = "REJECT_TREND_V2_SIGNAL_CYCLE"
        reported = validation_results["base"]
    elif not all_pass:
        decision = "REJECT_TREND_V2_EXECUTION_CYCLE"
        reported = risk_results["base"]
    else:
        decision = "ELIGIBLE_FOR_TREND_V2_FINAL_FREEZE_REVIEW"
        reported = risk_results["base"]

    report: dict[str, Any] = {
        "phase": "development_only",
        "cycle": "trend_v2_regime_filtered_volatility_aware_breakout",
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
            "unfiltered_v2_base": _summary(control),
            "trend_v1_historical_context": {
                "validation_total_return": -0.4507,
                "validation_max_drawdown": -0.5060,
                "validation_profit_factor": 0.7699,
                "validation_trade_count": 337,
                "role": "historical_context_only",
            },
        },
        "research_neighborhood": [
            {"name": item.name, "base": _summary(item.base), "severe": _summary(item.severe)}
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
        description="Run frozen Trend V2 evidence on 2021-2024 development data only"
    )
    parser.add_argument(
        "--report",
        default="artifacts/m3_trend_v2_development_evidence.json",
    )
    args = parser.parse_args()
    report = run_trend_v2_development_evidence(report_path=args.report)
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
