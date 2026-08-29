from __future__ import annotations

import math
from collections.abc import Iterable
from dataclasses import dataclass
from statistics import mean

from . import backtest as bt
from .history import Candle


@dataclass(frozen=True, slots=True)
class DonchianBreakoutConfig:
    entry_lookback: int = 24
    exit_lookback: int = 12
    initial_cash: float = 10_000.0
    fee_bps: float = 4.0
    slippage_bps: float = 1.5

    def __post_init__(self) -> None:
        if self.entry_lookback < 2:
            raise ValueError("entry_lookback must be >= 2")
        if self.exit_lookback < 2:
            raise ValueError("exit_lookback must be >= 2")
        if self.exit_lookback > self.entry_lookback:
            raise ValueError("exit_lookback must be <= entry_lookback")
        if not math.isfinite(self.initial_cash) or self.initial_cash <= 0.0:
            raise ValueError("initial_cash must be positive and finite")
        for name, value in (("fee_bps", self.fee_bps), ("slippage_bps", self.slippage_bps)):
            if not math.isfinite(value) or value < 0.0:
                raise ValueError(f"{name} must be non-negative and finite")


def donchian_signals(
    candles: Iterable[Candle],
    config: DonchianBreakoutConfig | None = None,
) -> tuple[tuple[bool, ...], tuple[bool, ...]]:
    """Return causal long-entry and long-exit signals from completed candles.

    At index ``i`` the channel uses only candles strictly before ``i``. The current candle's
    close may confirm the breakout/breakdown, and execution is deferred to the next candle open.
    """
    cfg = config or DonchianBreakoutConfig()
    bars = list(candles)
    entries = [False] * len(bars)
    exits = [False] * len(bars)
    warmup = max(cfg.entry_lookback, cfg.exit_lookback)
    for index in range(warmup, len(bars)):
        entry_window = bars[index - cfg.entry_lookback : index]
        exit_window = bars[index - cfg.exit_lookback : index]
        prior_high = max(bar.high for bar in entry_window)
        prior_low = min(bar.low for bar in exit_window)
        entries[index] = bars[index].close > prior_high
        exits[index] = bars[index].close < prior_low
    return tuple(entries), tuple(exits)


def _first_evaluation_index(
    bars: list[Candle],
    config: DonchianBreakoutConfig,
    trade_start_time_ms: int | None,
) -> int:
    minimum = max(config.entry_lookback, config.exit_lookback) + 1
    if minimum >= len(bars):
        raise ValueError("Not enough candles for Donchian breakout backtest")
    if trade_start_time_ms is None:
        return minimum
    for index in range(minimum, len(bars)):
        if bars[index].open_time_ms >= trade_start_time_ms:
            return index
    raise ValueError("trade_start_time_ms is after the available candles")


