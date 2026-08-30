from __future__ import annotations

import math
from collections.abc import Iterable
from dataclasses import dataclass
from statistics import mean

from . import backtest as bt
from .orderflow_feature_dataset import OrderFlowFeatureRow
from .sf2_protocol import (
    FEE_BPS,
    MAX_HOLD_BARS,
    MINIMUM_HOLD_BARS,
    SIGNAL_TO_EXECUTION_DELAY_BARS,
    SLIPPAGE_BPS,
    SF2Candidate,
)

INITIAL_CASH = 10_000.0


@dataclass(frozen=True, slots=True)
class SF2SignalObservation:
    entry: bool
    opposite: bool
    signed_strength: float


@dataclass(frozen=True, slots=True)
class SF2ExecutionConfig:
    side: int
    initial_cash: float = INITIAL_CASH
    fee_bps: float = FEE_BPS
    slippage_bps: float = SLIPPAGE_BPS
    minimum_hold_bars: int = MINIMUM_HOLD_BARS
    max_hold_bars: int = MAX_HOLD_BARS
    signal_to_execution_delay_bars: int = SIGNAL_TO_EXECUTION_DELAY_BARS

    def __post_init__(self) -> None:
        if self.side not in (-1, 1):
            raise ValueError("side must be +1 or -1")
        if not math.isfinite(self.initial_cash) or self.initial_cash <= 0.0:
            raise ValueError("initial_cash must be positive and finite")
        for name, value in (("fee_bps", self.fee_bps), ("slippage_bps", self.slippage_bps)):
            if not math.isfinite(value) or value < 0.0:
                raise ValueError(f"{name} must be non-negative and finite")
        if self.minimum_hold_bars < 0:
            raise ValueError("minimum_hold_bars must be >= 0")
        if self.max_hold_bars < 1 or self.max_hold_bars < self.minimum_hold_bars:
            raise ValueError("max_hold_bars must be >= minimum_hold_bars and >= 1")
        if self.signal_to_execution_delay_bars != 1:
            raise ValueError("SF2 preregistration requires exactly one execution-delay bar")


def _validated_rows(rows: Iterable[OrderFlowFeatureRow]) -> list[OrderFlowFeatureRow]:
    data = list(rows)
    if len(data) < 3:
        raise ValueError("Not enough SF2 feature rows")
    previous_open: int | None = None
    for row in data:
        open_time = row.candle.open_time_ms
        if row.footprint_available_at_ms > open_time:
            raise ValueError("order-flow feature is not available by candle open")
        if previous_open is not None and open_time <= previous_open:
            raise ValueError("SF2 feature rows must be strictly chronological")
        finite_features = (
            row.of_delta_ratio,
            row.of_absorption,
            row.of_price_delta_divergence,
        )
        if any(not math.isfinite(float(value)) for value in finite_features):
            raise ValueError("SF2 signal features must be finite")
        if not -1.0 <= row.of_delta_ratio <= 1.0:
            raise ValueError("order-flow delta ratio must be in [-1, 1]")
        if not -1.0 <= row.of_absorption <= 1.0:
            raise ValueError("absorption score must be in [-1, 1]")
        if not -1.0 <= row.of_price_delta_divergence <= 1.0:
            raise ValueError("divergence score must be in [-1, 1]")
        if row.of_stacked_buy_levels < 0 or row.of_stacked_sell_levels < 0:
            raise ValueError("stacked imbalance levels cannot be negative")
        previous_open = open_time
    return data


def _side(candidate: SF2Candidate) -> int:
    raw = candidate.parameters.get("side")
    if isinstance(raw, bool) or not isinstance(raw, int) or raw not in (-1, 1):
        raise ValueError("SF2 candidate side must be +1 or -1")
    return raw


def _threshold(candidate: SF2Candidate, key: str) -> float:
    raw = candidate.parameters.get(key)
    if isinstance(raw, bool) or not isinstance(raw, (int, float)):
        raise ValueError(f"SF2 candidate {key} must be numeric")
    value = float(raw)
    if not math.isfinite(value) or value <= 0.0:
        raise ValueError(f"SF2 candidate {key} must be positive and finite")
    return value


def _directional_observation(
    raw_score: float,
    *,
    side: int,
    threshold: float,
) -> SF2SignalObservation:
    signed = float(side) * raw_score
    return SF2SignalObservation(
        entry=signed >= threshold,
        opposite=signed <= -threshold,
        signed_strength=signed,
    )


