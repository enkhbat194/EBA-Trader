from __future__ import annotations

import math
from bisect import bisect_left, insort
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
from .trend_v2_policy import BASELINE_TREND_V2_CONFIG, TrendV2Config

FIFTEEN_MINUTES_MS = 15 * 60 * 1000
ONE_HOUR_MS = 60 * 60 * 1000


@dataclass(frozen=True, slots=True)
class DirectionalIndicators:
    atr: tuple[float | None, ...]
    plus_di: tuple[float | None, ...]
    minus_di: tuple[float | None, ...]
    adx: tuple[float | None, ...]


@dataclass(frozen=True, slots=True)
class TrendV2Features:
    bars: tuple[Candle, ...]
    hourly_bars: tuple[Candle, ...]
    atr_15m: tuple[float | None, ...]
    atr_pct_median: tuple[float | None, ...]
    ema20_15m: tuple[float | None, ...]
    ema50_15m: tuple[float | None, ...]
    ema50_1h: tuple[float | None, ...]
    ema200_1h: tuple[float | None, ...]
    plus_di_1h: tuple[float | None, ...]
    minus_di_1h: tuple[float | None, ...]
    adx_1h: tuple[float | None, ...]
    latest_hour_index: tuple[int | None, ...]
    complete_hour_streak: tuple[int, ...]
    invalid_hour_streak: tuple[int, ...]
    contiguous_15m_streak: tuple[int, ...]


@dataclass(frozen=True, slots=True)
class TrendV2Trade:
    trade: ClosedTrade
    quantity: float
    initial_stop: float
    planned_risk_usd: float
    planned_risk_fraction: float
    entry_notional_fraction: float
    exit_reason: str
    entry_invariants_valid: bool


@dataclass(frozen=True, slots=True)
class TrendV2Result:
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
    daily_halt_count: int
    max_drawdown_halted: bool
    entry_invariant_violations: int
    veto_entry_violations: int
    effective_start_ms: int
    effective_end_exclusive_ms: int
    trades: tuple[TrendV2Trade, ...]


@dataclass(frozen=True, slots=True)
class _SignalIntent:
    signal_index: int
    signal_close: float
    signal_atr: float
    signal_stop: float
    invariants_valid: bool


def _wilder_average(values: list[float], period: int) -> list[float | None]:
    result: list[float | None] = [None] * len(values)
    if period <= 1:
        raise ValueError("period must be > 1")
    if len(values) < period:
        return result
    current = sum(values[:period]) / period
    result[period - 1] = current
    for index in range(period, len(values)):
        current = ((period - 1) * current + values[index]) / period
        result[index] = current
    return result


def directional_indicators(
    candles: Iterable[Candle],
    period: int = 14,
) -> DirectionalIndicators:
    bars = list(candles)
    if period <= 1:
        raise ValueError("period must be > 1")
    if not bars:
        return DirectionalIndicators((), (), (), ())

    true_ranges: list[float] = []
    plus_dm: list[float] = []
    minus_dm: list[float] = []
    for index, bar in enumerate(bars):
        if index == 0:
            true_ranges.append(bar.high - bar.low)
            plus_dm.append(0.0)
            minus_dm.append(0.0)
            continue
        previous = bars[index - 1]
        true_ranges.append(
            max(
                bar.high - bar.low,
                abs(bar.high - previous.close),
                abs(bar.low - previous.close),
            )
        )
        up_move = bar.high - previous.high
        down_move = previous.low - bar.low
        plus_dm.append(up_move if up_move > down_move and up_move > 0 else 0.0)
        minus_dm.append(down_move if down_move > up_move and down_move > 0 else 0.0)

    atr_values = _wilder_average(true_ranges, period)
    plus_smoothed = _wilder_average(plus_dm, period)
    minus_smoothed = _wilder_average(minus_dm, period)
    plus_di: list[float | None] = [None] * len(bars)
    minus_di: list[float | None] = [None] * len(bars)
    dx: list[float | None] = [None] * len(bars)
    for index in range(len(bars)):
        atr_value = atr_values[index]
        plus_value = plus_smoothed[index]
        minus_value = minus_smoothed[index]
        if atr_value is None or plus_value is None or minus_value is None or atr_value <= 0:
            continue
        plus_di[index] = 100.0 * plus_value / atr_value
        minus_di[index] = 100.0 * minus_value / atr_value
        denominator = plus_di[index] + minus_di[index]
        dx[index] = (
            100.0 * abs(plus_di[index] - minus_di[index]) / denominator
            if denominator > 0
            else 0.0
        )

    adx_values: list[float | None] = [None] * len(bars)
    first_dx = period - 1
    seed_end = first_dx + period
    if seed_end <= len(bars):
        seed_values = [value for value in dx[first_dx:seed_end] if value is not None]
        if len(seed_values) == period:
            current = sum(seed_values) / period
            seed_index = seed_end - 1
            adx_values[seed_index] = current
            for index in range(seed_index + 1, len(bars)):
                if dx[index] is None:
                    continue
                current = ((period - 1) * current + dx[index]) / period
                adx_values[index] = current

    return DirectionalIndicators(
        atr=tuple(atr_values),
        plus_di=tuple(plus_di),
        minus_di=tuple(minus_di),
        adx=tuple(adx_values),
    )


