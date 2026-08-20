from __future__ import annotations

import hashlib
import json
import math
from collections.abc import Mapping
from pathlib import Path

from .data_policy import allowed_source_gap_ranges
from .execution_policy import (
    EXECUTION_POLICY_NAME,
    EXECUTION_POLICY_VERSION,
    FIRST_CYCLE_ATR_MULTIPLIER,
    FIRST_CYCLE_ATR_PERIOD,
    FIRST_CYCLE_DAILY_LOSS_LIMIT,
    FIRST_CYCLE_MAX_DRAWDOWN_HALT,
    FIRST_CYCLE_RISK_FRACTION,
)
from .history import find_interval_gaps, load_csv, parse_utc, validate_interval_window
from .provenance import collect_source_provenance
from .research import COST_SCENARIOS
from .risk_trend import RiskTrendConfig, RiskTrendResult, run_risk_sized_trend_backtest
from .study_policy import (
    FIRST_CYCLE_FAST_EMA,
    FIRST_CYCLE_INITIAL_CASH,
    FIRST_CYCLE_INTERVAL,
    FIRST_CYCLE_SLOW_EMA,
    FIRST_CYCLE_SYMBOL,
    RESEARCH_END_EXCLUSIVE,
    RESEARCH_START,
    VALIDATION_END_EXCLUSIVE,
    VALIDATION_START,
)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _json_number(value: float) -> float | None:
    return value if math.isfinite(value) else None


def risk_result_to_dict(result: RiskTrendResult) -> dict[str, object]:
    max_planned_risk = max(
        (item.planned_risk_fraction for item in result.trades),
        default=0.0,
    )
    return {
        "initial_cash": result.initial_cash,
        "final_equity": result.final_equity,
        "total_return": result.total_return,
        "annualized_return": result.annualized_return,
        "benchmark_return": result.benchmark_return,
        "benchmark_max_drawdown": result.benchmark_max_drawdown,
        "benchmark_relative_return": result.benchmark_relative_return,
        "max_drawdown": result.max_drawdown,
        "trade_count": result.trade_count,
        "win_rate": result.win_rate,
        "profit_factor": _json_number(result.profit_factor),
        "expectancy": result.expectancy,
        "average_win": result.average_win,
        "average_loss": result.average_loss,
        "sharpe": result.sharpe,
        "sortino": result.sortino,
        "time_exposure": result.time_exposure,
        "average_notional_fraction": result.average_notional_fraction,
        "max_planned_risk_fraction": max_planned_risk,
        "total_cost": result.total_cost,
        "stop_out_count": result.stop_out_count,
        "daily_halt_count": result.daily_halt_count,
        "max_drawdown_halted": result.max_drawdown_halted,
    }


def _load_exact_window(path: Path, *, start: str, end: str):
    rows = load_csv(path)
    return validate_interval_window(
        rows,
        FIRST_CYCLE_INTERVAL,
        parse_utc(start),
        parse_utc(end),
        allowed_missing_ranges=allowed_source_gap_ranges(
            FIRST_CYCLE_SYMBOL,
            FIRST_CYCLE_INTERVAL,
        ),
    )


def _evaluate_cost_scenarios(candles, costs: Mapping[str, Mapping[str, float]]):
    scenarios: dict[str, object] = {}
    for name in ("base", "adverse", "severe"):
        scenario = costs[name]
        result = run_risk_sized_trend_backtest(
            candles,
            RiskTrendConfig(
                fast_ema=FIRST_CYCLE_FAST_EMA,
                slow_ema=FIRST_CYCLE_SLOW_EMA,
                atr_period=FIRST_CYCLE_ATR_PERIOD,
                atr_multiplier=FIRST_CYCLE_ATR_MULTIPLIER,
                risk_fraction=FIRST_CYCLE_RISK_FRACTION,
                daily_loss_limit=FIRST_CYCLE_DAILY_LOSS_LIMIT,
                max_drawdown_halt=FIRST_CYCLE_MAX_DRAWDOWN_HALT,
                initial_cash=FIRST_CYCLE_INITIAL_CASH,
                fee_bps=float(scenario["fee_bps"]),
                slippage_bps=float(scenario["slippage_bps"]),
            ),
        )
        scenarios[name] = risk_result_to_dict(result)
    return scenarios


def _load_signal_authority(
    development_report_path: Path,
    development_verdict_path: Path,
) -> tuple[dict[str, object], dict[str, object]]:
    if not development_report_path.is_file():
        raise FileNotFoundError("Signal development evidence report is missing")
    if not development_verdict_path.is_file():
        raise FileNotFoundError("Signal development verdict is missing")

    signal = json.loads(development_report_path.read_text(encoding="utf-8"))
    verdict = json.loads(development_verdict_path.read_text(encoding="utf-8"))
    if verdict.get("status") != "ELIGIBLE_FOR_FROZEN_OOS":
        raise RuntimeError("Signal baseline did not pass its predeclared development screening")
    if verdict.get("all_gates_passed") is not True:
        raise RuntimeError("Signal development gates did not all pass")
    if verdict.get("development_report_sha256") != _sha256(development_report_path):
        raise RuntimeError("Signal verdict no longer matches signal development evidence")
    return signal, verdict


