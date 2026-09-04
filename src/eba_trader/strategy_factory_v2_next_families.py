from __future__ import annotations

import math
from bisect import bisect_left
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from statistics import mean
from typing import Any

from . import backtest as bt
from .history import Candle, validate_candles
from .orderflow_feature_dataset import OrderFlowFeatureRow

SOURCE_STEP_MS = 60_000
DERIVED_INTERVAL_MINUTES = frozenset({5, 15, 60})
NEXT_FAMILY_IDS = frozenset(
    {
        "mtf_trend_pullback_v1",
        "breakout_retest_entry_v1",
        "path_efficiency_persistence_v1",
        "low_turnover_flow_persistence_v1",
    }
)
INITIAL_CASH = 10_000.0
FEE_BPS = 4.0
SLIPPAGE_BPS = 1.5


@dataclass(frozen=True, slots=True)
class NextFamilySignal:
    entry: bool = False
    opposite: bool = False
    signed_strength: float = 0.0


@dataclass(frozen=True, slots=True)
class NextExecutionPolicy:
    side: int
    minimum_hold_minutes: int
    max_hold_minutes: int
    cooldown_minutes: int
    initial_cash: float = INITIAL_CASH
    fee_bps: float = FEE_BPS
    slippage_bps: float = SLIPPAGE_BPS

    def __post_init__(self) -> None:
        if self.side not in (-1, 1):
            raise ValueError("side must be +1 or -1")
        if self.minimum_hold_minutes < 15:
            raise ValueError("minimum_hold_minutes must be >= 15")
        if self.max_hold_minutes < self.minimum_hold_minutes:
            raise ValueError("max_hold_minutes must be >= minimum_hold_minutes")
        if self.max_hold_minutes > 24 * 60:
            raise ValueError("max_hold_minutes must be <= 1440")
        if self.cooldown_minutes < 5:
            raise ValueError("cooldown_minutes must be >= 5")


@dataclass(frozen=True, slots=True)
class MtfTrendPullbackConfig:
    side: int
    regime_lookback_15m: int
    pullback_lookback_5m: int
    minimum_regime_return: float
    minimum_pullback_return: float
    minimum_resume_return: float
    minimum_hold_minutes: int
    max_hold_minutes: int
    cooldown_minutes: int

    def __post_init__(self) -> None:
        _validate_side(self.side)
        _bounded_int(self.regime_lookback_15m, 4, 64, "regime_lookback_15m")
        _bounded_int(self.pullback_lookback_5m, 2, 24, "pullback_lookback_5m")
        _bounded_fraction(self.minimum_regime_return, 0.0001, 0.20, "minimum_regime_return")
        _bounded_fraction(
            self.minimum_pullback_return,
            0.0001,
            0.10,
            "minimum_pullback_return",
        )
        _bounded_fraction(self.minimum_resume_return, 0.0, 0.05, "minimum_resume_return")
        self.execution_policy

    @property
    def execution_policy(self) -> NextExecutionPolicy:
        return NextExecutionPolicy(
            side=self.side,
            minimum_hold_minutes=self.minimum_hold_minutes,
            max_hold_minutes=self.max_hold_minutes,
            cooldown_minutes=self.cooldown_minutes,
        )


@dataclass(frozen=True, slots=True)
class BreakoutRetestConfig:
    side: int
    range_lookback_15m: int
    minimum_breakout_bps: float
    retest_tolerance_bps: float
    max_retest_wait_5m: int
    minimum_hold_minutes: int
    max_hold_minutes: int
    cooldown_minutes: int

    def __post_init__(self) -> None:
        _validate_side(self.side)
        _bounded_int(self.range_lookback_15m, 4, 64, "range_lookback_15m")
        _bounded_float(self.minimum_breakout_bps, 0.0, 500.0, "minimum_breakout_bps")
        _bounded_float(self.retest_tolerance_bps, 0.0, 100.0, "retest_tolerance_bps")
        _bounded_int(self.max_retest_wait_5m, 1, 24, "max_retest_wait_5m")
        self.execution_policy

    @property
    def execution_policy(self) -> NextExecutionPolicy:
        return NextExecutionPolicy(
            side=self.side,
            minimum_hold_minutes=self.minimum_hold_minutes,
            max_hold_minutes=self.max_hold_minutes,
            cooldown_minutes=self.cooldown_minutes,
        )


