from __future__ import annotations

import argparse

from .evidence import FIRST_CYCLE_FAST_EMA, FIRST_CYCLE_SLOW_EMA
from .research import run_baseline_study


def baseline_study_cli() -> None:
    parser = argparse.ArgumentParser(
        description="Run the first-cycle predeclared EMA 20/50 development baseline"
    )
    parser.add_argument("--symbol", default="BTCUSDT")
    parser.add_argument("--interval", default="15m")
    parser.add_argument("--cash", type=float, default=1000.0)
    parser.add_argument("--refresh", action="store_true")
    args = parser.parse_args()

    report = run_baseline_study(
        symbol=args.symbol,
        interval=args.interval,
        fast_ema=FIRST_CYCLE_FAST_EMA,
        slow_ema=FIRST_CYCLE_SLOW_EMA,
        initial_cash=args.cash,
        refresh=args.refresh,
    )

    print("baseline=EMA20/50 PREDECLARED")
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
    print("parameter_override=DISABLED")
    print("holdout=2025 LOCKED")
    print("report=artifacts/m2_trend_baseline.json")