def run_risk_execution_evidence(
    *,
    data_dir: str | Path = "data/cache/m2",
    signal_report_path: str | Path = "artifacts/m2_development_evidence.json",
    signal_verdict_path: str | Path = "artifacts/m2_development_verdict.json",
    report_path: str | Path = "artifacts/m2_risk_execution_evidence.json",
) -> dict[str, object]:
    """Validate the predeclared risk-sized execution layer before frozen OOS is opened."""
    provenance = collect_source_provenance(require_clean=True)
    signal_path = Path(signal_report_path)
    verdict_path = Path(signal_verdict_path)
    signal, verdict = _load_signal_authority(signal_path, verdict_path)

    if str(signal.get("symbol", "")).upper() != FIRST_CYCLE_SYMBOL:
        raise ValueError("Signal development symbol does not match first-cycle policy")
    if str(signal.get("interval", "")) != FIRST_CYCLE_INTERVAL:
        raise ValueError("Signal development interval does not match first-cycle policy")

    base_dir = Path(data_dir)
    research_path = base_dir / f"{FIRST_CYCLE_SYMBOL.lower()}_{FIRST_CYCLE_INTERVAL}_research.csv"
    validation_path = base_dir / (
        f"{FIRST_CYCLE_SYMBOL.lower()}_{FIRST_CYCLE_INTERVAL}_validation.csv"
    )
    if not research_path.is_file() or not validation_path.is_file():
        raise FileNotFoundError("Development historical caches are missing")

    research_candles = _load_exact_window(
        research_path,
        start=RESEARCH_START,
        end=RESEARCH_END_EXCLUSIVE,
    )
    validation_candles = _load_exact_window(
        validation_path,
        start=VALIDATION_START,
        end=VALIDATION_END_EXCLUSIVE,
    )
    interval_ms = 15 * 60 * 1000

    def dataset_gaps(candles):
        return [
            {
                "missing_start_ms": previous + interval_ms,
                "missing_end_exclusive_ms": current,
                "missing_candle_count": (current - previous) // interval_ms - 1,
            }
            for previous, current in find_interval_gaps(candles, FIRST_CYCLE_INTERVAL)
        ]

    costs = signal["baseline"].get("cost_scenarios", COST_SCENARIOS)
    report: dict[str, object] = {
        "phase": "risk_execution_development",
        "source_provenance": provenance,
        "signal_development_report": str(signal_path),
        "signal_development_report_sha256": _sha256(signal_path),
        "signal_development_verdict": str(verdict_path),
        "signal_development_verdict_sha256": _sha256(verdict_path),
        "signal_screening_status": verdict["status"],
        "symbol": FIRST_CYCLE_SYMBOL,
        "interval": FIRST_CYCLE_INTERVAL,
        "initial_cash": FIRST_CYCLE_INITIAL_CASH,
        "strategy": {
            "fast_ema": FIRST_CYCLE_FAST_EMA,
            "slow_ema": FIRST_CYCLE_SLOW_EMA,
        },
        "execution_policy": {
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
        },
        "cost_scenarios": costs,
        "datasets": {
            "research": {
                "path": str(research_path),
                "sha256": _sha256(research_path),
                "start": RESEARCH_START,
                "end_exclusive": RESEARCH_END_EXCLUSIVE,
                "candle_count": len(research_candles),
                "source_gaps": dataset_gaps(research_candles),
            },
            "validation": {
                "path": str(validation_path),
                "sha256": _sha256(validation_path),
                "start": VALIDATION_START,
                "end_exclusive": VALIDATION_END_EXCLUSIVE,
                "candle_count": len(validation_candles),
                "source_gaps": dataset_gaps(validation_candles),
            },
        },
        "windows": {
            "research": {
                "scenarios": _evaluate_cost_scenarios(research_candles, costs),
            },
            "validation": {
                "scenarios": _evaluate_cost_scenarios(validation_candles, costs),
            },
        },
        "oos_2025": "LOCKED_NOT_ACCESSED",
    }

    output = Path(report_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
    return report


def main() -> None:
    report = run_risk_execution_evidence()
    validation = report["windows"]["validation"]["scenarios"]
    base = validation["base"]
    severe = validation["severe"]
    print(
        f"risk_model={report['execution_policy']['name']} "
        f"validation_return={base['total_return']:.2%} "
        f"validation_dd={base['max_drawdown']:.2%} "
        f"risk_per_trade_max={base['max_planned_risk_fraction']:.3%} "
        f"severe_return={severe['total_return']:.2%}"
    )
    print("oos_2025=LOCKED_NOT_ACCESSED")
    print("report=artifacts/m2_risk_execution_evidence.json")


if __name__ == "__main__":
    main()
