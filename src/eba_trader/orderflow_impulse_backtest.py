from __future__ import annotations

import math
from collections.abc import Iterable
from dataclasses import dataclass
from statistics import mean

from . import backtest as bt
from .orderflow_feature_dataset import OrderFlowFeatureRow


@dataclass(frozen=True, slots=True)
class OrderFlowDeltaImpulseConfig:
    side: int = 1
    entry_delta_ratio: float = 0.2
    exit_delta_ratio: float = 0.0
    initial_cash: float = 10_000.0
    fee_bps: float = 4.0
    slippage_bps: float = 1.5

    def __post_init__(self) -> None:
        if self.side not in (-1, 1):
            raise ValueError("side must be +1 (long) or -1 (short)")
        if not math.isfinite(self.entry_delta_ratio) or not 0.0 < self.entry_delta_ratio <= 1.0:
            raise ValueError("entry_delta_ratio must be finite in (0, 1]")
        if not math.isfinite(self.exit_delta_ratio) or not 0.0 <= self.exit_delta_ratio <= 1.0:
            raise ValueError("exit_delta_ratio must be finite in [0, 1]")
        if self.exit_delta_ratio >= self.entry_delta_ratio:
            raise ValueError("exit_delta_ratio must be smaller than entry_delta_ratio")
        if not math.isfinite(self.initial_cash) or self.initial_cash <= 0.0:
            raise ValueError("initial_cash must be positive and finite")
        for name, value in (("fee_bps", self.fee_bps), ("slippage_bps", self.slippage_bps)):
            if not math.isfinite(value) or value < 0.0:
                raise ValueError(f"{name} must be non-negative and finite")


def _validated_rows(rows: Iterable[OrderFlowFeatureRow]) -> list[OrderFlowFeatureRow]:
    data = list(rows)
    if len(data) < 2:
        raise ValueError("Not enough order-flow feature rows")
    previous_open: int | None = None
    for row in data:
        open_time = row.candle.open_time_ms
        if row.footprint_available_at_ms > open_time:
            raise ValueError("order-flow feature is not available by candle open")
        if previous_open is not None and open_time <= previous_open:
            raise ValueError("order-flow feature rows must be strictly chronological")
        if not math.isfinite(row.of_delta_ratio) or not -1.0 <= row.of_delta_ratio <= 1.0:
            raise ValueError("order-flow delta ratio must be finite in [-1, 1]")
        previous_open = open_time
    return data


def orderflow_delta_signals(
    rows: Iterable[OrderFlowFeatureRow],
    config: OrderFlowDeltaImpulseConfig | None = None,
) -> tuple[tuple[bool, ...], tuple[bool, ...], tuple[float, ...]]:
    """Return causal entry/exit signals from already-closed footprint delta.

    Each feature row contains order flow from the footprint that closed at or before the
    attached candle open. The signal uses only ``of_delta_ratio``; price high/low/close from
    the attached candle never participates. Execution is intentionally deferred one full bar
    to the next candle open even though the footprint is already available, which keeps the
    research contract conservative with respect to feed and processing latency.
    """

    cfg = config or OrderFlowDeltaImpulseConfig()
    data = _validated_rows(rows)
    entries: list[bool] = []
    exits: list[bool] = []
    signed_scores: list[float] = []
    for row in data:
        score = float(cfg.side) * row.of_delta_ratio
        signed_scores.append(score)
        entries.append(score >= cfg.entry_delta_ratio)
        exits.append(score <= -cfg.exit_delta_ratio)
    return tuple(entries), tuple(exits), tuple(signed_scores)


def _first_evaluation_index(
    rows: list[OrderFlowFeatureRow],
    trade_start_time_ms: int | None,
) -> int:
    minimum = 1
    if trade_start_time_ms is None:
        return minimum
    for index in range(minimum, len(rows)):
        if rows[index].candle.open_time_ms >= trade_start_time_ms:
            return index
    raise ValueError("trade_start_time_ms is after the available feature rows")


def _marked_equity(
    *,
    basis: float,
    quantity: float,
    side: int,
    entry_price: float,
    mark_price: float,
) -> float:
    return basis + float(side) * quantity * (mark_price - entry_price)