@dataclass(frozen=True, slots=True)
class PathEfficiencyConfig:
    side: int
    lookback_15m: int
    minimum_efficiency: float
    minimum_directional_return: float
    minimum_hold_minutes: int
    max_hold_minutes: int
    cooldown_minutes: int

    def __post_init__(self) -> None:
        _validate_side(self.side)
        _bounded_int(self.lookback_15m, 4, 64, "lookback_15m")
        _bounded_fraction(self.minimum_efficiency, 0.05, 1.0, "minimum_efficiency")
        _bounded_fraction(
            self.minimum_directional_return,
            0.0001,
            0.20,
            "minimum_directional_return",
        )
        self.execution_policy

    @property
    def execution_policy(self) -> NextExecutionPolicy:
        return NextExecutionPolicy(
            side=self.side,
            minimum_hold_minutes=self.minimum_hold_minutes,
            max_hold_minutes=self.max_hold_minutes,
            cooldown_minutes=self.cooldown_minutes,
        )


@dataclass(frozen=True, slots=True)
class LowTurnoverFlowPersistenceConfig:
    side: int
    short_flow_lookback_minutes: int
    long_flow_lookback_minutes: int
    price_lookback_minutes: int
    minimum_short_flow_ratio: float
    minimum_long_flow_ratio: float
    minimum_directional_price_return: float
    minimum_hold_minutes: int
    max_hold_minutes: int
    cooldown_minutes: int

    def __post_init__(self) -> None:
        _validate_side(self.side)
        _bounded_int(
            self.short_flow_lookback_minutes,
            15,
            120,
            "short_flow_lookback_minutes",
        )
        _bounded_int(
            self.long_flow_lookback_minutes,
            30,
            360,
            "long_flow_lookback_minutes",
        )
        if self.long_flow_lookback_minutes <= self.short_flow_lookback_minutes:
            raise ValueError("long_flow_lookback_minutes must exceed short_flow_lookback_minutes")
        _bounded_int(self.price_lookback_minutes, 15, 360, "price_lookback_minutes")
        _bounded_fraction(self.minimum_short_flow_ratio, 0.001, 1.0, "minimum_short_flow_ratio")
        _bounded_fraction(self.minimum_long_flow_ratio, 0.001, 1.0, "minimum_long_flow_ratio")
        _bounded_fraction(
            self.minimum_directional_price_return,
            0.0,
            0.20,
            "minimum_directional_price_return",
        )
        policy = self.execution_policy
        if policy.minimum_hold_minutes < 30:
            raise ValueError("low-turnover flow minimum_hold_minutes must be >= 30")
        if policy.cooldown_minutes < 15:
            raise ValueError("low-turnover flow cooldown_minutes must be >= 15")

    @property
    def execution_policy(self) -> NextExecutionPolicy:
        return NextExecutionPolicy(
            side=self.side,
            minimum_hold_minutes=self.minimum_hold_minutes,
            max_hold_minutes=self.max_hold_minutes,
            cooldown_minutes=self.cooldown_minutes,
        )


@dataclass(frozen=True, slots=True)
class NextFamilyExecution:
    result: bt.BacktestResult
    signals: tuple[NextFamilySignal, ...]
    side: int


def _validate_side(side: int) -> None:
    if isinstance(side, bool) or side not in (-1, 1):
        raise ValueError("side must be +1 or -1")


def _bounded_int(value: int, minimum: int, maximum: int, name: str) -> None:
    if isinstance(value, bool) or not isinstance(value, int) or not minimum <= value <= maximum:
        raise ValueError(f"{name} must be an integer in [{minimum}, {maximum}]")


