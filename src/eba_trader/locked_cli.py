from __future__ import annotations

import argparse

from .research import run_baseline_study
from .study_policy import (
    FIRST_CYCLE_FAST_EMA,
    FIRST_CYCLE_INITIAL_CASH,
    FIRST_CYCLE_INTERVAL,
    FIRST_CYCLE_SLOW_EMA,
    FIRST_CYCLE_SYMBOL,
)


def baseline_study_cli() -> None:
    parser = argparse.ArgumentParser(
        description="Run the first-cycle predeclared EMA 20/50 development baseline"
    )
    parser.add_argument("--refresh", action="store_true")
    args = parser.parse_args()

    report = run_baseline_study(
        symbol=FIRST_CYCLE_SYMBOL,
        interval=FIRST_CYCLE_INTERVAL,
        fast_ema=FIRST_CYCLE_FAST_EMA,
        slow_ema=FIRST_CYCLE_SLOW_EMA,
        initial_cash=FIRST_CYCLE_INITIAL_CASH,
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