def resample_complete_hours(candles: Iterable[Candle]) -> tuple[Candle, ...]:
    bars = list(candles)
    grouped: dict[int, list[Candle]] = defaultdict(list)
    for bar in bars:
        hour_start = bar.open_time_ms - bar.open_time_ms % ONE_HOUR_MS
        grouped[hour_start].append(bar)

    result: list[Candle] = []
    expected_offsets = (0, FIFTEEN_MINUTES_MS, 2 * FIFTEEN_MINUTES_MS, 3 * FIFTEEN_MINUTES_MS)
    for hour_start in sorted(grouped):
        group = sorted(grouped[hour_start], key=lambda item: item.open_time_ms)
        offsets = tuple(item.open_time_ms - hour_start for item in group)
        if offsets != expected_offsets:
            continue
        result.append(
            Candle(
                open_time_ms=hour_start,
                open=group[0].open,
                high=max(item.high for item in group),
                low=min(item.low for item in group),
                close=group[-1].close,
                volume=sum(item.volume for item in group),
                close_time_ms=hour_start + ONE_HOUR_MS - 1,
                quote_volume=sum(item.quote_volume for item in group),
                trade_count=sum(item.trade_count for item in group),
            )
        )
    return tuple(result)


def rolling_prior_median(
    values: Iterable[float | None],
    window: int,
) -> tuple[float | None, ...]:
    if window <= 0:
        raise ValueError("window must be positive")
    queue: deque[float] = deque()
    ordered: list[float] = []
    result: list[float | None] = []
    for value in values:
        result.append(median(ordered) if len(queue) == window else None)
        if value is None:
            continue
        queue.append(value)
        insort(ordered, value)
        if len(queue) > window:
            removed = queue.popleft()
            ordered.pop(bisect_left(ordered, removed))
    return tuple(result)


def _contiguous_streak(bars: list[Candle], step_ms: int) -> tuple[int, ...]:
    if not bars:
        return ()
    result = [1]
    for index in range(1, len(bars)):
        result.append(
            result[-1] + 1
            if bars[index].open_time_ms - bars[index - 1].open_time_ms == step_ms
            else 1
        )
    return tuple(result)


