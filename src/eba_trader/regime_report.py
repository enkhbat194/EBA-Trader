from __future__ import annotations

import argparse
import json
from pathlib import Path

from .backtest import TrendBacktestConfig, run_trend_backtest
from .history import load_csv
from .regime_diagnostics import diagnose_trades_by_regime


def regime_report_cli() -> None:
    parser = argparse.ArgumentParser(
        description="Break Trend Following V1 closed-trade results down by causal market regime"
    )
    parser.add_argument("--csv", required=True)
    parser.add_argument("--fast", type=int, default=20)
    parser.add_argument("--slow", type=int, default=50)
    parser.add_argument("--cash", type=float, default=1000.0)
    parser.add_argument("--fee-bps", type=float, default=10.0)
    parser.add_argument("--slippage-bps", type=float, default=5.0)
    parser.add_argument("--lookback-days", type=int, default=14)
    parser.add_argument("--threshold", type=float, default=1.5)
    parser.add_argument("--report", default="artifacts/m2_trend_regimes.json")
    args = parser.parse_args()

    candles = load_csv(args.csv)
    result = run_trend_backtest(
        candles,
        TrendBacktestConfig(
            fast_ema=args.fast,
            slow_ema=args.slow,
            initial_cash=args.cash,
            fee_bps=args.fee_bps,
            slippage_bps=args.slippage_bps,
        ),
    )
    diagnostics = diagnose_trades_by_regime(
        candles,
        result,
        lookback_days=args.lookback_days,
        threshold=args.threshold,
    )

    payload = {
        "method": {
            "fast_ema": args.fast,
            "slow_ema": args.slow,
            "lookback_days": diagnostics.lookback_days,
            "directional_threshold": diagnostics.threshold,
            "causal": True,
            "note": "Each trade is labeled using only fully completed price history before entry.",
        },
        "strategy": {
            "total_return": result.total_return,
            "benchmark_return": result.benchmark_return,
            "benchmark_max_drawdown": result.benchmark_max_drawdown,
            "max_drawdown": result.max_drawdown,
            "drawdown_better_than_btc": result.max_drawdown > result.benchmark_max_drawdown,
            "trade_count": result.trade_count,
        },
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

    output = Path(args.report)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")

    print(
        f"strategy_return={result.total_return:.2%} "
        f"btc_buy_hold={result.benchmark_return:.2%} "
        f"strategy_drawdown={result.max_drawdown:.2%} "
        f"btc_drawdown={result.benchmark_max_drawdown:.2%} "
        f"trades={result.trade_count}"
    )
    for item in diagnostics.stats:
        print(
            f"{item.regime.value}: trades={item.trade_count} "
            f"pnl={item.total_pnl:.2f} win_rate={item.win_rate:.1%} "
            f"avg_return={item.average_return:.2%}"
        )
    print(f"report={output}")
