from __future__ import annotations

import math
from collections.abc import Iterable
from dataclasses import dataclass
from statistics import mean

from . import backtest as bt
from .history import Candle


@dataclass(frozen=True, slots=True)
class AtrTrailingConfig:
    atr_period: int = 14
    atr_multiplier: float = 2.5
    initial_cash: float = 10_000.0
    fee_bps: float = 4.0
    slippage_bps: float = 1.5

    def __post_init__(self) -> None:
        if self.atr_period < 2:
            raise ValueError("atr_period must be >= 2")
        if not math.isfinite(self.atr_multiplier) or self.atr_multiplier <= 0.0:
            raise ValueError("atr_multiplier must be positive and finite")
        if not math.isfinite(self.initial_cash) or self.initial_cash <= 0.0:
            raise ValueError("initial_cash must be positive and finite")
        for name, value in (("fee_bps", self.fee_bps), ("slippage_bps", self.slippage_bps)):
            if not math.isfinite(value) or value < 0.0:
                raise ValueError(f"{name} must be non-negative and finite")


def true_ranges(candles: Iterable[Candle]) -> list[float]:
    bars = list(candles)
    if not bars:
        return []
    result = [bars[0].high - bars[0].low]
    for previous, current in zip(bars, bars[1:], strict=False):
        result.append(
            max(
                current.high - current.low,
                abs(current.high - previous.close),
                abs(current.low - previous.close),
            )
        )
    return result


def wilder_atr(candles: Iterable[Candle], period: int) -> list[float | None]:
    bars = list(candles)
    if period < 2:
        raise ValueError("period must be >= 2")
    values: list[float | None] = [None] * len(bars)
    if len(bars) < period:
        return values
    ranges = true_ranges(bars)
    current = mean(ranges[:period])
    values[period - 1] = current
    for index in range(period, len(bars)):
        current = ((current * (period - 1)) + ranges[index]) / period
        values[index] = current
    return values


def atr_trailing_regime(
    candles: Iterable[Candle],
    config: AtrTrailingConfig | None = None,
) -> tuple[tuple[float | None, ...], tuple[int, ...]]:
    """Return causal ATR stop values and {-1, 0, +1} regimes.

    Every value at index ``i`` uses candles no later than ``i``. The initial regime is neutral.
    A later close above the prior stop establishes a long regime; a close below establishes a
    defensive/short regime. EBA Trader's first ATR implementation trades only the long regime.
    """
    cfg = config or AtrTrailingConfig()
    bars = list(candles)
    atr_values = wilder_atr(bars, cfg.atr_period)
    stops: list[float | None] = [None] * len(bars)
    regimes = [0] * len(bars)
    if len(bars) < cfg.atr_period:
        return tuple(stops), tuple(regimes)

    seed = cfg.atr_period - 1
    if atr_values[seed] is None:
        raise RuntimeError("ATR seed is unexpectedly unavailable")
    stops[seed] = bars[seed].close

    for index in range(seed + 1, len(bars)):
        atr_value = atr_values[index]
        previous_stop = stops[index - 1]
        if atr_value is None or previous_stop is None:
            raise RuntimeError("ATR trailing state is unexpectedly unavailable")
        close = bars[index].close
        loss = cfg.atr_multiplier * atr_value
        previous_regime = regimes[index - 1]

        if close > previous_stop:
            candidate = close - loss
            stops[index] = max(previous_stop, candidate) if previous_regime >= 0 else candidate
            regimes[index] = 1
        elif close < previous_stop:
            candidate = close + loss
            stops[index] = min(previous_stop, candidate) if previous_regime <= 0 else candidate
            regimes[index] = -1
        else:
            stops[index] = previous_stop
            regimes[index] = previous_regime

    return tuple(stops), tuple(regimes)


def _first_evaluation_index(
    bars: list[Candle],
    config: AtrTrailingConfig,
    trade_start_time_ms: int | None,
) -> int:
    minimum = config.atr_period + 1
    if minimum >= len(bars):
        raise ValueError("Not enough candles for ATR trailing backtest")
    if trade_start_time_ms is None:
        return minimum
    for index in range(minimum, len(bars)):
        if bars[index].open_time_ms >= trade_start_time_ms:
            return index
    raise ValueError("trade_start_time_ms is after the available candles")


def run_atr_trailing_backtest(
    candles: Iterable[Candle],
    config: AtrTrailingConfig | None = None,
    *,
    trade_start_time_ms: int | None = None,
) -> bt.BacktestResult:
    """Run a long-only causal ATR trailing-stop regime strategy.

    The regime is calculated from completed candles. Regime flips execute at the next candle
    open, so the entry/exit decision never consumes that execution candle's high/low/close.
    Trading and benchmark accounting begin at one common evaluation timestamp while earlier
    candles remain available only for causal indicator warm-up.
    """
    cfg = config or AtrTrailingConfig()
    bars = list(candles)
    if len(bars) < cfg.atr_period + 2:
        raise ValueError("Not enough candles for ATR trailing backtest")

    evaluation_index = _first_evaluation_index(bars, cfg, trade_start_time_ms)
    evaluation_start_ms = bars[evaluation_index].open_time_ms
    evaluation_bars = bars[evaluation_index:]
    _, regimes = atr_trailing_regime(bars, cfg)

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

    for index in range(cfg.atr_period, len(bars) - 1):
        previous_regime = regimes[index - 1]
        regime = regimes[index]
        flip_long = previous_regime <= 0 and regime == 1
        flip_flat = previous_regime == 1 and regime <= 0
        next_bar = bars[index + 1]
        evaluation_active = next_bar.open_time_ms >= evaluation_start_ms

        if evaluation_active:
            if flip_long and quantity == 0.0:
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
            elif flip_flat and quantity > 0.0:
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