def _bounded_float(value: float, minimum: float, maximum: float, name: str) -> None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{name} must be numeric")
    numeric = float(value)
    if not math.isfinite(numeric) or not minimum <= numeric <= maximum:
        raise ValueError(f"{name} must be finite and in [{minimum}, {maximum}]")


def _bounded_fraction(value: float, minimum: float, maximum: float, name: str) -> None:
    _bounded_float(value, minimum, maximum, name)


def _validated_source_candles(candles: Sequence[Candle]) -> tuple[Candle, ...]:
    data = tuple(validate_candles(candles))
    for candle in data:
        if candle.open_time_ms % SOURCE_STEP_MS != 0:
            raise ValueError("next-family source candles must align to one-minute UTC boundaries")
    return data


def aggregate_closed_candles(
    candles: Sequence[Candle],
    *,
    interval_minutes: int,
) -> tuple[Candle, ...]:
    """Aggregate only complete UTC-aligned groups and never bridge a one-minute gap.

    Leading/trailing partial groups and groups containing any missing source minute are skipped.
    Every returned bar is therefore fully closed and can become available only after its
    ``close_time_ms``. The function is data preparation only and grants no research authority.
    """

    if interval_minutes not in DERIVED_INTERVAL_MINUTES:
        raise ValueError("derived interval must be one of 5, 15 or 60 minutes")
    data = _validated_source_candles(candles)
    step_ms = interval_minutes * SOURCE_STEP_MS
    expected_count = interval_minutes
    buckets: dict[int, list[Candle]] = {}
    for candle in data:
        bucket_start = candle.open_time_ms // step_ms * step_ms
        buckets.setdefault(bucket_start, []).append(candle)

    output: list[Candle] = []
    for bucket_start in sorted(buckets):
        rows = buckets[bucket_start]
        expected_opens = [bucket_start + index * SOURCE_STEP_MS for index in range(expected_count)]
        if len(rows) != expected_count:
            continue
        if [row.open_time_ms for row in rows] != expected_opens:
            continue
        if any(
            left.open_time_ms + SOURCE_STEP_MS != right.open_time_ms
            for left, right in zip(rows, rows[1:], strict=False)
        ):
            continue
        output.append(
            Candle(
                open_time_ms=bucket_start,
                open=rows[0].open,
                high=max(row.high for row in rows),
                low=min(row.low for row in rows),
                close=rows[-1].close,
                volume=sum(row.volume for row in rows),
                close_time_ms=rows[-1].close_time_ms,
                quote_volume=sum(row.quote_volume for row in rows),
                trade_count=sum(row.trade_count for row in rows),
            )
        )
    return tuple(output)


def _closed_before(
    bars: Sequence[Candle],
    close_times: Sequence[int],
    timestamp_ms: int,
) -> Sequence[Candle]:
    return bars[: bisect_left(close_times, timestamp_ms)]


def _directional_return(bars: Sequence[Candle], side: int) -> float:
    if not bars:
        return 0.0
    return float(side) * (bars[-1].close / bars[0].open - 1.0)


def _decision_boundary(timestamp_ms: int, interval_minutes: int) -> bool:
    return timestamp_ms % (interval_minutes * SOURCE_STEP_MS) == 0


