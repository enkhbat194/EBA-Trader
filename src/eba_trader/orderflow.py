from __future__ import annotations

import math
from dataclasses import dataclass
from decimal import ROUND_FLOOR, Decimal
from enum import StrEnum


class AggressorSide(StrEnum):
    BUY = "buy"
    SELL = "sell"


@dataclass(frozen=True, slots=True)
class TradeEvent:
    timestamp_ms: int
    price: float
    quantity: float
    aggressor: AggressorSide

    def __post_init__(self) -> None:
        if self.timestamp_ms < 0:
            raise ValueError("timestamp_ms must be >= 0")
        if not math.isfinite(self.price) or self.price <= 0:
            raise ValueError("price must be finite and > 0")
        if not math.isfinite(self.quantity) or self.quantity <= 0:
            raise ValueError("quantity must be finite and > 0")


@dataclass(frozen=True, slots=True)
class PriceLevelFlow:
    price: float
    buy_volume: float
    sell_volume: float

    @property
    def total_volume(self) -> float:
        return self.buy_volume + self.sell_volume

    @property
    def delta(self) -> float:
        return self.buy_volume - self.sell_volume


@dataclass(frozen=True, slots=True)
class DiagonalImbalanceStacks:
    buy_levels: int
    sell_levels: int

    @property
    def signed_score(self) -> int:
        if self.buy_levels > self.sell_levels:
            return self.buy_levels
        if self.sell_levels > self.buy_levels:
            return -self.sell_levels
        return 0


@dataclass(frozen=True, slots=True)
class FootprintFeatures:
    start_ms: int
    end_ms: int
    buy_volume: float
    sell_volume: float
    delta: float
    delta_ratio: float
    total_volume: float
    trade_count: int
    poc_price: float | None
    levels: tuple[PriceLevelFlow, ...]


class TradeFlowAggregator:
    """Deterministic closed-window footprint aggregation from executed trades."""

    def __init__(self, *, price_bucket: float) -> None:
        if not math.isfinite(price_bucket) or price_bucket <= 0:
            raise ValueError("price_bucket must be finite and > 0")
        self.price_bucket = price_bucket
        self._bucket = Decimal(str(price_bucket))

    def aggregate(
        self,
        events: list[TradeEvent] | tuple[TradeEvent, ...],
        *,
        start_ms: int,
        end_ms: int,
    ) -> FootprintFeatures:
        if start_ms < 0 or end_ms <= start_ms:
            raise ValueError("invalid aggregation window")
        selected = [event for event in events if start_ms <= event.timestamp_ms < end_ms]
        selected.sort(
            key=lambda event: (
                event.timestamp_ms,
                event.price,
                event.quantity,
                event.aggressor.value,
            )
        )

        level_map: dict[Decimal, list[float]] = {}
        buy_volume = 0.0
        sell_volume = 0.0
        for event in selected:
            level = self._bucket_price(event.price)
            flow = level_map.setdefault(level, [0.0, 0.0])
            if event.aggressor is AggressorSide.BUY:
                flow[0] += event.quantity
                buy_volume += event.quantity
            else:
                flow[1] += event.quantity
                sell_volume += event.quantity

        levels = tuple(
            PriceLevelFlow(price=float(price), buy_volume=flow[0], sell_volume=flow[1])
            for price, flow in sorted(level_map.items())
        )
        total_volume = buy_volume + sell_volume
        delta = buy_volume - sell_volume
        delta_ratio = delta / total_volume if total_volume > 0 else 0.0
        poc_price = None
        if levels:
            poc_price = max(levels, key=lambda level: (level.total_volume, -level.price)).price

        return FootprintFeatures(
            start_ms=start_ms,
            end_ms=end_ms,
            buy_volume=buy_volume,
            sell_volume=sell_volume,
            delta=delta,
            delta_ratio=delta_ratio,
            total_volume=total_volume,
            trade_count=len(selected),
            poc_price=poc_price,
            levels=levels,
        )

    def _bucket_price(self, price: float) -> Decimal:
        value = Decimal(str(price))
        steps = (value / self._bucket).to_integral_value(rounding=ROUND_FLOOR)
        return steps * self._bucket


def _max_true_run(flags: tuple[bool, ...]) -> int:
    best = 0
    current = 0
    for flag in flags:
        if flag:
            current += 1
            best = max(best, current)
        else:
            current = 0
    return best


def diagonal_imbalance_stacks(
    levels: tuple[PriceLevelFlow, ...] | list[PriceLevelFlow],
    *,
    ratio_threshold: float = 3.0,
    min_volume: float = 0.0,
) -> DiagonalImbalanceStacks:
    """Return consecutive executed-flow diagonal imbalance levels.

    Buy imbalance compares aggressive buy volume at a price level with aggressive sell
    volume one bucket lower. Sell imbalance mirrors that comparison against aggressive
    buy volume one bucket higher. Both compared cells must contain more than
    ``min_volume`` so an empty diagonal cell cannot manufacture an infinite imbalance.
    This is executed-trade footprint evidence only; it is not resting LOB liquidity.
    """

    if not math.isfinite(ratio_threshold) or ratio_threshold <= 1.0:
        raise ValueError("ratio_threshold must be finite and > 1")
    if not math.isfinite(min_volume) or min_volume < 0.0:
        raise ValueError("min_volume must be finite and >= 0")

    ordered = tuple(sorted(levels, key=lambda level: level.price))
    if len({level.price for level in ordered}) != len(ordered):
        raise ValueError("price levels must be unique")
    for level in ordered:
        if (
            not math.isfinite(level.price)
            or not math.isfinite(level.buy_volume)
            or not math.isfinite(level.sell_volume)
            or level.buy_volume < 0.0
            or level.sell_volume < 0.0
        ):
            raise ValueError("price-level flow must be finite and non-negative")

    buy_flags = tuple(
        upper.buy_volume > min_volume
        and lower.sell_volume > min_volume
        and upper.buy_volume >= ratio_threshold * lower.sell_volume
        for lower, upper in zip(ordered, ordered[1:], strict=False)
    )
    sell_flags = tuple(
        lower.sell_volume > min_volume
        and upper.buy_volume > min_volume
        and lower.sell_volume >= ratio_threshold * upper.buy_volume
        for lower, upper in zip(ordered, ordered[1:], strict=False)
    )
    return DiagonalImbalanceStacks(
        buy_levels=_max_true_run(buy_flags),
        sell_levels=_max_true_run(sell_flags),
    )


def cumulative_delta(
    windows: list[FootprintFeatures] | tuple[FootprintFeatures, ...],
) -> tuple[float, ...]:
    running = 0.0
    output: list[float] = []
    previous_end: int | None = None
    for window in windows:
        if previous_end is not None and window.start_ms < previous_end:
            raise ValueError("footprint windows must be ordered and non-overlapping")
        running += window.delta
        output.append(running)
        previous_end = window.end_ms
    return tuple(output)