def prepare_trend_v2_features(
    candles: Iterable[Candle],
    config: TrendV2Config | None = None,
) -> TrendV2Features:
    cfg = config or BASELINE_TREND_V2_CONFIG
    bars = list(candles)
    if not bars:
        raise ValueError("Trend V2 requires candles")
    hourly = list(resample_complete_hours(bars))

    closes_15m = [bar.close for bar in bars]
    atr_15m = tuple(atr(bars, cfg.atr_period))
    atr_pct = [
        value / bar.close if value is not None and bar.close > 0 else None
        for bar, value in zip(bars, atr_15m, strict=True)
    ]
    atr_pct_median = rolling_prior_median(atr_pct, cfg.volatility_median_bars)
    ema20_15m = tuple(ema(closes_15m, cfg.signal_fast_ema))
    ema50_15m = tuple(ema(closes_15m, cfg.signal_slow_ema))

    closes_1h = [bar.close for bar in hourly]
    ema50_1h = tuple(ema(closes_1h, cfg.hour_fast_ema))
    ema200_1h = tuple(ema(closes_1h, cfg.hour_slow_ema))
    directional = directional_indicators(hourly, cfg.adx_period)

    latest_hour_index: list[int | None] = []
    hourly_cursor = -1
    for bar in bars:
        while (
            hourly_cursor + 1 < len(hourly)
            and hourly[hourly_cursor + 1].close_time_ms <= bar.close_time_ms
        ):
            hourly_cursor += 1
        latest_hour_index.append(hourly_cursor if hourly_cursor >= 0 else None)

    hour_complete_streak = _contiguous_streak(hourly, ONE_HOUR_MS)
    complete_hour_streak = [
        hour_complete_streak[index] if index is not None else 0
        for index in latest_hour_index
    ]
    contiguous_15m_streak = _contiguous_streak(bars, FIFTEEN_MINUTES_MS)

    invalid_hour_streak: list[int] = []
    for index, bar in enumerate(hourly):
        fast = ema50_1h[index]
        slow = ema200_1h[index]
        plus = directional.plus_di[index]
        minus = directional.minus_di[index]
        adx_value = directional.adx[index]
        ready = all(value is not None for value in (fast, slow, plus, minus, adx_value))
        structural = ready and bar.close > fast > slow
        invalid = not ready or not structural or plus <= minus or adx_value < cfg.adx_exit_threshold
        contiguous = index > 0 and bar.open_time_ms - hourly[index - 1].open_time_ms == ONE_HOUR_MS
        previous = invalid_hour_streak[-1] if contiguous and invalid_hour_streak else 0
        invalid_hour_streak.append(previous + 1 if invalid else 0)

    return TrendV2Features(
        bars=tuple(bars),
        hourly_bars=tuple(hourly),
        atr_15m=atr_15m,
        atr_pct_median=atr_pct_median,
        ema20_15m=ema20_15m,
        ema50_15m=ema50_15m,
        ema50_1h=ema50_1h,
        ema200_1h=ema200_1h,
        plus_di_1h=directional.plus_di,
        minus_di_1h=directional.minus_di,
        adx_1h=directional.adx,
        latest_hour_index=tuple(latest_hour_index),
        complete_hour_streak=tuple(complete_hour_streak),
        invalid_hour_streak=tuple(invalid_hour_streak),
        contiguous_15m_streak=contiguous_15m_streak,
    )


def _features_ready(features: TrendV2Features, index: int, cfg: TrendV2Config) -> bool:
    hour_index = features.latest_hour_index[index]
    if hour_index is None or hour_index < cfg.hour_slope_lookback:
        return False
    if index < max(cfg.donchian_lookback + 1, cfg.signal_slope_lookback):
        return False
    hour_values = (
        features.ema50_1h[hour_index],
        features.ema200_1h[hour_index],
        features.ema200_1h[hour_index - cfg.hour_slope_lookback],
        features.plus_di_1h[hour_index],
        features.minus_di_1h[hour_index],
        features.adx_1h[hour_index],
    )
    bar_values = (
        features.atr_15m[index],
        features.atr_pct_median[index],
        features.ema20_15m[index],
        features.ema50_15m[index],
        features.ema20_15m[index - cfg.signal_slope_lookback],
    )
    return all(value is not None for value in hour_values + bar_values)


def _entry_conditions(
    features: TrendV2Features,
    index: int,
    cfg: TrendV2Config,
    *,
    filters_enabled: bool,
) -> tuple[bool, bool]:
    if not _features_ready(features, index, cfg):
        return False, False
    if features.complete_hour_streak[index] < cfg.complete_hours_after_gap:
        return True, False

    bars = features.bars
    fast = features.ema20_15m[index]
    slow = features.ema50_15m[index]
    prior_fast = features.ema20_15m[index - cfg.signal_slope_lookback]
    alignment = fast > slow and fast > prior_fast
    breakout = bars[index].close > max(
        item.high for item in bars[index - cfg.donchian_lookback : index]
    )
    prior_level = max(
        item.high for item in bars[index - cfg.donchian_lookback - 1 : index - 1]
    )
    fresh = bars[index - 1].close <= prior_level
    if not alignment or not breakout or not fresh:
        return True, False

    if not filters_enabled:
        return True, True

    hour_index = features.latest_hour_index[index]
    hour = features.hourly_bars[hour_index]
    hour_fast = features.ema50_1h[hour_index]
    hour_slow = features.ema200_1h[hour_index]
    old_slow = features.ema200_1h[hour_index - cfg.hour_slope_lookback]
    plus = features.plus_di_1h[hour_index]
    minus = features.minus_di_1h[hour_index]
    adx_value = features.adx_1h[hour_index]
    regime = (
        hour.close > hour_fast > hour_slow
        and hour_slow > old_slow
        and adx_value >= cfg.adx_entry_threshold
        and plus > minus
    )
    atr_value = features.atr_15m[index]
    median_atr_pct = features.atr_pct_median[index]
    atr_pct = atr_value / bars[index].close
    relative_atr = atr_pct / median_atr_pct if median_atr_pct > 0 else math.inf
    volatility = (
        cfg.min_relative_atr <= relative_atr <= cfg.max_relative_atr
        and atr_pct <= cfg.absolute_atr_pct_ceiling
    )
    return True, regime and volatility


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