def mtf_trend_pullback_signals(
    candles: Sequence[Candle],
    config: MtfTrendPullbackConfig,
) -> tuple[NextFamilySignal, ...]:
    source = _validated_source_candles(candles)
    bars_5m = aggregate_closed_candles(source, interval_minutes=5)
    bars_15m = aggregate_closed_candles(source, interval_minutes=15)
    close_5m = tuple(bar.close_time_ms for bar in bars_5m)
    close_15m = tuple(bar.close_time_ms for bar in bars_15m)
    output: list[NextFamilySignal] = []

    for candle in source:
        timestamp = candle.open_time_ms
        if not _decision_boundary(timestamp, 5):
            output.append(NextFamilySignal())
            continue
        known_5m = _closed_before(bars_5m, close_5m, timestamp)
        known_15m = _closed_before(bars_15m, close_15m, timestamp)
        if (
            len(known_15m) < config.regime_lookback_15m
            or len(known_5m) < config.pullback_lookback_5m + 1
        ):
            output.append(NextFamilySignal())
            continue

        regime = known_15m[-config.regime_lookback_15m :]
        pullback = known_5m[-config.pullback_lookback_5m - 1 : -1]
        resume = known_5m[-1]
        regime_return = _directional_return(regime, config.side)
        pullback_return = _directional_return(pullback, config.side)
        resume_return = float(config.side) * (resume.close / resume.open - 1.0)
        entry = (
            regime_return >= config.minimum_regime_return
            and pullback_return <= -config.minimum_pullback_return
            and resume_return >= config.minimum_resume_return
        )
        opposite = regime_return < 0.0
        strength = min(
            regime_return / config.minimum_regime_return,
            -pullback_return / config.minimum_pullback_return,
            (
                resume_return / config.minimum_resume_return
                if config.minimum_resume_return > 0.0
                else 1.0
            ),
        )
        output.append(
            NextFamilySignal(
                entry=entry,
                opposite=opposite,
                signed_strength=max(-4.0, min(4.0, strength)),
            )
        )
    return tuple(output)


def breakout_retest_signals(
    candles: Sequence[Candle],
    config: BreakoutRetestConfig,
) -> tuple[NextFamilySignal, ...]:
    """Require a later fully closed retest bar; the breakout bar can never fill itself."""

    source = _validated_source_candles(candles)
    bars_5m = aggregate_closed_candles(source, interval_minutes=5)
    bars_15m = aggregate_closed_candles(source, interval_minutes=15)
    close_5m = tuple(bar.close_time_ms for bar in bars_5m)
    close_15m = tuple(bar.close_time_ms for bar in bars_15m)
    output: list[NextFamilySignal] = []
    last_processed_5m_open: int | None = None
    pending_level: float | None = None
    pending_breakout_open: int | None = None
    pending_wait = 0
    active_level: float | None = None
    tolerance = config.retest_tolerance_bps / 10_000.0

    for candle in source:
        timestamp = candle.open_time_ms
        if not _decision_boundary(timestamp, 5):
            output.append(NextFamilySignal())
            continue
        known_5m = _closed_before(bars_5m, close_5m, timestamp)
        if not known_5m:
            output.append(NextFamilySignal())
            continue
        latest = known_5m[-1]
        if latest.open_time_ms == last_processed_5m_open:
            output.append(NextFamilySignal())
            continue
        last_processed_5m_open = latest.open_time_ms

        entry = False
        opposite = False
        strength = 0.0
        if pending_level is not None and pending_breakout_open is not None:
            if latest.open_time_ms > pending_breakout_open:
                pending_wait += 1
                if config.side == 1:
                    touched = latest.low <= pending_level * (1.0 + tolerance)
                    reclaimed = latest.close >= pending_level
                else:
                    touched = latest.high >= pending_level * (1.0 - tolerance)
                    reclaimed = latest.close <= pending_level
                if touched and reclaimed:
                    entry = True
                    active_level = pending_level
                    distance_bps = abs(latest.close / pending_level - 1.0) * 10_000.0
                    strength = 1.0 + distance_bps / max(config.retest_tolerance_bps, 1.0)
                    pending_level = None
                    pending_breakout_open = None
                    pending_wait = 0
                elif pending_wait >= config.max_retest_wait_5m:
                    pending_level = None
                    pending_breakout_open = None
                    pending_wait = 0

        if active_level is not None:
            directional = float(config.side) * (latest.close / active_level - 1.0)
            opposite = directional < -tolerance
            if opposite:
                active_level = None

        if pending_level is None and not entry:
            known_15m = _closed_before(bars_15m, close_15m, latest.open_time_ms)
            if len(known_15m) >= config.range_lookback_15m:
                prior_range = known_15m[-config.range_lookback_15m :]
                boundary = (
                    max(bar.high for bar in prior_range)
                    if config.side == 1
                    else min(bar.low for bar in prior_range)
                )
                breakout_bps = (
                    float(config.side) * (latest.close / boundary - 1.0) * 10_000.0
                )
                if breakout_bps >= config.minimum_breakout_bps:
                    pending_level = boundary
                    pending_breakout_open = latest.open_time_ms
                    pending_wait = 0
                    strength = max(strength, breakout_bps / max(config.minimum_breakout_bps, 1.0))

        output.append(
            NextFamilySignal(
                entry=entry,
                opposite=opposite,
                signed_strength=max(-4.0, min(4.0, strength)),
            )
        )
    return tuple(output)


