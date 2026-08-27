from __future__ import annotations

import math
from dataclasses import dataclass
from decimal import Decimal

from .orderflow import PriceLevelFlow
from .orderflow_dataset import AggregateTradeRecord


@dataclass(frozen=True, slots=True)
class ExecutedFlowResponse:
    """Bounded reversal-oriented scores derived only from completed executed trades.

    Positive scores support a bullish/long interpretation; negative scores support a
    bearish interpretation. These are executed-flow proxies, not direct observations of
    resting limit-order-book liquidity.
    """

    absorption: float
    exhaustion: float


def _clamp_unit(value: float) -> float:
    return max(-1.0, min(1.0, value))


def executed_flow_response(
    records: tuple[AggregateTradeRecord, ...] | list[AggregateTradeRecord],
    levels: tuple[PriceLevelFlow, ...] | list[PriceLevelFlow],
    *,
    start_ms: int,
    end_ms: int,
    price_step: float,
) -> ExecutedFlowResponse:
    """Measure pressure-vs-price response and edge-flow depletion for one closed window.

    Absorption proxy:
    - aggressive sell pressure that fails to produce proportional downward progress is
      positive (bullish seller absorption proxy);
    - aggressive buy pressure that fails to produce proportional upward progress is
      negative (bearish buyer absorption proxy).

    Exhaustion proxy:
    - after net downward progress, depleted aggressive sell volume at the exact lowest
      price bucket versus the adjacent bucket is positive;
    - after net upward progress, depleted aggressive buy volume at the exact highest
      bucket versus the adjacent bucket is negative.

    Windows with fewer than two trades, no usable directional path, missing adjacent edge
    buckets, or zero reference flow return a neutral zero for the unavailable component.
    Input order does not affect the result because aggregate-trade IDs define sequence.
    """

    if start_ms < 0 or end_ms <= start_ms:
        raise ValueError("invalid executed-flow response window")
    if not math.isfinite(price_step) or price_step <= 0.0:
        raise ValueError("price_step must be finite and > 0")

    selected = sorted(
        (record for record in records if start_ms <= record.timestamp_ms < end_ms),
        key=lambda record: record.aggregate_trade_id,
    )
    if len({record.aggregate_trade_id for record in selected}) != len(selected):
        raise ValueError("aggregate trade IDs must be unique inside response window")
    if len(selected) < 2:
        return ExecutedFlowResponse(absorption=0.0, exhaustion=0.0)

    total_volume = sum(record.quantity for record in selected)
    if not math.isfinite(total_volume) or total_volume <= 0.0:
        raise ValueError("executed-flow response requires positive finite volume")
    buy_volume = sum(
        record.quantity for record in selected if record.aggressor.value == "buy"
    )
    sell_volume = total_volume - buy_volume
    pressure = (buy_volume - sell_volume) / total_volume

    first_price = selected[0].price
    last_price = selected[-1].price
    low_price = min(record.price for record in selected)
    high_price = max(record.price for record in selected)
    price_range = high_price - low_price
    progress = 0.0
    if price_range > 0.0:
        progress = _clamp_unit((last_price - first_price) / price_range)

    if pressure > 0.0:
        aligned_progress = max(0.0, progress)
    elif pressure < 0.0:
        aligned_progress = max(0.0, -progress)
    else:
        aligned_progress = 0.0
    absorption = _clamp_unit(-pressure * (1.0 - min(aligned_progress, 1.0)))

    ordered_levels = tuple(sorted(levels, key=lambda level: level.price))
    if len({level.price for level in ordered_levels}) != len(ordered_levels):
        raise ValueError("price levels must be unique")
    for level in ordered_levels:
        if (
            not math.isfinite(level.price)
            or not math.isfinite(level.buy_volume)
            or not math.isfinite(level.sell_volume)
            or level.buy_volume < 0.0
            or level.sell_volume < 0.0
        ):
            raise ValueError("price-level flow must be finite and non-negative")

    step = Decimal(str(price_step))
    by_price = {Decimal(str(level.price)): level for level in ordered_levels}
    exhaustion = 0.0
    if progress < 0.0 and ordered_levels:
        low = ordered_levels[0]
        above = by_price.get(Decimal(str(low.price)) + step)
        if above is not None and above.sell_volume > 0.0 and low.sell_volume < above.sell_volume:
            depletion = (above.sell_volume - low.sell_volume) / above.sell_volume
            exhaustion = depletion * (above.sell_volume / total_volume)
    elif progress > 0.0 and ordered_levels:
        high = ordered_levels[-1]
        below = by_price.get(Decimal(str(high.price)) - step)
        if below is not None and below.buy_volume > 0.0 and high.buy_volume < below.buy_volume:
            depletion = (below.buy_volume - high.buy_volume) / below.buy_volume
            exhaustion = -depletion * (below.buy_volume / total_volume)

    return ExecutedFlowResponse(
        absorption=_clamp_unit(absorption),
        exhaustion=_clamp_unit(exhaustion),
    )
