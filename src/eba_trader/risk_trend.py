from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import UTC, datetime
from statistics import mean
from typing import Iterable

from .backtest import (
    ClosedTrade,
    _annualized_return,
    _buy_and_hold_metrics,
    _infer_bars_per_year,
    _risk_adjusted_ratios,
    ema,
    max_drawdown,
)
from .history import Candle


@dataclass(frozen=True, slots=True)
class RiskTrendConfig:
    fast_ema: int = 20
    slow_ema: int = 50
    atr_period: int = 14
    atr_multiplier: float = 2.0
    risk_fraction: float = 0.005
    daily_loss_limit: float = 0.02
    max_drawdown_halt: float = 0.08
    initial_cash: float = 1000.0
    fee_bps: float = 10.0
    slippage_bps: float = 5.0

    def __post_init__(self) -> None:
        if self.fast_ema <= 1 or self.slow_ema <= self.fast_ema:
            raise ValueError("Require 1 < fast_ema < slow_ema")
        if self.atr_period <= 1:
            raise ValueError("atr_period must be > 1")
        if self.atr_multiplier <= 0:
            raise ValueError("atr_multiplier must be positive")
        if not 0 < self.risk_fraction <= 0.02:
            raise ValueError("risk_fraction must be in (0, 0.02]")
        if not 0 < self.daily_loss_limit < 1:
            raise ValueError("daily_loss_limit must be in (0, 1)")
        if not 0 < self.max_drawdown_halt < 1:
            raise ValueError("max_drawdown_halt must be in (0, 1)")
        if self.initial_cash <= 0:
            raise ValueError("initial_cash must be positive")
        if min(self.fee_bps, self.slippage_bps) < 0:
            raise ValueError("cost assumptions cannot be negative")


@dataclass(frozen=True, slots=True)
class RiskSizedTrade:
    trade: ClosedTrade
    quantity: float
    stop_price: float
    planned_risk_usd: float
    planned_risk_fraction: float
    exit_reason: str


@dataclass(frozen=True, slots=True)
class RiskTrendResult:
    initial_cash: float
    final_equity: float
    total_return: float
    annualized_return: float
    benchmark_return: float
    benchmark_max_drawdown: float
    benchmark_relative_return: float
    max_drawdown: float
    trade_count: int
    win_rate: float
    profit_factor: float
    expectancy: float
    average_win: float
    average_loss: float
    sharpe: float
    sortino: float
    time_exposure: float
    average_notional_fraction: float
    total_cost: float
    stop_out_count: int
    daily_halt_count: int
    max_drawdown_halted: bool
    trades: tuple[RiskSizedTrade, ...]


def atr(candles: Iterable[Candle], period: int = 14) -> list[float | None]:
    bars = list(candles)
    if period <= 1:
        raise ValueError("period must be > 1")
    result: list[float | None] = [None] * len(bars)
    if len(bars) < period:
        return result

    true_ranges: list[float] = []
    for index, bar in enumerate(bars):
        if index == 0:
            true_range = bar.high - bar.low
        else:
            previous_close = bars[index - 1].close
            true_range = max(
                bar.high - bar.low,
                abs(bar.high - previous_close),
                abs(bar.low - previous_close),
            )
        true_ranges.append(true_range)

    seed = mean(true_ranges[:period])
    result[period - 1] = seed
    current = seed
    for index in range(period, len(bars)):
        current = ((period - 1) * current + true_ranges[index]) / period
        result[index] = current
    return result


def _profit_factor(values: list[float]) -> float:
    gross_profit = sum(max(value, 0.0) for value in values)
    gross_loss = -sum(min(value, 0.0) for value in values)
    if gross_loss == 0:
        return math.inf if gross_profit > 0 else 0.0
    return gross_profit / gross_loss


def _utc_day(timestamp_ms: int):
    return datetime.fromtimestamp(timestamp_ms / 1000.0, tz=UTC).date()


def _sell_execution_price(raw_price: float, slippage_bps: float) -> float:
    return raw_price * (1.0 - slippage_bps / 10_000.0)


def _entry_quantity(
    *,
    cash: float,
    equity: float,
    entry_price: float,
    stop_price: float,
    fee_bps: float,
    slippage_bps: float,
    risk_fraction: float,
) -> tuple[float, float]:
    fee_rate = fee_bps / 10_000.0
    anticipated_stop_execution = _sell_execution_price(stop_price, slippage_bps)
    loss_per_unit = entry_price * (1.0 + fee_rate) - anticipated_stop_execution * (
        1.0 - fee_rate
    )
    if loss_per_unit <= 0:
        raise RuntimeError("Calculated stop risk per unit is not positive")

    risk_budget = equity * risk_fraction
    risk_quantity = risk_budget / loss_per_unit
    cash_quantity = cash / (entry_price * (1.0 + fee_rate))
    quantity = min(risk_quantity, cash_quantity)
    if quantity <= 0:
        return 0.0, 0.0
    planned_loss = quantity * loss_per_unit
    return quantity, planned_loss