def _path_efficiency(bars: Sequence[Candle]) -> float:
    if not bars:
        return 0.0
    points = [bars[0].open, *(bar.close for bar in bars)]
    path = sum(abs(right - left) for left, right in zip(points, points[1:], strict=False))
    if path <= 0.0:
        return 0.0
    displacement = abs(points[-1] - points[0])
    return min(1.0, displacement / path)


def path_efficiency_signals(
    candles: Sequence[Candle],
    config: PathEfficiencyConfig,
) -> tuple[NextFamilySignal, ...]:
    source = _validated_source_candles(candles)
    bars_15m = aggregate_closed_candles(source, interval_minutes=15)
    close_15m = tuple(bar.close_time_ms for bar in bars_15m)
    output: list[NextFamilySignal] = []

    for candle in source:
        timestamp = candle.open_time_ms
        if not _decision_boundary(timestamp, 15):
            output.append(NextFamilySignal())
            continue
        known = _closed_before(bars_15m, close_15m, timestamp)
        if len(known) < config.lookback_15m:
            output.append(NextFamilySignal())
            continue
        window = known[-config.lookback_15m :]
        directional_return = _directional_return(window, config.side)
        efficiency = _path_efficiency(window)
        entry = (
            directional_return >= config.minimum_directional_return
            and efficiency >= config.minimum_efficiency
        )
        opposite = directional_return <= -config.minimum_directional_return
        strength = min(
            directional_return / config.minimum_directional_return,
            efficiency / config.minimum_efficiency,
        )
        output.append(
            NextFamilySignal(
                entry=entry,
                opposite=opposite,
                signed_strength=max(-4.0, min(4.0, strength)),
            )
        )
    return tuple(output)


def _validate_orderflow_alignment(
    source: Sequence[Candle],
    rows: Sequence[OrderFlowFeatureRow],
) -> tuple[OrderFlowFeatureRow, ...]:
    data = tuple(rows)
    if len(data) != len(source):
        raise ValueError("next-family candles/orderflow rows must have identical lengths")
    for candle, row in zip(source, data, strict=True):
        if row.candle.open_time_ms != candle.open_time_ms:
            raise ValueError("next-family orderflow rows are not time-aligned")
        if row.footprint_available_at_ms > candle.open_time_ms:
            raise ValueError("next-family orderflow feature is not causal at candle open")
    return data


def _contiguous_slice(
    timestamps: Sequence[int],
    *,
    end_index_exclusive: int,
    count: int,
) -> tuple[int, int] | None:
    start = end_index_exclusive - count
    if start < 0:
        return None
    for index in range(start + 1, end_index_exclusive):
        if timestamps[index] - timestamps[index - 1] != SOURCE_STEP_MS:
            return None
    return start, end_index_exclusive


def _flow_ratio(rows: Sequence[OrderFlowFeatureRow]) -> float:
    total = sum(row.of_buy_volume + row.of_sell_volume for row in rows)
    if total <= 0.0:
        return 0.0
    return sum(row.of_delta for row in rows) / total