def sf2_candidate_signals(
    rows: Iterable[OrderFlowFeatureRow],
    candidate: SF2Candidate,
) -> tuple[SF2SignalObservation, ...]:
    """Generate preregistered SF2 signals using only information available at row open.

    The feature dataset aligns the footprint that closed immediately before candle ``i``
    with row ``i``. For the flow/price family, the matching already-closed price response
    is candle ``i-1``. The still-forming high/low/close of candle ``i`` is never used.
    Execution is handled separately and is delayed to candle ``i+1`` open.
    """

    data = _validated_rows(rows)
    side = _side(candidate)
    observations: list[SF2SignalObservation] = []

    for index, row in enumerate(data):
        if candidate.family == "divergence_reversal_v1":
            threshold = _threshold(candidate, "signal_threshold")
            observation = _directional_observation(
                row.of_price_delta_divergence,
                side=side,
                threshold=threshold,
            )
        elif candidate.family == "absorption_reversal_v1":
            threshold = _threshold(candidate, "signal_threshold")
            observation = _directional_observation(
                row.of_absorption,
                side=side,
                threshold=threshold,
            )
        elif candidate.family == "stacked_delta_continuation_v1":
            minimum_levels_raw = candidate.parameters.get("minimum_stacked_levels")
            if (
                isinstance(minimum_levels_raw, bool)
                or not isinstance(minimum_levels_raw, int)
                or minimum_levels_raw < 1
            ):
                raise ValueError("minimum_stacked_levels must be an integer >= 1")
            minimum_delta = _threshold(candidate, "minimum_delta_ratio")
            directional_delta = float(side) * row.of_delta_ratio
            directional_levels = (
                row.of_stacked_buy_levels if side > 0 else row.of_stacked_sell_levels
            )
            opposite_levels = (
                row.of_stacked_sell_levels if side > 0 else row.of_stacked_buy_levels
            )
            entry = directional_levels >= minimum_levels_raw and directional_delta >= minimum_delta
            opposite = opposite_levels >= minimum_levels_raw and directional_delta <= -minimum_delta
            level_strength = min(directional_levels / minimum_levels_raw, 2.0)
            observation = SF2SignalObservation(
                entry=entry,
                opposite=opposite,
                signed_strength=directional_delta * level_strength,
            )
        elif candidate.family == "flow_price_continuation_v1":
            minimum_delta = _threshold(candidate, "minimum_delta_ratio")
            minimum_price_return = _threshold(candidate, "minimum_price_return")
            if index == 0:
                observation = SF2SignalObservation(False, False, 0.0)
            else:
                closed = data[index - 1].candle
                price_return = closed.close / closed.open - 1.0
                directional_delta = float(side) * row.of_delta_ratio
                directional_return = float(side) * price_return
                entry = (
                    directional_delta >= minimum_delta
                    and directional_return >= minimum_price_return
                )
                opposite = (
                    directional_delta <= -minimum_delta
                    and directional_return <= -minimum_price_return
                )
                normalized_price = directional_return / minimum_price_return
                normalized_delta = directional_delta / minimum_delta
                strength = min(normalized_price, normalized_delta)
                observation = SF2SignalObservation(
                    entry=entry,
                    opposite=opposite,
                    signed_strength=max(-4.0, min(4.0, strength)),
                )
        else:
            raise ValueError(f"unsupported SF2 family: {candidate.family}")
        observations.append(observation)

    return tuple(observations)


def _first_evaluation_index(
    rows: list[OrderFlowFeatureRow],
    trade_start_time_ms: int | None,
) -> int:
    if trade_start_time_ms is None:
        return 1
    for index in range(1, len(rows)):
        if rows[index].candle.open_time_ms >= trade_start_time_ms:
            return index
    raise ValueError("trade_start_time_ms is after the available SF2 rows")


def _marked_equity(
    *,
    basis: float,
    quantity: float,
    side: int,
    entry_price: float,
    mark_price: float,
) -> float:
    return basis + float(side) * quantity * (mark_price - entry_price)


def run_sf2_candidate_backtest(
    rows: Iterable[OrderFlowFeatureRow],
    candidate: SF2Candidate,
    *,
    trade_start_time_ms: int | None = None,
    execution: SF2ExecutionConfig | None = None,
) -> bt.BacktestResult:
    """Backtest one preregistered one-sided SF2 candidate with fixed anti-churn holds."""

    data = _validated_rows(rows)
    side = _side(candidate)
    cfg = execution or SF2ExecutionConfig(side=side)
    if cfg.side != side:
        raise ValueError("execution side must match the preregistered candidate side")
    signals = sf2_candidate_signals(data, candidate)
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
    entry_execution_index: int | None = None
    total_cost = 0.0
    trades: list[bt.ClosedTrade] = []
    equity_curve = [cash]
    bar_returns: list[float] = []
    exposed_bars = 0
    evaluated_bars = 0
    previous_equity = cash

    # Signal row i executes one bar later at row i+1 open. This is intentionally more
    # conservative than executing at the same open where the closed footprint is available.
    for signal_index in range(0, len(data) - 1):
        execution_index = signal_index + 1
        next_bar = data[execution_index].candle
        if next_bar.open_time_ms < evaluation_start_ms:
            continue

        signal = signals[signal_index]
        if quantity == 0.0 and signal.entry and cash > 0.0:
            entry_equity = cash
            entry_price = next_bar.open * (1.0 + float(side) * slippage_rate)
            entry_fee = cash * fee_rate
            entry_slippage = cash * slippage_rate
            total_cost += entry_fee + entry_slippage
            position_basis = cash - entry_fee
            quantity = position_basis / entry_price
            entry_time_ms = next_bar.open_time_ms
            entry_execution_index = execution_index
            cash = 0.0
        elif quantity > 0.0:
            if entry_execution_index is None:
                raise RuntimeError("SF2 position lacks entry execution index")
            held_bars = execution_index - entry_execution_index
            can_signal_exit = held_bars >= cfg.minimum_hold_bars
            forced_max_hold = held_bars >= cfg.max_hold_bars
            if forced_max_hold or (can_signal_exit and signal.opposite):
                exit_price = next_bar.open * (1.0 - float(side) * slippage_rate)
                gross_equity = _marked_equity(
                    basis=position_basis,
                    quantity=quantity,
                    side=side,
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
                entry_execution_index = None

        if quantity > 0.0:
            mark_equity = max(
                _marked_equity(
                    basis=position_basis,
                    quantity=quantity,
                    side=side,
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
        exit_price = final_bar.close * (1.0 - float(side) * slippage_rate)
        gross_equity = _marked_equity(
            basis=position_basis,
            quantity=quantity,
            side=side,
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
