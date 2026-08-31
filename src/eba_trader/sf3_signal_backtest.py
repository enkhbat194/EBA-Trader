from __future__ import annotations

import math
from collections.abc import Iterable
from dataclasses import dataclass
from statistics import mean, median

from . import backtest as bt
from .orderflow_feature_dataset import OrderFlowFeatureRow
from .sf3_protocol import (
    FEE_BPS,
    MAX_HOLD_BARS,
    MINIMUM_HOLD_BARS,
    SIGNAL_TO_EXECUTION_DELAY_BARS,
    SLIPPAGE_BPS,
    SF3Candidate,
)

INITIAL_CASH = 10_000.0


@dataclass(frozen=True, slots=True)
class SF3SignalObservation:
    entry: bool
    opposite: bool
    signed_strength: float


@dataclass(frozen=True, slots=True)
class SF3ExecutionConfig:
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
            raise ValueError("SF3 preregistration requires exactly one execution-delay bar")


def _validated_rows(rows: Iterable[OrderFlowFeatureRow]) -> list[OrderFlowFeatureRow]:
    data = list(rows)
    if len(data) < 3:
        raise ValueError("Not enough SF3 feature rows")
    previous_open: int | None = None
    for row in data:
        open_time = row.candle.open_time_ms
        if row.footprint_available_at_ms > open_time:
            raise ValueError("order-flow feature is not available by candle open")
        if previous_open is not None and open_time <= previous_open:
            raise ValueError("SF3 feature rows must be strictly chronological")
        values = (
            row.candle.open,
            row.candle.high,
            row.candle.low,
            row.candle.close,
            row.of_buy_volume,
            row.of_sell_volume,
            row.of_delta,
            row.of_delta_ratio,
        )
        if any(not math.isfinite(float(value)) for value in values):
            raise ValueError("SF3 prices and flow features must be finite")
        if row.candle.open <= 0.0 or row.candle.high <= 0.0 or row.candle.low <= 0.0:
            raise ValueError("SF3 candle prices must be positive")
        if row.candle.close <= 0.0:
            raise ValueError("SF3 candle prices must be positive")
        if row.of_buy_volume < 0.0 or row.of_sell_volume < 0.0:
            raise ValueError("SF3 executed volumes cannot be negative")
        if not -1.0 <= row.of_delta_ratio <= 1.0:
            raise ValueError("order-flow delta ratio must be in [-1, 1]")
        previous_open = open_time
    return data


def _side(candidate: SF3Candidate) -> int:
    raw = candidate.parameters.get("side")
    if isinstance(raw, bool) or not isinstance(raw, int) or raw not in (-1, 1):
        raise ValueError("SF3 candidate side must be +1 or -1")
    return raw


def _positive_float(candidate: SF3Candidate, key: str) -> float:
    raw = candidate.parameters.get(key)
    if isinstance(raw, bool) or not isinstance(raw, (int, float)):
        raise ValueError(f"SF3 candidate {key} must be numeric")
    value = float(raw)
    if not math.isfinite(value) or value <= 0.0:
        raise ValueError(f"SF3 candidate {key} must be positive and finite")
    return value


def _positive_int(candidate: SF3Candidate, key: str) -> int:
    raw = candidate.parameters.get(key)
    if isinstance(raw, bool) or not isinstance(raw, int) or raw < 1:
        raise ValueError(f"SF3 candidate {key} must be an integer >= 1")
    return raw


def _empty() -> SF3SignalObservation:
    return SF3SignalObservation(False, False, 0.0)


def _flow_ratio(rows: list[OrderFlowFeatureRow]) -> float:
    total_volume = sum(row.of_buy_volume + row.of_sell_volume for row in rows)
    if total_volume <= 0.0:
        return 0.0
    return sum(row.of_delta for row in rows) / total_volume