def low_turnover_flow_persistence_signals(
    candles: Sequence[Candle],
    rows: Sequence[OrderFlowFeatureRow],
    config: LowTurnoverFlowPersistenceConfig,
) -> tuple[NextFamilySignal, ...]:
    source = _validated_source_candles(candles)
    flow = _validate_orderflow_alignment(source, rows)
    timestamps = tuple(candle.open_time_ms for candle in source)
    output: list[NextFamilySignal] = []

    for index, candle in enumerate(source):
        if not _decision_boundary(candle.open_time_ms, 15):
            output.append(NextFamilySignal())
            continue
        short_bounds = _contiguous_slice(
            timestamps,
            end_index_exclusive=index + 1,
            count=config.short_flow_lookback_minutes,
        )
        long_bounds = _contiguous_slice(
            timestamps,
            end_index_exclusive=index + 1,
            count=config.long_flow_lookback_minutes,
        )
        price_bounds = _contiguous_slice(
            timestamps,
            end_index_exclusive=index,
            count=config.price_lookback_minutes,
        )
        if short_bounds is None or long_bounds is None or price_bounds is None:
            output.append(NextFamilySignal())
            continue

        short_ratio = _flow_ratio(flow[slice(*short_bounds)])
        long_ratio = _flow_ratio(flow[slice(*long_bounds)])
        price_window = source[slice(*price_bounds)]
        price_return = _directional_return(price_window, config.side)
        directional_short = float(config.side) * short_ratio
        directional_long = float(config.side) * long_ratio
        entry = (
            directional_short >= config.minimum_short_flow_ratio
            and directional_long >= config.minimum_long_flow_ratio
            and price_return >= config.minimum_directional_price_return
        )
        opposite = directional_long <= -config.minimum_long_flow_ratio
        price_strength = (
            price_return / config.minimum_directional_price_return
            if config.minimum_directional_price_return > 0.0
            else 1.0
        )
        strength = min(
            directional_short / config.minimum_short_flow_ratio,
            directional_long / config.minimum_long_flow_ratio,
            price_strength,
        )
        output.append(
            NextFamilySignal(
                entry=entry,
                opposite=opposite,
                signed_strength=max(-4.0, min(4.0, strength)),
            )
        )
    return tuple(output)


def _first_evaluation_index(candles: Sequence[Candle], trade_start_time_ms: int | None) -> int:
    if trade_start_time_ms is None:
        return 0
    for index, candle in enumerate(candles):
        if candle.open_time_ms >= trade_start_time_ms:
            return index
    raise ValueError("trade_start_time_ms is after the available next-family candles")


def _marked_equity(
    *,
    basis: float,
    quantity: float,
    side: int,
    entry_price: float,
    mark_price: float,
) -> float:
    return basis + float(side) * quantity * (mark_price - entry_price)


