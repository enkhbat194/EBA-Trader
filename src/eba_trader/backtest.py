from __future__ import annotations

import argparse
import math
from dataclasses import dataclass
from statistics import mean, pstdev
from typing import Iterable

from .history import Candle, load_csv


@dataclass(frozen=True, slots=True)
class TrendBacktestConfig:
    fast_ema: int = 20
    slow_ema: int = 50
    initial_cash: float = 1000.0
    fee_bps: float = 10.0
    slippage_bps: float = 5.0

    def __post_init__(self) -> None:
        if self.fast_ema <= 1 or self.slow_ema <= self.fast_ema:
            raise ValueError("Require 1 < fast_ema < slow_ema")
        if self.initial_cash <= 0:
            raise ValueError("initial_cash must be positive")
        if min(self.fee_bps, self.slippage_bps) < 0:
            raise ValueError("Costs cannot be negative")


@dataclass(frozen=True, slots=True)
class ClosedTrade:
    entry_time_ms: int
    exit_time_ms: int
    entry_price: float
    exit_price: float
    net_return: float
    pnl: float


@dataclass(frozen=True, slots=True)
class BacktestResult:
    initial_cash: float
    final_equity: float
    total_return: float
    benchmark_return: float
    max_drawdown: float
    trade_count: int
    win_rate: float
    profit_factor: float
    expectancy: float
    sharpe: float
    exposure: float
    total_cost: float
    trades: tuple[ClosedTrade, ...]


def ema(values: Iterable[float], period: int) -> list[float | None]:
    data = list(values)
    if period <= 1:
        raise ValueError("period must be > 1")
    result: list[float | None] = [None] * len(data)
    if len(data) < period:
        return result
    seed = mean(data[:period])
    result[period - 1] = seed
    alpha = 2.0 / (period + 1.0)
    current = seed
    for index in range(period, len(data)):
        current = alpha * data[index] + (1.0 - alpha) * current
        result[index] = current
    return result


def max_drawdown(equity_curve: list[float]) -> float:
    peak = equity_curve[0]
    worst = 0.0
    for equity in equity_curve:
        peak = max(peak, equity)
        drawdown = equity / peak - 1.0
        worst = min(worst, drawdown)
    return worst


def _safe_profit_factor(trades: list[ClosedTrade]) -> float:
    gross_profit = sum(max(trade.pnl, 0.0) for trade in trades)
    gross_loss = -sum(min(trade.pnl, 0.0) for trade in trades)
    if gross_loss == 0:
        return math.inf if gross_profit > 0 else 0.0
    return gross_profit / gross_loss