def run_trend_v2_backtest(
    candles: Iterable[Candle],
    config: TrendV2Config | None = None,
    *,
    evaluation_start_ms: int | None = None,
    evaluation_end_exclusive_ms: int | None = None,
    risk_sized: bool = False,
    filters_enabled: bool = True,
) -> TrendV2Result:
    cfg = config or BASELINE_TREND_V2_CONFIG
    bars = list(candles)
    features = prepare_trend_v2_features(bars, cfg)
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
        raise ValueError("Trend V2 evaluation window contains no candles")
    start_index = next(
        (index for index in candidate_indices if _features_ready(features, index, cfg)),
        None,
    )
    if start_index is None:
        raise ValueError("Trend V2 indicators cannot warm within the evaluation context")
    end_index = candidate_indices[-1] + 1
    if end_index - start_index < 2:
        raise ValueError("Trend V2 evaluation window is too short")

    cash = cfg.initial_cash
    quantity = 0.0
    entry_price = 0.0
    entry_fee = 0.0
    entry_time_ms = 0
    initial_stop = 0.0
    active_stop = 0.0
    highest_completed_high = 0.0
    planned_risk_usd = 0.0
    planned_risk_fraction = 0.0
    entry_notional_fraction = 0.0
    entry_invariants_valid = False
    pending_entry: _SignalIntent | None = None
    pending_normal_exit = False
    exit_bar_index: int | None = None
    trades: list[TrendV2Trade] = []
    total_cost = 0.0
    stop_out_count = 0
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

    def close_position(raw_price: float, timestamp_ms: int, reason: str, bar_index: int) -> None:
        nonlocal cash, quantity, total_cost, stop_out_count, day_realized_pnl, exit_bar_index
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
            TrendV2Trade(
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
                planned_risk_usd=planned_risk_usd,
                planned_risk_fraction=planned_risk_fraction,
                entry_notional_fraction=entry_notional_fraction,
                exit_reason=reason,
                entry_invariants_valid=entry_invariants_valid,
            )
        )
        if reason == "stop":
            stop_out_count += 1
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
            pending_normal_exit = False
        elif quantity > 0 and pending_normal_exit:
            close_position(bar.open, bar.open_time_ms, "normal_exit", index)
            pending_normal_exit = False

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
                <= pending_entry.signal_close + cfg.max_entry_gap_atr * pending_entry.signal_atr
            )
            invalidation_ok = bar.open > pending_entry.signal_stop
            risk_veto = risk_sized and (daily_halted or max_drawdown_halted)
            if contiguous and favorable_gap_ok and invalidation_ok and not risk_veto:
                raw_entry = bar.open
                execution_entry = raw_entry * (1.0 + cfg.slippage_bps / 10_000.0)
                candidate_stop = execution_entry - cfg.initial_stop_atr * pending_entry.signal_atr
                if candidate_stop > 0:
                    fee_rate = cfg.fee_bps / 10_000.0
                    if risk_sized:
                        loss_per_unit = execution_entry - candidate_stop
                        risk_budget = equity_at_open * cfg.risk_fraction
                        risk_quantity = risk_budget / loss_per_unit if loss_per_unit > 0 else 0.0
                        notional_quantity = (
                            equity_at_open
                            * cfg.max_notional_fraction
                            / (execution_entry * (1.0 + fee_rate))
                        )
                        cash_quantity = cash / (execution_entry * (1.0 + fee_rate))
                        entry_quantity = min(risk_quantity, notional_quantity, cash_quantity)
                    else:
                        entry_quantity = cash / (execution_entry * (1.0 + fee_rate))
                    if entry_quantity > 0:
                        fee = entry_quantity * execution_entry * fee_rate
                        required_cash = entry_quantity * execution_entry + fee
                        entry_slippage = entry_quantity * max(execution_entry - raw_entry, 0.0)
                        if required_cash > cash + 1e-9:
                            raise RuntimeError("Trend V2 Spot entry exceeded cash")
                        cash -= required_cash
                        total_cost += fee + entry_slippage
                        quantity = entry_quantity
                        entry_price = execution_entry
                        entry_fee = fee
                        entry_time_ms = bar.open_time_ms
                        initial_stop = candidate_stop
                        active_stop = candidate_stop
                        highest_completed_high = bar.open
                        planned_risk_usd = entry_quantity * (
                            execution_entry - candidate_stop
                        )
                        planned_risk_fraction = (
                            planned_risk_usd / equity_at_open if equity_at_open > 0 else 0.0
                        )
                        entry_notional_fraction = (
                            required_cash / equity_at_open if equity_at_open > 0 else 0.0
                        )
                        entry_invariants_valid = pending_entry.invariants_valid
                        if not entry_invariants_valid:
                            entry_invariant_violations += 1
                        if risk_veto:
                            veto_entry_violations += 1
                        max_notional_fraction = max(
                            max_notional_fraction,
                            entry_notional_fraction,
                        )
            pending_entry = None

        if quantity > 0 and bar.low <= active_stop:
            close_position(active_stop, bar.close_time_ms, "stop", index)

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
            highest_completed_high = max(highest_completed_high, bar.high)
            atr_value = features.atr_15m[index]
            if atr_value is not None:
                active_stop = max(
                    active_stop,
                    highest_completed_high - cfg.trailing_stop_atr * atr_value,
                )
            hour_index = features.latest_hour_index[index]
            regime_invalid = (
                hour_index is not None
                and features.invalid_hour_streak[hour_index] >= cfg.regime_exit_bars
            )
            ema_exit = (
                features.ema50_15m[index] is not None
                and bar.close < features.ema50_15m[index]
            )
            pending_normal_exit = regime_invalid or ema_exit
        elif index < end_index - 1:
            cooldown_complete = (
                exit_bar_index is None or index - exit_bar_index >= cfg.reentry_cooldown_bars
            )
            ready, eligible = _entry_conditions(
                features,
                index,
                cfg,
                filters_enabled=filters_enabled,
            )
            risk_veto = risk_sized and (daily_halted or max_drawdown_halted)
            if cooldown_complete and ready and eligible and not risk_veto:
                atr_value = features.atr_15m[index]
                pending_entry = _SignalIntent(
                    signal_index=index,
                    signal_close=bar.close,
                    signal_atr=atr_value,
                    signal_stop=bar.close - cfg.initial_stop_atr * atr_value,
                    invariants_valid=True,
                )

    if quantity > 0:
        final_bar = bars[end_index - 1]
        close_position(final_bar.close, final_bar.close_time_ms, "end_of_test", end_index - 1)
        prior_equity = equity_curve[-2] if len(equity_curve) >= 2 else cfg.initial_cash
        if bar_returns and prior_equity > 0:
            bar_returns[-1] = cash / prior_equity - 1.0
        equity_curve[-1] = cash

    pnl_values = [item.trade.pnl for item in trades]
    wins = [value for value in pnl_values if value > 0]
    losses = [value for value in pnl_values if value < 0]
    evaluation_bars = bars[start_index:end_index]
    benchmark_return, benchmark_drawdown = _buy_and_hold_metrics(
        evaluation_bars,
        cfg,
    )
    bars_per_year = _infer_bars_per_year(evaluation_bars)
    sharpe, sortino = _risk_adjusted_ratios(bar_returns, bars_per_year)
    final_equity = cash
    total_return = final_equity / cfg.initial_cash - 1.0
    return TrendV2Result(
        layer="risk_sized" if risk_sized else "signal_allocation",
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
        daily_halt_count=len(daily_halt_days),
        max_drawdown_halted=max_drawdown_halted,
        entry_invariant_violations=entry_invariant_violations,
        veto_entry_violations=veto_entry_violations,
        effective_start_ms=evaluation_bars[0].open_time_ms,
        effective_end_exclusive_ms=evaluation_bars[-1].close_time_ms + 1,
        trades=tuple(trades),
    )