def _closed_price_return(
    data: list[OrderFlowFeatureRow],
    *,
    index: int,
    lookback: int,
) -> float | None:
    if index < lookback:
        return None
    closed = data[index - lookback : index]
    if len(closed) != lookback:
        return None
    start = closed[0].candle.open
    end = closed[-1].candle.close
    return end / start - 1.0


def _rolling_vwap(
    data: list[OrderFlowFeatureRow],
    *,
    index: int,
    lookback: int,
) -> float | None:
    if index < lookback:
        return None
    weighted = 0.0
    volume = 0.0
    # Flow row k+1 describes the executed volume of the already-closed price candle k.
    for price_index in range(index - lookback, index):
        flow_index = price_index + 1
        if flow_index >= len(data):
            return None
        candle = data[price_index].candle
        flow = data[flow_index]
        executed_volume = flow.of_buy_volume + flow.of_sell_volume
        weighted += candle.close * executed_volume
        volume += executed_volume
    if volume <= 0.0:
        return None
    return weighted / volume


def sf3_candidate_signals(
    rows: Iterable[OrderFlowFeatureRow],
    candidate: SF3Candidate,
) -> tuple[SF3SignalObservation, ...]:
    """Generate preregistered SF3 signals from information available at row open only.

    Order-flow row ``i`` contains flow that completed immediately before candle ``i``
    opened. Any price response used at row ``i`` therefore ends at candle ``i-1``.
    The still-forming high/low/close of candle ``i`` is never part of its own signal.
    Execution happens separately at candle ``i+1`` open.
    """

    data = _validated_rows(rows)
    side = _side(candidate)
    observations: list[SF3SignalObservation] = []

    for index, row in enumerate(data):
        if candidate.family == "rolling_flow_trend_v1":
            lookback = _positive_int(candidate, "lookback")
            minimum_flow = _positive_float(candidate, "minimum_flow_ratio")
            minimum_return = _positive_float(candidate, "minimum_price_return")
            price_return = _closed_price_return(data, index=index, lookback=lookback)
            if price_return is None or index + 1 < lookback:
                observation = _empty()
            else:
                flow_rows = data[index - lookback + 1 : index + 1]
                if len(flow_rows) != lookback:
                    observation = _empty()
                else:
                    flow_ratio = _flow_ratio(flow_rows)
                    directional_return = float(side) * price_return
                    directional_flow = float(side) * flow_ratio
                    entry = (
                        directional_return >= minimum_return
                        and directional_flow >= minimum_flow
                    )
                    opposite = (
                        directional_return <= -minimum_return
                        and directional_flow <= -minimum_flow
                    )
                    strength = min(
                        directional_return / minimum_return,
                        directional_flow / minimum_flow,
                    )
                    observation = SF3SignalObservation(
                        entry,
                        opposite,
                        max(-4.0, min(4.0, strength)),
                    )
        elif candidate.family == "volume_shock_momentum_v1":
            lookback = _positive_int(candidate, "lookback")
            multiple = _positive_float(candidate, "volume_multiple")
            minimum_return = _positive_float(candidate, "minimum_price_return")
            if index < lookback or index == 0:
                observation = _empty()
            else:
                prior_volumes = [
                    item.of_buy_volume + item.of_sell_volume
                    for item in data[index - lookback : index]
                ]
                reference_volume = median(prior_volumes)
                current_volume = row.of_buy_volume + row.of_sell_volume
                closed = data[index - 1].candle
                price_return = closed.close / closed.open - 1.0
                directional_return = float(side) * price_return
                shock = reference_volume > 0.0 and current_volume >= reference_volume * multiple
                entry = shock and directional_return >= minimum_return
                opposite = shock and directional_return <= -minimum_return
                volume_strength = (
                    current_volume / max(reference_volume * multiple, 1e-12)
                    if reference_volume > 0.0
                    else 0.0
                )
                return_strength = directional_return / minimum_return
                observation = SF3SignalObservation(
                    entry,
                    opposite,
                    max(-4.0, min(4.0, min(volume_strength, return_strength))),
                )
        elif candidate.family == "vwap_reversion_flow_v1":
            lookback = _positive_int(candidate, "lookback")
            deviation_threshold = _positive_float(candidate, "entry_deviation_bps")
            reversal_delta = _positive_float(candidate, "minimum_reversal_delta_ratio")
            vwap = _rolling_vwap(data, index=index, lookback=lookback)
            if vwap is None or index == 0:
                observation = _empty()
            else:
                closed_price = data[index - 1].candle.close
                deviation_bps = (closed_price / vwap - 1.0) * 10_000.0
                extreme_against_side = -float(side) * deviation_bps
                directional_flow = float(side) * row.of_delta_ratio
                entry = (
                    extreme_against_side >= deviation_threshold
                    and directional_flow >= reversal_delta
                )
                reverted_through_vwap = float(side) * deviation_bps >= 0.0
                flow_reversed = directional_flow <= -reversal_delta
                opposite = reverted_through_vwap or flow_reversed
                strength = min(
                    extreme_against_side / deviation_threshold,
                    directional_flow / reversal_delta,
                )
                observation = SF3SignalObservation(
                    entry,
                    opposite,
                    max(-4.0, min(4.0, strength)),
                )
        elif candidate.family == "compression_expansion_v1":
            short_lookback = _positive_int(candidate, "short_lookback")
            long_lookback = _positive_int(candidate, "long_lookback")
            compression_max = _positive_float(candidate, "compression_ratio_max")
            minimum_return = _positive_float(candidate, "minimum_price_return")
            if short_lookback >= long_lookback:
                raise ValueError("SF3 compression short lookback must be below long lookback")
            if index < long_lookback + 1:
                observation = _empty()
            else:
                compression_candles = data[index - long_lookback - 1 : index - 1]
                normalized_ranges = [
                    (item.candle.high - item.candle.low) / item.candle.open
                    for item in compression_candles
                ]
                long_range = mean(normalized_ranges)
                short_range = mean(normalized_ranges[-short_lookback:])
                compression_ratio = short_range / long_range if long_range > 0.0 else math.inf
                expansion = data[index - 1].candle
                price_return = expansion.close / expansion.open - 1.0
                directional_return = float(side) * price_return
                compressed = compression_ratio <= compression_max
                entry = compressed and directional_return >= minimum_return
                opposite = directional_return <= -minimum_return
                compression_strength = (
                    compression_max / max(compression_ratio, 1e-12)
                    if math.isfinite(compression_ratio)
                    else 0.0
                )
                return_strength = directional_return / minimum_return
                observation = SF3SignalObservation(
                    entry,
                    opposite,
                    max(-4.0, min(4.0, min(compression_strength, return_strength))),
                )
        else:
            raise ValueError(f"unsupported SF3 family: {candidate.family}")
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
    raise ValueError("trade_start_time_ms is after the available SF3 rows")


def _marked_equity(
    *,
    basis: float,
    quantity: float,
    side: int,
    entry_price: float,
    mark_price: float,
) -> float:
    return basis + float(side) * quantity * (mark_price - entry_price)


def run_sf3_candidate_backtest(
    rows: Iterable[OrderFlowFeatureRow],
    candidate: SF3Candidate,
    *,
    trade_start_time_ms: int | None = None,
    execution: SF3ExecutionConfig | None = None,
) -> bt.BacktestResult:
    """Backtest one preregistered one-sided SF3 candidate with fixed slower holds."""

    data = _validated_rows(rows)
    side = _side(candidate)
    cfg = execution or SF3ExecutionConfig(side=side)
    if cfg.side != side:
        raise ValueError("execution side must match the preregistered candidate side")
    signals = sf3_candidate_signals(data, candidate)
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
                raise RuntimeError("SF3 position lacks entry execution index")
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