def run_risk_sized_trend_backtest(
    candles: Iterable[Candle],
    config: RiskTrendConfig | None = None,
) -> RiskTrendResult:
    cfg = config or RiskTrendConfig()
    bars = list(candles)
    warmup = max(cfg.slow_ema, cfg.atr_period)
    if len(bars) < warmup + 2:
        raise ValueError("Not enough candles for risk-sized Trend backtest")

    closes = [bar.close for bar in bars]
    fast = ema(closes, cfg.fast_ema)
    slow = ema(closes, cfg.slow_ema)
    atr_values = atr(bars, cfg.atr_period)

    seed_index = cfg.slow_ema - 1
    seed_fast = fast[seed_index]
    seed_slow = slow[seed_index]
    if seed_fast is None or seed_slow is None:
        raise RuntimeError("EMA warm-up state is unavailable")
    previous_signal = seed_fast > seed_slow

    cash = cfg.initial_cash
    quantity = 0.0
    entry_price = 0.0
    entry_fee = 0.0
    entry_time_ms = 0
    stop_price = 0.0
    planned_risk_usd = 0.0
    planned_risk_fraction = 0.0
    total_cost = 0.0
    trades: list[RiskSizedTrade] = []
    equity_curve: list[float] = [cfg.initial_cash]
    returns: list[float] = []
    previous_equity = cfg.initial_cash
    peak_equity = cfg.initial_cash
    time_exposed_bars = 0
    notional_fraction_sum = 0.0
    evaluated_bars = 0
    stop_out_count = 0
    max_drawdown_halted = False

    current_day = None
    day_start_equity = cfg.initial_cash
    daily_halted = False
    daily_halt_days: set[object] = set()

    def close_position(raw_exit_price: float, timestamp_ms: int, reason: str) -> None:
        nonlocal cash, quantity, total_cost, stop_out_count
        if quantity <= 0:
            return
        exit_price = _sell_execution_price(raw_exit_price, cfg.slippage_bps)
        gross = quantity * exit_price
        exit_fee = gross * cfg.fee_bps / 10_000.0
        exit_slippage = quantity * max(raw_exit_price - exit_price, 0.0)
        total_cost += exit_fee + exit_slippage
        exit_net = gross - exit_fee
        entry_outflow = quantity * entry_price + entry_fee
        pnl = exit_net - entry_outflow
        cash += exit_net
        trades.append(
            RiskSizedTrade(
                trade=ClosedTrade(
                    entry_time_ms=entry_time_ms,
                    exit_time_ms=timestamp_ms,
                    entry_price=entry_price,
                    exit_price=exit_price,
                    net_return=pnl / entry_outflow if entry_outflow > 0 else 0.0,
                    pnl=pnl,
                ),
                quantity=quantity,
                stop_price=stop_price,
                planned_risk_usd=planned_risk_usd,
                planned_risk_fraction=planned_risk_fraction,
                exit_reason=reason,
            )
        )
        if reason == "stop":
            stop_out_count += 1
        quantity = 0.0

    for index in range(warmup, len(bars) - 1):
        fast_value = fast[index]
        slow_value = slow[index]
        atr_value = atr_values[index]
        if fast_value is None or slow_value is None or atr_value is None:
            continue

        signal = fast_value > slow_value
        crossed_up = not previous_signal and signal
        crossed_down = previous_signal and not signal
        next_bar = bars[index + 1]

        day = _utc_day(next_bar.open_time_ms)
        if day != current_day:
            current_day = day
            day_start_equity = previous_equity
            daily_halted = False

        if quantity > 0.0 and crossed_down:
            close_position(next_bar.open, next_bar.open_time_ms, "ema_exit")

        current_equity_at_open = cash + quantity * next_bar.open
        peak_equity = max(peak_equity, current_equity_at_open)
        current_drawdown = current_equity_at_open / peak_equity - 1.0
        if current_drawdown <= -cfg.max_drawdown_halt:
            max_drawdown_halted = True

        if day_start_equity > 0:
            day_return_at_open = current_equity_at_open / day_start_equity - 1.0
            if day_return_at_open <= -cfg.daily_loss_limit:
                daily_halted = True
                daily_halt_days.add(day)

        if (
            quantity == 0.0
            and crossed_up
            and not daily_halted
            and not max_drawdown_halted
        ):
            raw_entry = next_bar.open
            execution_entry = raw_entry * (1.0 + cfg.slippage_bps / 10_000.0)
            candidate_stop = execution_entry - cfg.atr_multiplier * atr_value
            if candidate_stop > 0:
                entry_qty, planned_loss = _entry_quantity(
                    cash=cash,
                    equity=current_equity_at_open,
                    entry_price=execution_entry,
                    stop_price=candidate_stop,
                    fee_bps=cfg.fee_bps,
                    slippage_bps=cfg.slippage_bps,
                    risk_fraction=cfg.risk_fraction,
                )
                if entry_qty > 0:
                    fee = entry_qty * execution_entry * cfg.fee_bps / 10_000.0
                    entry_slippage = entry_qty * max(execution_entry - raw_entry, 0.0)
                    required_cash = entry_qty * execution_entry + fee
                    if required_cash > cash + 1e-9:
                        raise RuntimeError("Spot position sizing exceeded available cash")
                    cash -= required_cash
                    total_cost += fee + entry_slippage
                    quantity = entry_qty
                    entry_price = execution_entry
                    entry_fee = fee
                    entry_time_ms = next_bar.open_time_ms
                    stop_price = candidate_stop
                    planned_risk_usd = planned_loss
                    planned_risk_fraction = (
                        planned_loss / current_equity_at_open
                        if current_equity_at_open > 0
                        else 0.0
                    )

        if quantity > 0.0:
            if next_bar.open <= stop_price:
                close_position(next_bar.open, next_bar.open_time_ms, "stop")
            elif next_bar.low <= stop_price:
                close_position(stop_price, next_bar.close_time_ms, "stop")

        mark_equity = cash + quantity * next_bar.close
        if quantity > 0.0:
            time_exposed_bars += 1
            notional_fraction_sum += (
                quantity * next_bar.close / mark_equity if mark_equity > 0 else 0.0
            )
        evaluated_bars += 1
        if previous_equity > 0:
            returns.append(mark_equity / previous_equity - 1.0)
        previous_equity = mark_equity
        equity_curve.append(mark_equity)
        peak_equity = max(peak_equity, mark_equity)

        if peak_equity > 0 and mark_equity / peak_equity - 1.0 <= -cfg.max_drawdown_halt:
            max_drawdown_halted = True
        if day_start_equity > 0 and mark_equity / day_start_equity - 1.0 <= -cfg.daily_loss_limit:
            daily_halted = True
            daily_halt_days.add(day)

        previous_signal = signal

    if quantity > 0.0:
        final_bar = bars[-1]
        close_position(final_bar.close, final_bar.close_time_ms, "end_of_test")
        if previous_equity > 0:
            returns.append(cash / previous_equity - 1.0)
        equity_curve.append(cash)

    pnl_values = [item.trade.pnl for item in trades]
    wins = [value for value in pnl_values if value > 0]
    losses = [value for value in pnl_values if value < 0]
    final_equity = cash
    total_return = final_equity / cfg.initial_cash - 1.0
    evaluation_bars = bars[warmup + 1 :]
    benchmark_return, benchmark_drawdown = _buy_and_hold_metrics(
        evaluation_bars,
        type(
            "BenchmarkConfig",
            (),
            {
                "initial_cash": cfg.initial_cash,
                "fee_bps": cfg.fee_bps,
                "slippage_bps": cfg.slippage_bps,
            },
        )(),
    )
    bars_per_year = _infer_bars_per_year(evaluation_bars)
    sharpe, sortino = _risk_adjusted_ratios(returns, bars_per_year)

    return RiskTrendResult(
        initial_cash=cfg.initial_cash,
        final_equity=final_equity,
        total_return=total_return,
        annualized_return=_annualized_return(cfg.initial_cash, final_equity, evaluation_bars),
        benchmark_return=benchmark_return,
        benchmark_max_drawdown=benchmark_drawdown,
        benchmark_relative_return=total_return - benchmark_return,
        max_drawdown=max_drawdown(equity_curve),
        trade_count=len(trades),
        win_rate=len(wins) / len(trades) if trades else 0.0,
        profit_factor=_profit_factor(pnl_values),
        expectancy=mean(pnl_values) if pnl_values else 0.0,
        average_win=mean(wins) if wins else 0.0,
        average_loss=mean(losses) if losses else 0.0,
        sharpe=sharpe,
        sortino=sortino,
        time_exposure=time_exposed_bars / max(evaluated_bars, 1),
        average_notional_fraction=(
            notional_fraction_sum / time_exposed_bars if time_exposed_bars else 0.0
        ),
        total_cost=total_cost,
        stop_out_count=stop_out_count,
        daily_halt_count=len(daily_halt_days),
        max_drawdown_halted=max_drawdown_halted,
        trades=tuple(trades),
    )