def run_donchian_breakout_backtest(
    candles: Iterable[Candle],
    config: DonchianBreakoutConfig | None = None,
    *,
    trade_start_time_ms: int | None = None,
) -> bt.BacktestResult:
    """Run a long-only Donchian breakout with next-open execution and shared EBA metrics."""
    cfg = config or DonchianBreakoutConfig()
    bars = list(candles)
    warmup = max(cfg.entry_lookback, cfg.exit_lookback)
    if len(bars) < warmup + 2:
        raise ValueError("Not enough candles for Donchian breakout backtest")

    evaluation_index = _first_evaluation_index(bars, cfg, trade_start_time_ms)
    evaluation_start_ms = bars[evaluation_index].open_time_ms
    evaluation_bars = bars[evaluation_index:]
    entries, exits = donchian_signals(bars, cfg)

    cash = cfg.initial_cash
    quantity = 0.0
    entry_equity = 0.0
    entry_price = 0.0
    entry_time_ms = 0
    total_cost = 0.0
    trades: list[bt.ClosedTrade] = []
    equity_curve = [cash]
    bar_returns: list[float] = []
    exposed_bars = 0
    evaluated_bars = 0
    previous_equity = cash

    for index in range(warmup, len(bars) - 1):
        next_bar = bars[index + 1]
        if next_bar.open_time_ms < evaluation_start_ms:
            continue

        if entries[index] and quantity == 0.0:
            execution_price = next_bar.open * (1.0 + cfg.slippage_bps / 10_000.0)
            fee = cash * cfg.fee_bps / 10_000.0
            slippage_cost = cash * cfg.slippage_bps / 10_000.0
            total_cost += fee + slippage_cost
            deployable = cash - fee
            quantity = deployable / execution_price
            entry_equity = cash
            entry_price = execution_price
            entry_time_ms = next_bar.open_time_ms
            cash = 0.0
        elif exits[index] and quantity > 0.0:
            execution_price = next_bar.open * (1.0 - cfg.slippage_bps / 10_000.0)
            gross = quantity * execution_price
            fee = gross * cfg.fee_bps / 10_000.0
            slippage_cost = gross * cfg.slippage_bps / 10_000.0
            total_cost += fee + slippage_cost
            cash = gross - fee
            trades.append(
                bt.ClosedTrade(
                    entry_time_ms=entry_time_ms,
                    exit_time_ms=next_bar.open_time_ms,
                    entry_price=entry_price,
                    exit_price=execution_price,
                    net_return=cash / entry_equity - 1.0,
                    pnl=cash - entry_equity,
                )
            )
            quantity = 0.0

        mark_equity = cash if quantity == 0.0 else quantity * next_bar.close
        if quantity > 0.0:
            exposed_bars += 1
        if previous_equity > 0.0:
            bar_returns.append(mark_equity / previous_equity - 1.0)
        previous_equity = mark_equity
        equity_curve.append(mark_equity)
        evaluated_bars += 1

    if quantity > 0.0:
        final_bar = bars[-1]
        execution_price = final_bar.close * (1.0 - cfg.slippage_bps / 10_000.0)
        gross = quantity * execution_price
        fee = gross * cfg.fee_bps / 10_000.0
        slippage_cost = gross * cfg.slippage_bps / 10_000.0
        total_cost += fee + slippage_cost
        cash = gross - fee
        trades.append(
            bt.ClosedTrade(
                entry_time_ms=entry_time_ms,
                exit_time_ms=final_bar.close_time_ms,
                entry_price=entry_price,
                exit_price=execution_price,
                net_return=cash / entry_equity - 1.0,
                pnl=cash - entry_equity,
            )
        )
        if previous_equity > 0.0:
            bar_returns.append(cash / previous_equity - 1.0)
        equity_curve.append(cash)

    final_equity = cash
    wins = [trade.pnl for trade in trades if trade.pnl > 0.0]
    losses = [trade.pnl for trade in trades if trade.pnl < 0.0]
    expectancy = mean([trade.pnl for trade in trades]) if trades else 0.0
    average_win = mean(wins) if wins else 0.0
    average_loss = mean(losses) if losses else 0.0
    bars_per_year = bt._infer_bars_per_year(evaluation_bars)
    sharpe, sortino = bt._risk_adjusted_ratios(bar_returns, bars_per_year)
    benchmark_return, benchmark_drawdown = bt._buy_and_hold_metrics(evaluation_bars, cfg)
    total_return = final_equity / cfg.initial_cash - 1.0

    return bt.BacktestResult(
        initial_cash=cfg.initial_cash,
        final_equity=final_equity,
        total_return=total_return,
        annualized_return=bt._annualized_return(cfg.initial_cash, final_equity, evaluation_bars),
        benchmark_return=benchmark_return,
        benchmark_max_drawdown=benchmark_drawdown,
        benchmark_relative_return=total_return - benchmark_return,
        max_drawdown=bt.max_drawdown(equity_curve),
        trade_count=len(trades),
        win_rate=len(wins) / len(trades) if trades else 0.0,
        profit_factor=bt._safe_profit_factor(trades),
        expectancy=expectancy,
        average_win=average_win,
        average_loss=average_loss,
        sharpe=sharpe,
        sortino=sortino,
        exposure=exposed_bars / max(evaluated_bars, 1),
        total_cost=total_cost,
        trades=tuple(trades),
    )
