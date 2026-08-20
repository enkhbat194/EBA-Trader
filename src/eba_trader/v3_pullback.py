from __future__ import annotations

import math
from collections import defaultdict, deque
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import UTC, datetime
from statistics import mean, median

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
from .risk_trend import atr
from .v3_pullback_policy import BASELINE_V3_PULLBACK_CONFIG, V3PullbackConfig

FIFTEEN_MINUTES_MS = 15 * 60 * 1000
FOUR_HOURS_MS = 4 * 60 * 60 * 1000


@dataclass(frozen=True, slots=True)
class V3PullbackFeatures:
    bars: tuple[Candle, ...]
    four_hour_bars: tuple[Candle, ...]
    atr_15m: tuple[float | None, ...]
    prior_vwap_15m: tuple[float | None, ...]
    prior_median_volume_15m: tuple[float | None, ...]
    ema50_4h: tuple[float | None, ...]
    ema200_4h: tuple[float | None, ...]
    latest_4h_index: tuple[int | None, ...]
    invalid_4h_streak: tuple[int, ...]
    contiguous_15m_streak: tuple[int, ...]


@dataclass(frozen=True, slots=True)
class V3PullbackTrade:
    trade: ClosedTrade
    quantity: float
    initial_stop: float
    profit_target: float
    planned_risk_usd: float
    planned_risk_fraction: float
    entry_notional_fraction: float
    exit_reason: str
    entry_invariants_valid: bool


@dataclass(frozen=True, slots=True)
class V3PullbackResult:
    layer: str
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
    max_notional_fraction: float
    max_planned_risk_fraction: float
    total_cost: float
    stop_out_count: int
    target_exit_count: int
    time_exit_count: int
    regime_exit_count: int
    daily_halt_count: int
    max_drawdown_halted: bool
    entry_invariant_violations: int
    veto_entry_violations: int
    effective_start_ms: int
    effective_end_exclusive_ms: int
    trades: tuple[V3PullbackTrade, ...]


@dataclass(slots=True)
class _ArmState:
    arm_index: int
    pullback_low: float


@dataclass(frozen=True, slots=True)
class _SignalIntent:
    signal_index: int
    signal_close: float
    signal_atr: float
    raw_stop: float
    invariants_valid: bool


def resample_complete_4h(candles: Iterable[Candle]) -> tuple[Candle, ...]:
    bars = list(candles)
    grouped: dict[int, list[Candle]] = defaultdict(list)
    for bar in bars:
        four_hour_start = bar.open_time_ms - bar.open_time_ms % FOUR_HOURS_MS
        grouped[four_hour_start].append(bar)

    expected_offsets = tuple(index * FIFTEEN_MINUTES_MS for index in range(16))
    result: list[Candle] = []
    for four_hour_start in sorted(grouped):
        group = sorted(grouped[four_hour_start], key=lambda item: item.open_time_ms)
        offsets = tuple(item.open_time_ms - four_hour_start for item in group)
        if offsets != expected_offsets:
            continue
        result.append(
            Candle(
                open_time_ms=four_hour_start,
                open=group[0].open,
                high=max(item.high for item in group),
                low=min(item.low for item in group),
                close=group[-1].close,
                volume=sum(item.volume for item in group),
                close_time_ms=four_hour_start + FOUR_HOURS_MS - 1,
                quote_volume=sum(item.quote_volume for item in group),
                trade_count=sum(item.trade_count for item in group),
            )
        )
    return tuple(result)


def rolling_prior_vwap(
    candles: Iterable[Candle],
    window: int,
) -> tuple[float | None, ...]:
    if window <= 0:
        raise ValueError("window must be positive")
    bars = list(candles)
    result: list[float | None] = [None] * len(bars)
    weighted_window: deque[float] = deque()
    volume_window: deque[float] = deque()
    weighted_sum = 0.0
    volume_sum = 0.0

    for index, bar in enumerate(bars):
        if len(weighted_window) == window and volume_sum > 0:
            result[index] = weighted_sum / volume_sum

        typical = (bar.high + bar.low + bar.close) / 3.0
        weighted = typical * bar.volume
        weighted_window.append(weighted)
        volume_window.append(bar.volume)
        weighted_sum += weighted
        volume_sum += bar.volume

        if len(weighted_window) > window:
            weighted_sum -= weighted_window.popleft()
            volume_sum -= volume_window.popleft()

    return tuple(result)