def run_orderflow_delta_impulse_backtest(
    rows: Iterable[OrderFlowFeatureRow],
    config: OrderFlowDeltaImpulseConfig | None = None,
    *,
    trade_start_time_ms: int | None = None,
) -> bt.BacktestResult:
    """Run a causal 1x long or short order-flow impulse strategy.

    A footprint delta signal on feature row ``i`` can only execute at candle ``i+1`` open.
    Fees and adverse slippage are applied on both entry and exit. Short positions use a
    linear 1x futures-style mark-to-market model without leverage or compounding notional.
    """

    cfg = config or OrderFlowDeltaImpulseConfig()
    data = _validated_rows(rows)
    entries, exits, _ = orderflow_delta_signals(data, cfg)
    evaluation_index = _first_evaluation_index(data, trade_start_time_ms)
    evaluation_start_ms = data[evaluation_index].candle.open_time_ms
    evaluation_bars = [row.candle for row in data[evaluation_index:]]

    fee_rate = cfg.fee_bps / 10_000.0
    slippage_rate = cfg.slippage_bps / 10_000.0
    cash = cfg.initial_cash
    quantity = 0.0
    position_basis = 0.0
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

    for index in range(0, len(data) - 1):
        next_bar = data[index + 1].candle
        if next_bar.open_time_ms < evaluation_start_ms:
            continue

        if entries[index] and quantity == 0.0 and cash > 0.0:
            entry_equity = cash
            entry_price = next_bar.open * (1.0 + float(cfg.side) * slippage_rate)
            entry_fee = cash * fee_rate
            entry_slippage = cash * slippage_rate
            total_cost += entry_fee + entry_slippage
            position_basis = cash - entry_fee
            quantity = position_basis / entry_price
            entry_time_ms = next_bar.open_time_ms
            cash = 0.0
        elif exits[index] and quantity > 0.0:
            exit_price = next_bar.open * (1.0 - float(cfg.side) * slippage_rate)
            gross_equity = _marked_equity(
                basis=position_basis,
                quantity=quantity,
                side=cfg.side,
                entry_price=entry_price,
                mark_price=exit_price,
            )
            exit_notional = quantity * exit_price
            exit_fee = exit_notional * fee_rate
            exit_slippage = exit_notional * slippage_rate
            total_cost += exit_fee + exit_slippage
            cash = max(gross_equity - exit_fee, 0.0)
            trades.append(
                bt.ClosedTrade(
                    entry_time_ms=entry_time_ms,
                    exit_time_ms=next_bar.open_time_ms,
                    entry_price=entry_price,
                    exit_price=exit_price,
                    net_return=cash / entry_equity - 1.0,
                    pnl=cash - entry_equity,
                )
            )
            quantity = 0.0
            position_basis = 0.0

        if quantity > 0.0:
            mark_equity = max(
                _marked_equity(
                    basis=position_basis,
                    quantity=quantity,
                    side=cfg.side,
                    entry_price=entry_price,
                    mark_price=next_bar.close,
                ),
                0.0,
            )
            exposed_bars += 1
        else:
            mark_equity = cash
        if previous_equity > 0.0:
            bar_returns.append(mark_equity / previous_equity - 1.0)
        previous_equity = mark_equity
        equity_curve.append(mark_equity)
        evaluated_bars += 1

    if quantity > 0.0:
        final_bar = data[-1].candle
        exit_price = final_bar.close * (1.0 - float(cfg.side) * slippage_rate)
        gross_equity = _marked_equity(
            basis=position_basis,
            quantity=quantity,
            side=cfg.side,
            entry_price=entry_price,
            mark_price=exit_price,
        )
        exit_notional = quantity * exit_price
        exit_fee = exit_notional * fee_rate
        exit_slippage = exit_notional * slippage_rate
        total_cost += exit_fee + exit_slippage
        cash = max(gross_equity - exit_fee, 0.0)
        trades.append(
            bt.ClosedTrade(
                entry_time_ms=entry_time_ms,
                exit_time_ms=final_bar.close_time_ms,
                entry_price=entry_price,
                exit_price=exit_price,
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
