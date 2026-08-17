from __future__ import annotations

import argparse
import json
from pathlib import Path

from .backtest import TrendBacktestConfig, run_trend_backtest
from .history import load_csv
from .regime_diagnostics import diagnose_trades_by_regime
from .research import run_baseline_study
from .validation import (
    _neighborhood_to_dict,
    _walk_forward_to_dict,
    run_parameter_neighborhood,
    run_walk_forward,
)

FIRST_CYCLE_FAST_EMA = 20
FIRST_CYCLE_SLOW_EMA = 50


def _regime_payload(candles: list, *, fast: int, slow: int, cash: float) -> dict[str, object]:
    result = run_trend_backtest(
        candles,
        TrendBacktestConfig(
            fast_ema=fast,
            slow_ema=slow,
            initial_cash=cash,
            fee_bps=10.0,
            slippage_bps=5.0,
        ),
    )
    diagnostics = diagnose_trades_by_regime(candles, result)
    return {
        "strategy_total_return": result.total_return,
        "benchmark_return": result.benchmark_return,
        "max_drawdown": result.max_drawdown,
        "trade_count": result.trade_count,
        "regimes": {
            item.regime.value: {
                "trade_count": item.trade_count,
                "total_pnl": item.total_pnl,
                "average_pnl": item.average_pnl,
                "win_rate": item.win_rate,
                "average_return": item.average_return,
            }
            for item in diagnostics.stats
        },
    }


def run_development_evidence(
    *,
    symbol: str = "BTCUSDT",
    interval: str = "15m",
    initial_cash: float = 1000.0,
    data_dir: str | Path = "data/cache/m2",
    report_path: str | Path = "artifacts/m2_development_evidence.json",
    refresh: bool = False,
) -> dict[str, object]:
    """Run the first development cycle with the predeclared EMA 20/50 baseline."""
    fast_ema = FIRST_CYCLE_FAST_EMA
    slow_ema = FIRST_CYCLE_SLOW_EMA
    base_dir = Path(data_dir)
    baseline = run_baseline_study(
        symbol=symbol,
        interval=interval,
        fast_ema=fast_ema,
        slow_ema=slow_ema,
        initial_cash=initial_cash,
        data_dir=base_dir,
        report_path="artifacts/m2_trend_baseline.json",
        refresh=refresh,
    )

    research_path = base_dir / f"{symbol.lower()}_{interval}_research.csv"
    validation_path = base_dir / f"{symbol.lower()}_{interval}_validation.csv"
    research_candles = load_csv(research_path)
    validation_candles = load_csv(validation_path)

    neighborhood = run_parameter_neighborhood(
        research_candles,
        initial_cash=initial_cash,
        fee_bps=10.0,
        slippage_bps=5.0,
    )
    walk_forward = run_walk_forward(
        research_candles,
        train_days=180,
        test_days=30,
        step_days=30,
        initial_cash=initial_cash,
        fee_bps=10.0,
        slippage_bps=5.0,
    )

    report: dict[str, object] = {
        "phase": "development_only",
        "cycle": "trend_v1_predeclared_ema_20_50",
        "symbol": symbol.upper(),
        "interval": interval,
        "data_dir": str(base_dir),
        "frozen_baseline": {"fast_ema": fast_ema, "slow_ema": slow_ema},
        "parameter_neighborhood_role": "fragility_diagnostic_not_tuning",
        "oos_2025": "LOCKED_NOT_ACCESSED",
        "baseline": baseline,
        "research_robustness": {
            "parameter_neighborhood": _neighborhood_to_dict(neighborhood),
            "walk_forward": _walk_forward_to_dict(walk_forward),
        },
        "regime_diagnostics": {
            "research": _regime_payload(
                research_candles,
                fast=fast_ema,
                slow=slow_ema,
                cash=initial_cash,
            ),
            "validation": _regime_payload(
                validation_candles,
                fast=fast_ema,
                slow=slow_ema,
                cash=initial_cash,
            ),
        },
    }

    output = Path(report_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
    return report


def development_evidence_cli() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Run the predeclared EMA 20/50 M2 development evidence without opening 2025 OOS"
        )
    )
    parser.add_argument("--symbol", default="BTCUSDT")
    parser.add_argument("--interval", default="15m")
    parser.add_argument("--cash", type=float, default=1000.0)
    parser.add_argument("--refresh", action="store_true")
    args = parser.parse_args()

    report = run_development_evidence(
        symbol=args.symbol,
        interval=args.interval,
        initial_cash=args.cash,
        refresh=args.refresh,
    )

    research_base = report["baseline"]["windows"]["research"]["scenarios"]["base"]
    validation_base = report["baseline"]["windows"]["validation"]["scenarios"]["base"]
    robustness = report["research_robustness"]
    neighborhood = robustness["parameter_neighborhood"]
    walk_forward = robustness["walk_forward"]

    print("baseline=EMA20/50 PREDECLARED")
    print(
        f"research_return={research_base['total_return']:.2%} "
        f"research_btc={research_base['benchmark_return']:.2%} "
        f"validation_return={validation_base['total_return']:.2%} "
        f"validation_btc={validation_base['benchmark_return']:.2%}"
    )
    print(
        f"parameter_positive={neighborhood['positive_return_fraction']:.1%} "
        f"walk_forward_positive={walk_forward['positive_test_fraction']:.1%} "
        f"walk_forward_beats_btc={walk_forward['benchmark_beating_fraction']:.1%}"
    )
    print("parameter_neighborhood=DIAGNOSTIC_ONLY")
    print("oos_2025=LOCKED_NOT_ACCESSED")
    print("report=artifacts/m2_development_evidence.json")