def rolling_prior_median_volume(
    candles: Iterable[Candle],
    window: int,
) -> tuple[float | None, ...]:
    if window <= 0:
        raise ValueError("window must be positive")
    bars = list(candles)
    result: list[float | None] = [None] * len(bars)
    for index in range(window, len(bars)):
        result[index] = median(item.volume for item in bars[index - window : index])
    return tuple(result)


def _contiguous_streak(bars: list[Candle], step_ms: int) -> tuple[int, ...]:
    if not bars:
        return ()
    result = [1]
    for index in range(1, len(bars)):
        if bars[index].open_time_ms - bars[index - 1].open_time_ms == step_ms:
            result.append(result[-1] + 1)
        else:
            result.append(1)
    return tuple(result)


def prepare_v3_pullback_features(
    candles: Iterable[Candle],
    config: V3PullbackConfig | None = None,
) -> V3PullbackFeatures:
    cfg = config or BASELINE_V3_PULLBACK_CONFIG
    bars = list(candles)
    if not bars:
        raise ValueError("V3 pullback requires candles")
    four_hour_bars = list(resample_complete_4h(bars))

    atr_15m = tuple(atr(bars, cfg.atr_period))
    prior_vwap = rolling_prior_vwap(bars, cfg.rolling_vwap_bars)
    prior_median_volume = rolling_prior_median_volume(bars, cfg.rolling_vwap_bars)

    closes_4h = [bar.close for bar in four_hour_bars]
    ema50_4h = tuple(ema(closes_4h, cfg.regime_fast_ema_4h))
    ema200_4h = tuple(ema(closes_4h, cfg.regime_slow_ema_4h))

    latest_4h_index: list[int | None] = []
    cursor = -1
    for bar in bars:
        while (
            cursor + 1 < len(four_hour_bars)
            and four_hour_bars[cursor + 1].close_time_ms <= bar.close_time_ms
        ):
            cursor += 1
        latest_4h_index.append(cursor if cursor >= 0 else None)

    invalid_4h_streak: list[int] = []
    for index, bar in enumerate(four_hour_bars):
        fast = ema50_4h[index]
        slow = ema200_4h[index]
        old_index = index - cfg.regime_slope_lookback_4h
        old_slow = ema200_4h[old_index] if old_index >= 0 else None
        ready = fast is not None and slow is not None and old_slow is not None
        valid = ready and bar.close > slow and fast > slow and slow > old_slow
        contiguous = (
            index > 0
            and bar.open_time_ms - four_hour_bars[index - 1].open_time_ms == FOUR_HOURS_MS
        )
        previous = invalid_4h_streak[-1] if contiguous and invalid_4h_streak else 0
        invalid_4h_streak.append(0 if valid else previous + 1)

    return V3PullbackFeatures(
        bars=tuple(bars),
        four_hour_bars=tuple(four_hour_bars),
        atr_15m=atr_15m,
        prior_vwap_15m=prior_vwap,
        prior_median_volume_15m=prior_median_volume,
        ema50_4h=ema50_4h,
        ema200_4h=ema200_4h,
        latest_4h_index=tuple(latest_4h_index),
        invalid_4h_streak=tuple(invalid_4h_streak),
        contiguous_15m_streak=_contiguous_streak(bars, FIFTEEN_MINUTES_MS),
    )


def _features_ready(
    features: V3PullbackFeatures,
    index: int,
    cfg: V3PullbackConfig,
) -> bool:
    if index < max(cfg.rolling_vwap_bars, cfg.recovery_high_lookback):
        return False
    hour_index = features.latest_4h_index[index]
    if hour_index is None or hour_index < cfg.regime_slope_lookback_4h:
        return False
    old_index = hour_index - cfg.regime_slope_lookback_4h
    values = (
        features.atr_15m[index],
        features.prior_vwap_15m[index],
        features.prior_median_volume_15m[index],
        features.ema50_4h[hour_index],
        features.ema200_4h[hour_index],
        features.ema200_4h[old_index],
    )
    return all(value is not None for value in values)


def _source_ready(
    features: V3PullbackFeatures,
    index: int,
    cfg: V3PullbackConfig,
) -> bool:
    return (
        _features_ready(features, index, cfg)
        and features.contiguous_15m_streak[index] >= cfg.complete_15m_after_gap
    )


