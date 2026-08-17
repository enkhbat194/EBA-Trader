from __future__ import annotations

import argparse
import json
import math
from dataclasses import dataclass
from pathlib import Path

from .backtest import BacktestResult, TrendBacktestConfig, run_trend_backtest
from .freeze import load_frozen_candidate
from .history import (
    Candle,
    fetch_binance_klines,
    load_csv,
    parse_utc,
    save_csv,
    validate_interval_window,
)


@dataclass(frozen=True, slots=True)
class StudyWindow:
    name: str
    start: str
    end: str


DEVELOPMENT_WINDOWS = (
    StudyWindow("research", "2021-01-01", "2024-01-01"),
    StudyWindow("validation", "2024-01-01", "2025-01-01"),
)
OOS_WINDOW = StudyWindow("out_of_sample", "2025-01-01", "2026-01-01")
DEFAULT_WINDOWS = DEVELOPMENT_WINDOWS

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


def _window_cache_path(base_dir: Path, symbol: str, interval: str, window: StudyWindow) -> Path:
    return base_dir / f"{symbol.lower()}_{interval}_{window.name}.csv"


def assert_oos_not_cached(base_dir: Path, symbol: str, interval: str) -> None:
    oos_path = _window_cache_path(base_dir, symbol, interval, OOS_WINDOW)
    if oos_path.exists():
        raise RuntimeError(
            "Frozen 2025 OOS cache already exists. Development evidence can no longer claim "
            "LOCKED_NOT_ACCESSED; quarantine the cycle instead of silently continuing."
        )


def _load_or_fetch_window(
    window: StudyWindow,
    *,
    symbol: str,
    interval: str,
    base_dir: Path,
    refresh: bool,
) -> list[Candle]:
    csv_path = _window_cache_path(base_dir, symbol, interval, window)
    start_ms = parse_utc(window.start)
    end_ms = parse_utc(window.end)

    if refresh or not csv_path.exists():
        candles = fetch_binance_klines(
            symbol,
            interval,
            start_ms,
            end_ms,
        )
        candles = validate_interval_window(candles, interval, start_ms, end_ms)
        save_csv(candles, csv_path)
        return candles

    candles = load_csv(csv_path)
    return validate_interval_window(candles, interval, start_ms, end_ms)


def _evaluate_window(
    candles: list[Candle],
    *,
    fast_ema: int,
    slow_ema: int,
    initial_cash: float,
) -> dict[str, object]:
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
    return scenarios


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
    assert_oos_not_cached(base_dir, symbol, interval)

    report: dict[str, object] = {
        "phase": "development",
        "symbol": symbol.upper(),
        "interval": interval,
        "fast_ema": fast_ema,
        "slow_ema": slow_ema,
        "initial_cash": initial_cash,
        "parameter_tuning": False,
        "holdout": {
            "name": OOS_WINDOW.name,
            "start": OOS_WINDOW.start,
            "end_exclusive": OOS_WINDOW.end,
            "status": "locked_not_downloaded",
            "cache_verified_absent": True,
        },
        "untouched_future_window": "2026+ remains outside the first baseline study",
        "windows": {},
    }

    window_report: dict[str, object] = {}
    for window in windows:
        if window.name == OOS_WINDOW.name:
            raise ValueError(
                "The frozen out-of-sample window cannot be opened by run_baseline_study"
            )
        candles = _load_or_fetch_window(
            window,
            symbol=symbol,
            interval=interval,
            base_dir=base_dir,
            refresh=refresh,
        )
        scenarios = _evaluate_window(
            candles,
            fast_ema=fast_ema,
            slow_ema=slow_ema,
            initial_cash=initial_cash,
        )
        window_report[window.name] = {
            "start": window.start,
            "end_exclusive": window.end,
            "candle_count": len(candles),
            "coverage": "exact",
            "scenarios": scenarios,
        }

    report["windows"] = window_report
    output = Path(report_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
    return report


def run_frozen_oos_study(
    *,
    confirm_frozen: bool,
    symbol: str = "BTCUSDT",
    interval: str = "15m",
    initial_cash: float = 1000.0,
    data_dir: str | Path = "data/cache/m2",
    report_path: str | Path = "artifacts/m2_trend_oos_2025.json",
    freeze_path: str | Path = "artifacts/m2_frozen_candidate.json",
    development_report_path: str | Path = "artifacts/m2_development_evidence.json",
    refresh: bool = False,
) -> dict[str, object]:
    if not confirm_frozen:
        raise ValueError(
            "Frozen OOS is locked. Confirm only after research/validation decisions are final."
        )

    output = Path(report_path)
    if output.exists():
        raise RuntimeError(
            "Frozen OOS report already exists. Do not rerun and retune against the holdout."
        )

    frozen = load_frozen_candidate(
        freeze_path=freeze_path,
        development_report_path=development_report_path,
    )
    fast_ema = int(frozen["fast_ema"])
    slow_ema = int(frozen["slow_ema"])

    base_dir = Path(data_dir)
    base_dir.mkdir(parents=True, exist_ok=True)
    candles = _load_or_fetch_window(
        OOS_WINDOW,
        symbol=symbol,
        interval=interval,
        base_dir=base_dir,
        refresh=refresh,
    )
    scenarios = _evaluate_window(
        candles,
        fast_ema=fast_ema,
        slow_ema=slow_ema,
        initial_cash=initial_cash,
    )
    report: dict[str, object] = {
        "phase": "frozen_out_of_sample",
        "symbol": symbol.upper(),
        "interval": interval,
        "fast_ema": fast_ema,
        "slow_ema": slow_ema,
        "initial_cash": initial_cash,
        "parameter_tuning": False,
        "development_report_sha256": frozen["development_report_sha256"],
        "retuning_after_open": "forbidden",
        "window": {
            "name": OOS_WINDOW.name,
            "start": OOS_WINDOW.start,
            "end_exclusive": OOS_WINDOW.end,
            "candle_count": len(candles),
            "coverage": "exact",
            "scenarios": scenarios,
        },
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
    return report


def baseline_study_cli() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Internal generic baseline runner; public first-cycle CLI is locked in locked_cli.py"
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
    print("holdout=2025 LOCKED")
    print("report=artifacts/m2_trend_baseline.json")


def frozen_oos_cli() -> None:
    parser = argparse.ArgumentParser(
        description="Open the frozen 2025 OOS using only the pre-frozen candidate"
    )
    parser.add_argument("--symbol", default="BTCUSDT")
    parser.add_argument("--interval", default="15m")
    parser.add_argument("--cash", type=float, default=1000.0)
    parser.add_argument("--confirm-frozen", action="store_true")
    args = parser.parse_args()

    report = run_frozen_oos_study(
        confirm_frozen=args.confirm_frozen,
        symbol=args.symbol,
        interval=args.interval,
        initial_cash=args.cash,
    )
    base = report["window"]["scenarios"]["base"]
    severe = report["window"]["scenarios"]["severe"]
    print(
        f"OOS 2025 fast={report['fast_ema']} slow={report['slow_ema']} "
        f"base_return={base['total_return']:.2%} "
        f"btc_buy_hold={base['benchmark_return']:.2%} "
        f"drawdown={base['max_drawdown']:.2%} "
        f"severe_return={severe['total_return']:.2%}"
    )
    print("retuning_after_open=FORBIDDEN")
    print("report=artifacts/m2_trend_oos_2025.json")
