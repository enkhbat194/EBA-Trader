from __future__ import annotations

import math
import statistics
from collections.abc import Iterable
from dataclasses import dataclass
from statistics import mean

from . import backtest as bt
from .history import Candle


@dataclass(frozen=True, slots=True)
class MeanReversionConfig:
    lookback: int = 32
    entry_z: float = 2.0
    exit_z: float = 0.25
    initial_cash: float = 10_000.0
    fee_bps: float = 4.0
    slippage_bps: float = 1.5

    def __post_init__(self) -> None:
        if self.lookback < 5:
            raise ValueError("lookback must be >= 5")
        if not math.isfinite(self.entry_z) or self.entry_z <= 0.0:
            raise ValueError("entry_z must be positive and finite")
        if not math.isfinite(self.exit_z) or self.exit_z < 0.0:
            raise ValueError("exit_z must be non-negative and finite")
        if self.exit_z >= self.entry_z:
            raise ValueError("exit_z must be smaller than entry_z")
        if not math.isfinite(self.initial_cash) or self.initial_cash <= 0.0:
            raise ValueError("initial_cash must be positive and finite")
        for name, value in (("fee_bps", self.fee_bps), ("slippage_bps", self.slippage_bps)):
            if not math.isfinite(value) or value < 0.0:
                raise ValueError(f"{name} must be non-negative and finite")


def mean_reversion_signals(
    candles: Iterable[Candle],
    config: MeanReversionConfig | None = None,
) -> tuple[tuple[bool, ...], tuple[bool, ...], tuple[float | None, ...]]:
    """Return causal long-entry/exit signals and z-scores.

    At index ``i`` the rolling mean and sample standard deviation use closes strictly before
    ``i``. The completed candle at ``i`` may trigger a signal; execution is deferred to the next
    candle open. This prevents the execution candle from influencing its own decision.
    """
    cfg = config or MeanReversionConfig()
    bars = list(candles)
    entries = [False] * len(bars)
    exits = [False] * len(bars)
    z_scores: list[float | None] = [None] * len(bars)

    for index in range(cfg.lookback, len(bars)):
        prior_closes = [bar.close for bar in bars[index - cfg.lookback : index]]
        center = statistics.fmean(prior_closes)
        spread = statistics.stdev(prior_closes)
        if spread <= 0.0 or not math.isfinite(spread):
            continue
        z_score = (bars[index].close - center) / spread
        z_scores[index] = z_score
        entries[index] = z_score <= -cfg.entry_z
        exits[index] = z_score >= -cfg.exit_z

    return tuple(entries), tuple(exits), tuple(z_scores)


def _first_evaluation_index(
    bars: list[Candle],
    config: MeanReversionConfig,
    trade_start_time_ms: int | None,
) -> int:
    minimum = config.lookback + 1
    if minimum >= len(bars):
        raise ValueError("Not enough candles for mean-reversion backtest")
    if trade_start_time_ms is None:
        return minimum
    for index in range(minimum, len(bars)):
        if bars[index].open_time_ms >= trade_start_time_ms:
            return index
    raise ValueError("trade_start_time_ms is after the available candles")


def run_mean_reversion_backtest(
    candles: Iterable[Candle],
    config: MeanReversionConfig | None = None,
    *,
    trade_start_time_ms: int | None = None,
) -> bt.BacktestResult:
    """Run a long-only causal z-score mean-reversion strategy with next-open execution."""
    cfg = config or MeanReversionConfig()
    bars = list(candles)
    if len(bars) < cfg.lookback + 2:
        raise ValueError("Not enough candles for mean-reversion backtest")

    evaluation_index = _first_evaluation_index(bars, cfg, trade_start_time_ms)
    evaluation_start_ms = bars[evaluation_index].open_time_ms
    evaluation_bars = bars[evaluation_index:]
    entries, exits, _ = mean_reversion_signals(bars, cfg)

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

    for index in range(cfg.lookback, len(bars) - 1):
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