def run_trend_backtest(candles: Iterable[Candle], config: TrendBacktestConfig | None = None) -> BacktestResult:
    cfg = config or TrendBacktestConfig()
    bars = list(candles)
    if len(bars) < cfg.slow_ema + 2:
        raise ValueError("Not enough candles for trend backtest")

    closes = [bar.close for bar in bars]
    fast = ema(closes, cfg.fast_ema)
    slow = ema(closes, cfg.slow_ema)
    round_trip_cost_rate = (cfg.fee_bps + cfg.slippage_bps) / 10_000.0

    cash = cfg.initial_cash
    quantity = 0.0
    entry_equity = 0.0
    entry_price = 0.0
    entry_time_ms = 0
    total_cost = 0.0
    trades: list[ClosedTrade] = []
    equity_curve: list[float] = [cash]
    bar_returns: list[float] = []
    exposed_bars = 0

    previous_equity = cash
    previous_signal = False

    for index in range(cfg.slow_ema, len(bars) - 1):
        fast_value = fast[index]
        slow_value = slow[index]
        if fast_value is None or slow_value is None:
            continue

        signal = fast_value > slow_value
        next_bar = bars[index + 1]

        if not previous_signal and signal and quantity == 0.0:
            execution_price = next_bar.open * (1.0 + cfg.slippage_bps / 10_000.0)
            fee = cash * cfg.fee_bps / 10_000.0
            total_cost += fee + cash * cfg.slippage_bps / 10_000.0
            deployable = cash - fee
            quantity = deployable / execution_price
            entry_equity = cash
            entry_price = execution_price
            entry_time_ms = next_bar.open_time_ms
            cash = 0.0

        elif previous_signal and not signal and quantity > 0.0:
            execution_price = next_bar.open * (1.0 - cfg.slippage_bps / 10_000.0)
            gross = quantity * execution_price
            fee = gross * cfg.fee_bps / 10_000.0
            total_cost += fee + gross * cfg.slippage_bps / 10_000.0
            cash = gross - fee
            pnl = cash - entry_equity
            trades.append(
                ClosedTrade(
                    entry_time_ms=entry_time_ms,
                    exit_time_ms=next_bar.open_time_ms,
                    entry_price=entry_price,
                    exit_price=execution_price,
                    net_return=cash / entry_equity - 1.0,
                    pnl=pnl,
                )
            )
            quantity = 0.0

        mark_equity = cash if quantity == 0.0 else quantity * next_bar.close
        if quantity > 0.0:
            exposed_bars += 1
        if previous_equity > 0:
            bar_returns.append(mark_equity / previous_equity - 1.0)
        previous_equity = mark_equity
        equity_curve.append(mark_equity)
        previous_signal = signal

    if quantity > 0.0:
        final_bar = bars[-1]
        execution_price = final_bar.close * (1.0 - cfg.slippage_bps / 10_000.0)
        gross = quantity * execution_price
        fee = gross * cfg.fee_bps / 10_000.0
        total_cost += fee + gross * cfg.slippage_bps / 10_000.0
        cash = gross - fee
        trades.append(
            ClosedTrade(
                entry_time_ms=entry_time_ms,
                exit_time_ms=final_bar.close_time_ms,
                entry_price=entry_price,
                exit_price=execution_price,
                net_return=cash / entry_equity - 1.0,
                pnl=cash - entry_equity,
            )
        )
        equity_curve.append(cash)

    final_equity = cash
    wins = [trade for trade in trades if trade.pnl > 0]
    expectancy = mean([trade.pnl for trade in trades]) if trades else 0.0
    std = pstdev(bar_returns) if len(bar_returns) > 1 else 0.0
    sharpe = (mean(bar_returns) / std * math.sqrt(365.0 * 24.0 * 4.0)) if std > 0 else 0.0

    benchmark_entry = bars[cfg.slow_ema + 1].open * (1.0 + cfg.slippage_bps / 10_000.0)
    benchmark_exit = bars[-1].close * (1.0 - cfg.slippage_bps / 10_000.0)
    benchmark_multiplier = benchmark_exit / benchmark_entry
    benchmark_multiplier *= 1.0 - cfg.fee_bps / 10_000.0
    benchmark_multiplier *= 1.0 - cfg.fee_bps / 10_000.0

    return BacktestResult(
        initial_cash=cfg.initial_cash,
        final_equity=final_equity,
        total_return=final_equity / cfg.initial_cash - 1.0,
        benchmark_return=benchmark_multiplier - 1.0,
        max_drawdown=max_drawdown(equity_curve),
        trade_count=len(trades),
        win_rate=len(wins) / len(trades) if trades else 0.0,
        profit_factor=_safe_profit_factor(trades),
        expectancy=expectancy,
        sharpe=sharpe,
        exposure=exposed_bars / max(len(equity_curve) - 1, 1),
        total_cost=total_cost,
        trades=tuple(trades),
    )


def backtest_trend_cli() -> None:
    parser = argparse.ArgumentParser(description="Run EBA Trader Trend Following V1 research backtest")
    parser.add_argument("--csv", required=True)
    parser.add_argument("--fast", type=int, default=20)
    parser.add_argument("--slow", type=int, default=50)
    parser.add_argument("--cash", type=float, default=1000.0)
    parser.add_argument("--fee-bps", type=float, default=10.0)
    parser.add_argument("--slippage-bps", type=float, default=5.0)
    args = parser.parse_args()

    result = run_trend_backtest(
        load_csv(args.csv),
        TrendBacktestConfig(
            fast_ema=args.fast,
            slow_ema=args.slow,
            initial_cash=args.cash,
            fee_bps=args.fee_bps,
            slippage_bps=args.slippage_bps,
        ),
    )
    print(f"final_equity={result.final_equity:.2f}")
    print(f"total_return={result.total_return:.2%}")
    print(f"btc_buy_hold={result.benchmark_return:.2%}")
    print(f"max_drawdown={result.max_drawdown:.2%}")
    print(f"trades={result.trade_count}")
    print(f"win_rate={result.win_rate:.2%}")
    print(f"profit_factor={result.profit_factor:.3f}")
    print(f"expectancy_usd={result.expectancy:.4f}")
    print(f"sharpe_approx={result.sharpe:.3f}")
    print(f"exposure={result.exposure:.2%}")
    print(f"estimated_cost_usd={result.total_cost:.4f}")