def _bull_regime(
    features: V3PullbackFeatures,
    index: int,
    cfg: V3PullbackConfig,
) -> bool:
    if not _features_ready(features, index, cfg):
        return False
    hour_index = features.latest_4h_index[index]
    if hour_index is None:
        return False
    old_index = hour_index - cfg.regime_slope_lookback_4h
    bar = features.four_hour_bars[hour_index]
    fast = features.ema50_4h[hour_index]
    slow = features.ema200_4h[hour_index]
    old_slow = features.ema200_4h[old_index]
    return bar.close > slow and fast > slow and slow > old_slow


def _arm_eligible(
    features: V3PullbackFeatures,
    index: int,
    cfg: V3PullbackConfig,
    *,
    filters_enabled: bool,
) -> bool:
    if not _source_ready(features, index, cfg) or not _bull_regime(features, index, cfg):
        return False

    bar = features.bars[index]
    atr_value = features.atr_15m[index]
    prior_vwap = features.prior_vwap_15m[index]
    if atr_value is None or atr_value <= 0 or prior_vwap is None or bar.volume <= 0:
        return False
    if bar.close >= prior_vwap:
        return False

    previous_close = features.bars[index - 1].close if index > 0 else bar.open
    true_range = max(
        bar.high - bar.low,
        abs(bar.high - previous_close),
        abs(bar.low - previous_close),
    )
    if true_range > cfg.max_true_range_atr * atr_value:
        return False
    if not filters_enabled:
        return True

    pullback_depth = (prior_vwap - bar.close) / atr_value
    return cfg.min_pullback_depth_atr <= pullback_depth <= cfg.max_pullback_depth_atr


def _recovery_eligible(
    features: V3PullbackFeatures,
    index: int,
    cfg: V3PullbackConfig,
    *,
    filters_enabled: bool,
) -> bool:
    if not _source_ready(features, index, cfg) or not _bull_regime(features, index, cfg):
        return False
    if index < cfg.recovery_high_lookback:
        return False

    bar = features.bars[index]
    atr_value = features.atr_15m[index]
    prior_vwap = features.prior_vwap_15m[index]
    prior_median_volume = features.prior_median_volume_15m[index]
    if (
        atr_value is None
        or atr_value <= 0
        or prior_vwap is None
        or prior_median_volume is None
    ):
        return False

    local_high = max(
        item.high
        for item in features.bars[index - cfg.recovery_high_lookback : index]
    )
    if not (bar.close > local_high and bar.close > bar.open):
        return False
    if bar.close <= prior_vwap - cfg.recovery_vwap_buffer_atr * atr_value:
        return False
    return not filters_enabled or bar.volume >= cfg.min_volume_ratio * prior_median_volume


def _profit_factor(values: list[float]) -> float:
    gross_profit = sum(max(value, 0.0) for value in values)
    gross_loss = -sum(min(value, 0.0) for value in values)
    if gross_loss == 0:
        return math.inf if gross_profit > 0 else 0.0
    return gross_profit / gross_loss


def _utc_day(timestamp_ms: int):
    return datetime.fromtimestamp(timestamp_ms / 1000.0, tz=UTC).date()


def _sell_price(raw_price: float, slippage_bps: float) -> float:
    return raw_price * (1.0 - slippage_bps / 10_000.0)