def run_next_family_backtest(
    candles: Sequence[Candle],
    signals: Sequence[NextFamilySignal],
    policy: NextExecutionPolicy,
    *,
    trade_start_time_ms: int | None = None,
) -> bt.BacktestResult:
    """Execute signals at the current one-minute open using information available by that open."""

    source = _validated_source_candles(candles)
    if len(signals) != len(source):
        raise ValueError("next-family signal vector length does not match source candles")
    evaluation_index = _first_evaluation_index(source, trade_start_time_ms)
    evaluation_bars = list(source[evaluation_index:])
    if not evaluation_bars:
        raise ValueError("next-family evaluation has no bars")

    fee_rate = policy.fee_bps / 10_000.0
    slippage_rate = policy.slippage_bps / 10_000.0
    cash = policy.initial_cash
    quantity = 0.0
    position_basis = 0.0
    entry_equity = 0.0
    entry_price = 0.0
    entry_time_ms = 0
    next_entry_time_ms = evaluation_bars[0].open_time_ms
    total_cost = 0.0
    trades: list[bt.ClosedTrade] = []
    equity_curve = [cash]
    bar_returns: list[float] = []
    previous_equity = cash
    exposed_bars = 0
    evaluated_bars = 0

    for index in range(evaluation_index, len(source)):
        bar = source[index]
        signal = signals[index]
        if quantity == 0.0:
            if signal.entry and bar.open_time_ms >= next_entry_time_ms and cash > 0.0:
                entry_equity = cash
                entry_price = bar.open * (1.0 + float(policy.side) * slippage_rate)
                entry_fee = cash * fee_rate
                entry_slippage = cash * slippage_rate
                total_cost += entry_fee + entry_slippage
                position_basis = cash - entry_fee
                quantity = position_basis / entry_price
                entry_time_ms = bar.open_time_ms
                cash = 0.0
        else:
            held_minutes = max(0, (bar.open_time_ms - entry_time_ms) // SOURCE_STEP_MS)
            signal_exit = held_minutes >= policy.minimum_hold_minutes and signal.opposite
            forced_exit = held_minutes >= policy.max_hold_minutes
            if signal_exit or forced_exit:
                exit_price = bar.open * (1.0 - float(policy.side) * slippage_rate)
                gross_equity = _marked_equity(
                    basis=position_basis,
                    quantity=quantity,
                    side=policy.side,
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
                        exit_time_ms=bar.open_time_ms,
                        entry_price=entry_price,
                        exit_price=exit_price,
                        net_return=cash / entry_equity - 1.0,
                        pnl=cash - entry_equity,
                    )
                )
                quantity = 0.0
                position_basis = 0.0
                next_entry_time_ms = bar.open_time_ms + policy.cooldown_minutes * SOURCE_STEP_MS

        if quantity > 0.0:
            mark_equity = max(
                _marked_equity(
                    basis=position_basis,
                    quantity=quantity,
                    side=policy.side,
                    entry_price=entry_price,
                    mark_price=bar.close,
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
        final_bar = source[-1]
        exit_price = final_bar.close * (1.0 - float(policy.side) * slippage_rate)
        gross_equity = _marked_equity(
            basis=position_basis,
            quantity=quantity,
            side=policy.side,
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
    benchmark_return, benchmark_drawdown = bt._buy_and_hold_metrics(evaluation_bars, policy)
    total_return = final_equity / policy.initial_cash - 1.0

    return bt.BacktestResult(
        initial_cash=policy.initial_cash,
        final_equity=final_equity,
        total_return=total_return,
        annualized_return=bt._annualized_return(policy.initial_cash, final_equity, evaluation_bars),
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


def execute_next_family(
    *,
    family_id: str,
    parameters: Mapping[str, object],
    candles: Sequence[Candle],
    orderflow_rows: Sequence[OrderFlowFeatureRow] = (),
    trade_start_time_ms: int | None = None,
) -> NextFamilyExecution:
    if family_id not in NEXT_FAMILY_IDS:
        raise ValueError(f"unsupported next Strategy Factory family: {family_id}")
    params: dict[str, Any] = dict(parameters)

    if family_id == "mtf_trend_pullback_v1":
        config = MtfTrendPullbackConfig(**params)
        signals = mtf_trend_pullback_signals(candles, config)
        policy = config.execution_policy
    elif family_id == "breakout_retest_entry_v1":
        config = BreakoutRetestConfig(**params)
        signals = breakout_retest_signals(candles, config)
        policy = config.execution_policy
    elif family_id == "path_efficiency_persistence_v1":
        config = PathEfficiencyConfig(**params)
        signals = path_efficiency_signals(candles, config)
        policy = config.execution_policy
    else:
        config = LowTurnoverFlowPersistenceConfig(**params)
        signals = low_turnover_flow_persistence_signals(candles, orderflow_rows, config)
        policy = config.execution_policy

    result = run_next_family_backtest(
        candles,
        signals,
        policy,
        trade_start_time_ms=trade_start_time_ms,
    )
    return NextFamilyExecution(result=result, signals=signals, side=policy.side)
