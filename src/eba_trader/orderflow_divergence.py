from __future__ import annotations

import math
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class PriceDeltaDivergence:
    """Bounded executed-flow divergence scores for one already-closed price bar.

    Positive ``signed_score`` is bullish, negative is bearish. The score is a research
    proxy derived from price extremes and executed-trade Delta ratio; it is not a claim
    about resting order-book liquidity or hidden institutional intent.
    """

    bullish: float
    bearish: float
    signed_score: float


def _finite(value: float, *, name: str) -> float:
    result = float(value)
    if not math.isfinite(result):
        raise ValueError(f"{name} must be finite")
    return result


def _price_pair(high: float, low: float, *, label: str) -> tuple[float, float]:
    checked_high = _finite(high, name=f"{label} high")
    checked_low = _finite(low, name=f"{label} low")
    if checked_high <= 0.0 or checked_low <= 0.0 or checked_high < checked_low:
        raise ValueError(f"{label} price range is invalid")
    return checked_high, checked_low


def _delta_ratio(value: float, *, name: str) -> float:
    result = _finite(value, name=name)
    if not -1.0 <= result <= 1.0:
        raise ValueError(f"{name} must be between -1 and 1")
    return result


def _volume(value: float, *, name: str) -> float:
    result = _finite(value, name=name)
    if result < 0.0:
        raise ValueError(f"{name} must be >= 0")
    return result


def price_delta_divergence(
    *,
    current_high: float,
    current_low: float,
    current_delta_ratio: float,
    current_total_volume: float,
    reference_highs: tuple[float, ...] | list[float],
    reference_lows: tuple[float, ...] | list[float],
    reference_delta_ratios: tuple[float, ...] | list[float],
    reference_total_volumes: tuple[float, ...] | list[float],
    min_total_volume: float = 0.0,
) -> PriceDeltaDivergence:
    """Measure causal price/Delta non-confirmation against already-closed references.

    Bullish divergence requires the current *closed* price bar to make a strict new low
    while its executed-flow Delta ratio is higher (less selling pressure) than the Delta
    ratio observed at the prior lowest reference price. Bearish divergence mirrors this:
    a strict new high with a lower Delta ratio than at the prior highest reference price.

    Only reference rows with total executed volume strictly above ``min_total_volume`` are
    eligible. The current row must also exceed that floor. Empty/insufficient eligible
    history returns neutral zero. If one outside bar makes both a new high and new low and
    both divergence conditions fire, the observation is ambiguous and returns neutral.

    Strength is the Delta-ratio gap normalized by its full possible range of two, so each
    directional score is bounded to [0, 1]. Reference order cannot change the result.
    """

    high, low = _price_pair(current_high, current_low, label="current")
    delta = _delta_ratio(current_delta_ratio, name="current_delta_ratio")
    volume = _volume(current_total_volume, name="current_total_volume")
    minimum = _volume(min_total_volume, name="min_total_volume")

    lengths = {
        len(reference_highs),
        len(reference_lows),
        len(reference_delta_ratios),
        len(reference_total_volumes),
    }
    if len(lengths) != 1:
        raise ValueError("reference divergence inputs must have equal lengths")
    if not reference_highs:
        return PriceDeltaDivergence(0.0, 0.0, 0.0)

    eligible: list[tuple[float, float, float]] = []
    for index, (ref_high, ref_low, ref_delta, ref_volume) in enumerate(
        zip(
            reference_highs,
            reference_lows,
            reference_delta_ratios,
            reference_total_volumes,
            strict=True,
        )
    ):
        checked_high, checked_low = _price_pair(
            ref_high,
            ref_low,
            label=f"reference[{index}]",
        )
        checked_delta = _delta_ratio(ref_delta, name=f"reference_delta_ratios[{index}]")
        checked_volume = _volume(ref_volume, name=f"reference_total_volumes[{index}]")
        if checked_volume > minimum:
            eligible.append((checked_high, checked_low, checked_delta))

    if volume <= minimum or not eligible:
        return PriceDeltaDivergence(0.0, 0.0, 0.0)

    prior_low = min(item[1] for item in eligible)
    prior_low_delta = min(item[2] for item in eligible if item[1] == prior_low)
    prior_high = max(item[0] for item in eligible)
    prior_high_delta = max(item[2] for item in eligible if item[0] == prior_high)

    bullish = 0.0
    if low < prior_low and delta > prior_low_delta:
        bullish = min(1.0, (delta - prior_low_delta) / 2.0)

    bearish = 0.0
    if high > prior_high and delta < prior_high_delta:
        bearish = min(1.0, (prior_high_delta - delta) / 2.0)

    if bullish > 0.0 and bearish > 0.0:
        return PriceDeltaDivergence(0.0, 0.0, 0.0)
    return PriceDeltaDivergence(
        bullish=bullish,
        bearish=bearish,
        signed_score=bullish if bullish > 0.0 else -bearish,
    )