def run_v3_pullback_backtest(
    candles: Iterable[Candle],
    config: V3PullbackConfig | None = None,
    *,
    evaluation_start_ms: int | None = None,
    evaluation_end_exclusive_ms: int | None = None,
    risk_sized: bool = False,
    filters_enabled: bool = True,
) -> V3PullbackResult:
    cfg = config or BASELINE_V3_PULLBACK_CONFIG
    bars = list(candles)
    if not bars:
        raise ValueError("V3 requires candles")
    features = prepare_v3_pullback_features(bars, cfg)

    requested_start = (
        evaluation_start_ms if evaluation_start_ms is not None else bars[0].open_time_ms
    )
    requested_end = (
        evaluation_end_exclusive_ms
        if evaluation_end_exclusive_ms is not None
        else bars[-1].close_time_ms + 1
    )
    candidate_indices = [
        index
        for index, bar in enumerate(bars)
        if requested_start <= bar.open_time_ms < requested_end
    ]
    if not candidate_indices:
        raise ValueError("V3 evaluation window contains no candles")
    start_index = next(
        (index for index in candidate_indices if _features_ready(features, index, cfg)),
        None,
    )
    if start_index is None:
        raise ValueError("V3 indicators cannot warm within the evaluation context")
    end_index = candidate_indices[-1] + 1
    if end_index - start_index < 2:
        raise ValueError("V3 evaluation window is too short")

    cash = cfg.initial_cash
    quantity = 0.0
    entry_price = 0.0
    entry_fee = 0.0
    entry_time_ms = 0
    entry_bar_index = -1
    initial_stop = 0.0
    active_stop = 0.0
    profit_target = 0.0
    planned_risk_usd = 0.0
    planned_risk_fraction = 0.0
    entry_notional_fraction = 0.0
    entry_invariants_valid = False

    arm: _ArmState | None = None
    pending_entry: _SignalIntent | None = None
    pending_normal_exit: str | None = None
    exit_bar_index: int | None = None

    trades: list[V3PullbackTrade] = []
    total_cost = 0.0
    stop_out_count = 0
    target_exit_count = 0
    time_exit_count = 0
    regime_exit_count = 0
    daily_halt_days: set[object] = set()
    max_drawdown_halted = False
    entry_invariant_violations = 0
    veto_entry_violations = 0
    equity_curve = [cfg.initial_cash]
    bar_returns: list[float] = []
    previous_equity = cfg.initial_cash
    peak_equity = cfg.initial_cash
    exposed_bars = 0
    notional_fraction_sum = 0.0
    max_notional_fraction = 0.0
    evaluated_bars = 0
    current_day = None
    day_start_equity = cfg.initial_cash
    day_realized_pnl = 0.0
    daily_halted = False

    def close_position(
        raw_price: float,
        timestamp_ms: int,
        reason: str,
        bar_index: int,
    ) -> None:
        nonlocal cash, quantity, total_cost, stop_out_count, target_exit_count
        nonlocal time_exit_count, regime_exit_count, day_realized_pnl, exit_bar_index
        if quantity <= 0:
            return

        execution_price = _sell_price(raw_price, cfg.slippage_bps)
        gross = quantity * execution_price
        fee = gross * cfg.fee_bps / 10_000.0
        slippage_cost = quantity * max(raw_price - execution_price, 0.0)
        total_cost += fee + slippage_cost
        exit_net = gross - fee
        entry_outflow = quantity * entry_price + entry_fee
        pnl = exit_net - entry_outflow
        cash += exit_net
        day_realized_pnl += pnl
        trades.append(
            V3PullbackTrade(
                trade=ClosedTrade(
                    entry_time_ms=entry_time_ms,
                    exit_time_ms=timestamp_ms,
                    entry_price=entry_price,
                    exit_price=execution_price,
                    net_return=pnl / entry_outflow if entry_outflow > 0 else 0.0,
                    pnl=pnl,
                ),
                quantity=quantity,
                initial_stop=initial_stop,
                profit_target=profit_target,
                planned_risk_usd=planned_risk_usd,
                planned_risk_fraction=planned_risk_fraction,
                entry_notional_fraction=entry_notional_fraction,
                exit_reason=reason,
                entry_invariants_valid=entry_invariants_valid,
            )
        )
        if reason == "stop":
            stop_out_count += 1
        elif reason == "target":
            target_exit_count += 1
        elif reason == "time_exit":
            time_exit_count += 1
        elif reason == "regime_exit":
            regime_exit_count += 1
        quantity = 0.0
        exit_bar_index = bar_index

    for index in range(start_index, end_index):
        bar = bars[index]
        day = _utc_day(bar.open_time_ms)
        if day != current_day:
            current_day = day
            day_start_equity = previous_equity
            day_realized_pnl = 0.0
            daily_halted = False

        if quantity > 0 and bar.open <= active_stop:
            close_position(bar.open, bar.open_time_ms, "stop", index)
            pending_normal_exit = None
        elif quantity > 0 and bar.open >= profit_target:
            close_position(bar.open, bar.open_time_ms, "target", index)
            pending_normal_exit = None
        elif quantity > 0 and pending_normal_exit is not None:
            close_position(bar.open, bar.open_time_ms, pending_normal_exit, index)
            pending_normal_exit = None

        equity_at_open = cash + quantity * bar.open
        if (
            risk_sized
            and day_start_equity > 0
            and day_realized_pnl / day_start_equity <= -cfg.daily_loss_limit
        ):
            daily_halted = True
            daily_halt_days.add(day)

        if pending_entry is not None and quantity == 0:
            signal_bar = bars[pending_entry.signal_index]
            contiguous = bar.open_time_ms - signal_bar.open_time_ms == FIFTEEN_MINUTES_MS
            favorable_gap_ok = (
                bar.open
                <= pending_entry.signal_close
                + cfg.max_entry_gap_atr * pending_entry.signal_atr
            )
            invalidation_ok = bar.open > pending_entry.raw_stop
            source_ok = _source_ready(features, index, cfg)
            regime_ok = _bull_regime(features, index, cfg)
            risk_veto = risk_sized and (daily_halted or max_drawdown_halted)

            if (
                contiguous
                and favorable_gap_ok
                and invalidation_ok
                and source_ok
                and regime_ok
                and not risk_veto
            ):
                raw_entry = bar.open
                execution_entry = raw_entry * (1.0 + cfg.slippage_bps / 10_000.0)
                stop_distance = execution_entry - pending_entry.raw_stop
                min_stop = cfg.min_stop_distance_atr * pending_entry.signal_atr
                max_stop = cfg.max_stop_distance_atr * pending_entry.signal_atr
                if pending_entry.raw_stop > 0 and min_stop <= stop_distance <= max_stop:
                    fee_rate = cfg.fee_bps / 10_000.0
                    if risk_sized:
                        risk_budget = equity_at_open * cfg.risk_fraction
                        risk_quantity = risk_budget / stop_distance
                        notional_quantity = (
                            equity_at_open
                            * cfg.max_notional_fraction
                            / (execution_entry * (1.0 + fee_rate))
                        )
                        cash_quantity = cash / (execution_entry * (1.0 + fee_rate))
                        entry_quantity = min(
                            risk_quantity,
                            notional_quantity,
                            cash_quantity,
                        )
                    else:
                        entry_quantity = cash / (execution_entry * (1.0 + fee_rate))

                    if entry_quantity > 0:
                        fee = entry_quantity * execution_entry * fee_rate
                        required_cash = entry_quantity * execution_entry + fee
                        entry_slippage = entry_quantity * max(
                            execution_entry - raw_entry,
                            0.0,
                        )
                        if required_cash > cash + 1e-9:
                            raise RuntimeError("V3 Spot entry exceeded cash")
                        cash -= required_cash
                        total_cost += fee + entry_slippage
                        quantity = entry_quantity
                        entry_price = execution_entry
                        entry_fee = fee
                        entry_time_ms = bar.open_time_ms
                        entry_bar_index = index
                        initial_stop = pending_entry.raw_stop
                        active_stop = pending_entry.raw_stop
                        profit_target = execution_entry + cfg.target_r * stop_distance
                        planned_risk_usd = entry_quantity * stop_distance
                        planned_risk_fraction = (
                            planned_risk_usd / equity_at_open if equity_at_open > 0 else 0.0
                        )
                        entry_notional_fraction = (
                            required_cash / equity_at_open if equity_at_open > 0 else 0.0
                        )
                        entry_invariants_valid = pending_entry.invariants_valid
                        if not entry_invariants_valid:
                            entry_invariant_violations += 1
                        max_notional_fraction = max(
                            max_notional_fraction,
                            entry_notional_fraction,
                        )
            pending_entry = None

        if quantity > 0:
            stop_touched = bar.low <= active_stop
            target_touched = bar.high >= profit_target
            if stop_touched:
                close_position(active_stop, bar.close_time_ms, "stop", index)
            elif target_touched:
                close_position(profit_target, bar.close_time_ms, "target", index)

        mark_equity = cash + quantity * bar.close
        if quantity > 0:
            exposed_bars += 1
            current_notional_fraction = (
                quantity * bar.close / mark_equity if mark_equity > 0 else 0.0
            )
            notional_fraction_sum += current_notional_fraction
        evaluated_bars += 1
        if previous_equity > 0:
            bar_returns.append(mark_equity / previous_equity - 1.0)
        previous_equity = mark_equity
        equity_curve.append(mark_equity)
        peak_equity = max(peak_equity, mark_equity)

        if (
            risk_sized
            and peak_equity > 0
            and mark_equity / peak_equity - 1.0 <= -cfg.max_drawdown_halt
        ):
            max_drawdown_halted = True
        if (
            risk_sized
            and day_start_equity > 0
            and day_realized_pnl / day_start_equity <= -cfg.daily_loss_limit
        ):
            daily_halted = True
            daily_halt_days.add(day)

        if quantity > 0:
            held_bars = index - entry_bar_index + 1
            hour_index = features.latest_4h_index[index]
            regime_invalid = (
                hour_index is not None
                and features.invalid_4h_streak[hour_index] >= 2
            )
            if held_bars >= cfg.max_holding_bars:
                pending_normal_exit = "time_exit"
            elif regime_invalid:
                pending_normal_exit = "regime_exit"
            continue

        if index >= end_index - 1 or pending_entry is not None:
            continue

        cooldown_complete = (
            exit_bar_index is None or index - exit_bar_index >= cfg.reentry_cooldown_bars
        )
        risk_veto = risk_sized and (daily_halted or max_drawdown_halted)
        if not cooldown_complete or risk_veto:
            arm = None
            continue

        arm_terminated_this_bar = False
        if arm is not None:
            arm.pullback_low = min(arm.pullback_low, bar.low)
            if not _source_ready(features, index, cfg) or not _bull_regime(
                features,
                index,
                cfg,
            ):
                arm = None
                arm_terminated_this_bar = True
            elif _recovery_eligible(
                features,
                index,
                cfg,
                filters_enabled=filters_enabled,
            ):
                atr_value = features.atr_15m[index]
                if atr_value is None or atr_value <= 0:
                    raise RuntimeError("V3 recovery ATR unexpectedly unavailable")
                raw_stop = arm.pullback_low - cfg.stop_buffer_atr * atr_value
                pending_entry = _SignalIntent(
                    signal_index=index,
                    signal_close=bar.close,
                    signal_atr=atr_value,
                    raw_stop=raw_stop,
                    invariants_valid=True,
                )
                arm = None
                arm_terminated_this_bar = True
            elif index - arm.arm_index >= cfg.arm_lifetime_bars:
                arm = None
                arm_terminated_this_bar = True

        if (
            arm is None
            and pending_entry is None
            and not arm_terminated_this_bar
            and _arm_eligible(
                features,
                index,
                cfg,
                filters_enabled=filters_enabled,
            )
        ):
            arm = _ArmState(arm_index=index, pullback_low=bar.low)

    if quantity > 0:
        final_bar = bars[end_index - 1]
        close_position(
            final_bar.close,
            final_bar.close_time_ms,
            "end_of_test",
            end_index - 1,
        )
        prior_equity = equity_curve[-2] if len(equity_curve) >= 2 else cfg.initial_cash
        if bar_returns and prior_equity > 0:
            bar_returns[-1] = cash / prior_equity - 1.0
        equity_curve[-1] = cash

    pnl_values = [item.trade.pnl for item in trades]
    wins = [value for value in pnl_values if value > 0]
    losses = [value for value in pnl_values if value < 0]
    evaluation_bars = bars[start_index:end_index]
    benchmark_return, benchmark_drawdown = _buy_and_hold_metrics(evaluation_bars, cfg)
    bars_per_year = _infer_bars_per_year(evaluation_bars)
    sharpe, sortino = _risk_adjusted_ratios(bar_returns, bars_per_year)
    final_equity = cash
    total_return = final_equity / cfg.initial_cash - 1.0

    return V3PullbackResult(
        layer="risk_sized" if risk_sized else "signal_allocation",
        initial_cash=cfg.initial_cash,
        final_equity=final_equity,
        total_return=total_return,
        annualized_return=_annualized_return(
            cfg.initial_cash,
            final_equity,
            evaluation_bars,
        ),
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
        time_exposure=exposed_bars / max(evaluated_bars, 1),
        average_notional_fraction=(
            notional_fraction_sum / exposed_bars if exposed_bars else 0.0
        ),
        max_notional_fraction=max_notional_fraction,
        max_planned_risk_fraction=max(
            (item.planned_risk_fraction for item in trades),
            default=0.0,
        ),
        total_cost=total_cost,
        stop_out_count=stop_out_count,
        target_exit_count=target_exit_count,
        time_exit_count=time_exit_count,
        regime_exit_count=regime_exit_count,
        daily_halt_count=len(daily_halt_days),
        max_drawdown_halted=max_drawdown_halted,
        entry_invariant_violations=entry_invariant_violations,
        veto_entry_violations=veto_entry_violations,
        effective_start_ms=evaluation_bars[0].open_time_ms,
        effective_end_exclusive_ms=evaluation_bars[-1].close_time_ms + 1,
        trades=tuple(trades),
    )
