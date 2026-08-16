from __future__ import annotations

import argparse
import json
import math
from dataclasses import dataclass
from pathlib import Path

from .backtest import BacktestResult, TrendBacktestConfig, run_trend_backtest
from .history import (
    fetch_binance_klines,
    find_interval_gaps,
    load_csv,
    parse_utc,
    save_csv,
)


@dataclass(frozen=True, slots=True)
class StudyWindow:
    name: str
    start: str
    end: str


DEFAULT_WINDOWS = (
    StudyWindow("research", "2021-01-01", "2024-01-01"),
    StudyWindow("validation", "2024-01-01", "2025-01-01"),
    StudyWindow("out_of_sample", "2025-01-01", "2026-01-01"),
)

COST_SCENARIOS = {
    "base": {"fee_bps": 10.0, "slippage_bps": 5.0},
    "adverse": {"fee_bps": 10.0, "slippage_bps": 10.0},
    "severe": {"fee_bps": 15.0, "slippage_bps": 20.0},
}


def _json_number(value: float) -> float | None:
    return value if math.isfinite(value) else None


def result_to_dict(result: BacktestResult) -> dict[str, float | int | None]:
    return {
        "initial_cash": result.initial_cash,
        "final_equity": result.final_equity,
        "total_return": result.total_return,
        "annualized_return": result.annualized_return,
        "benchmark_return": result.benchmark_return,
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
        "exposure": result.exposure,
        "total_cost": result.total_cost,
    }


def run_baseline_study(
    *,
    symbol: str = "BTCUSDT",
    interval: str = "15m",
    fast_ema: int = 20,
    slow_ema: int = 50,
    initial_cash: float = 1000.0,
    data_dir: str | Path = "data/cache/m2",
    report_path: str | Path = "artifacts/m2_trend_baseline.json",
    windows: tuple[StudyWindow, ...] = DEFAULT_WINDOWS,
    refresh: bool = False,
) -> dict[str, object]:
    base_dir = Path(data_dir)
    base_dir.mkdir(parents=True, exist_ok=True)

    report: dict[str, object] = {
        "symbol": symbol.upper(),
        "interval": interval,
        "fast_ema": fast_ema,
        "slow_ema": slow_ema,
        "initial_cash": initial_cash,
        "parameter_tuning": False,
        "untouched_future_window": "2026+ remains outside this baseline study",
        "windows": {},
    }

    window_report: dict[str, object] = {}
    for window in windows:
        csv_path = base_dir / f"{symbol.lower()}_{interval}_{window.name}.csv"
        if refresh or not csv_path.exists():
            candles = fetch_binance_klines(
                symbol,
                interval,
                parse_utc(window.start),
                parse_utc(window.end),
            )
            gaps = find_interval_gaps(candles, interval)
            if gaps:
                raise RuntimeError(
                    f"{window.name} has {len(gaps)} interval gaps; "
                    "baseline study refuses incomplete data"
                )
            save_csv(candles, csv_path)
        else:
            candles = load_csv(csv_path)
            gaps = find_interval_gaps(candles, interval)
            if gaps:
                raise RuntimeError(
                    f"Cached {window.name} data has {len(gaps)} interval gaps; "
                    "delete cache and refetch"
                )

        scenarios: dict[str, object] = {}
        for scenario_name, costs in COST_SCENARIOS.items():
            result = run_trend_backtest(
                candles,
                TrendBacktestConfig(
                    fast_ema=fast_ema,
                    slow_ema=slow_ema,
                    initial_cash=initial_cash,
                    fee_bps=costs["fee_bps"],
                    slippage_bps=costs["slippage_bps"],
                ),
            )
            scenarios[scenario_name] = result_to_dict(result)

        window_report[window.name] = {
            "start": window.start,
            "end_exclusive": window.end,
            "candle_count": len(candles),
            "gap_count": 0,
            "scenarios": scenarios,
        }

    report["windows"] = window_report
    output = Path(report_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
    return report


def baseline_study_cli() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Download frozen BTC/USDT research windows and run Trend Following V1 cost stress"
        )
    )
    parser.add_argument("--symbol", default="BTCUSDT")
    parser.add_argument("--interval", default="15m")
    parser.add_argument("--fast", type=int, default=20)
    parser.add_argument("--slow", type=int, default=50)
    parser.add_argument("--cash", type=float, default=1000.0)
    parser.add_argument("--refresh", action="store_true")
    args = parser.parse_args()

    report = run_baseline_study(
        symbol=args.symbol,
        interval=args.interval,
        fast_ema=args.fast,
        slow_ema=args.slow,
        initial_cash=args.cash,
        refresh=args.refresh,
    )

    print(
        f"study symbol={report['symbol']} interval={report['interval']} "
        f"fast={report['fast_ema']} slow={report['slow_ema']}"
    )
    for window_name, window in report["windows"].items():
        base = window["scenarios"]["base"]
        severe = window["scenarios"]["severe"]
        print(
            f"{window_name}: candles={window['candle_count']} "
            f"base_return={base['total_return']:.2%} "
            f"base_benchmark={base['benchmark_return']:.2%} "
            f"base_drawdown={base['max_drawdown']:.2%} "
            f"severe_return={severe['total_return']:.2%}"
        )
    print("report=artifacts/m2_trend_baseline.json")
