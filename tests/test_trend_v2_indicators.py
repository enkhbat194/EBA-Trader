from __future__ import annotations

from dataclasses import replace

import pytest

from eba_trader.history import Candle
from eba_trader.trend_v2 import (
    FIFTEEN_MINUTES_MS,
    directional_indicators,
    prepare_trend_v2_features,
    resample_complete_hours,
    rolling_prior_median,
)
from eba_trader.trend_v2_policy import BASELINE_TREND_V2_CONFIG


def _bar(index: int, price: float, *, start_ms: int = 0) -> Candle:
    open_time = start_ms + index * FIFTEEN_MINUTES_MS
    return Candle(
        open_time_ms=open_time,
        open=price,
        high=price + 1.0,
        low=price - 1.0,
        close=price + 0.5,
        volume=1.0,
        close_time_ms=open_time + FIFTEEN_MINUTES_MS - 1,
        quote_volume=price,
        trade_count=1,
    )


def test_resample_uses_exactly_four_utc_aligned_bars() -> None:
    bars = [_bar(index, 100.0 + index) for index in range(7)]

    hourly = resample_complete_hours(bars)

    assert len(hourly) == 1
    assert hourly[0].open_time_ms == 0
    assert hourly[0].open == 100.0
    assert hourly[0].close == 103.5
    assert hourly[0].high == 104.0
    assert hourly[0].low == 99.0


def test_rolling_median_excludes_current_value() -> None:
    assert rolling_prior_median([1.0, 3.0, 2.0, 100.0], 3) == (
        None,
        None,
        None,
        2.0,
    )


def test_wilder_directional_indicators_are_causal_and_trend_positive() -> None:
    bars = [_bar(index * 4, 100.0 + index * 2.0) for index in range(12)]
    indicators = directional_indicators(bars, period=3)

    assert indicators.adx[3] is None
    assert indicators.adx[4] == pytest.approx(100.0)
    assert indicators.plus_di[-1] > indicators.minus_di[-1]
    assert indicators.adx[-1] == pytest.approx(100.0)


def test_latest_hour_advances_only_after_hour_is_complete() -> None:
    config = replace(
        BASELINE_TREND_V2_CONFIG,
        hour_fast_ema=2,
        hour_slow_ema=3,
        hour_slope_lookback=1,
        adx_period=2,
        atr_period=2,
        volatility_median_bars=3,
        donchian_lookback=2,
        signal_fast_ema=2,
        signal_slow_ema=3,
        signal_slope_lookback=1,
    )
    features = prepare_trend_v2_features(
        [_bar(index, 100.0 + index) for index in range(12)],
        config,
    )

    assert features.latest_hour_index[2] is None
    assert features.latest_hour_index[3] == 0
    assert features.latest_hour_index[6] == 0
    assert features.latest_hour_index[7] == 1


def test_source_gap_resets_complete_hour_streak() -> None:
    bars = [_bar(index, 100.0 + index) for index in range(4)]
    bars.extend(_bar(index, 100.0 + index) for index in range(8, 24))
    config = replace(
        BASELINE_TREND_V2_CONFIG,
        hour_fast_ema=2,
        hour_slow_ema=3,
        hour_slope_lookback=1,
        adx_period=2,
        atr_period=2,
        volatility_median_bars=3,
        donchian_lookback=2,
        signal_fast_ema=2,
        signal_slow_ema=3,
        signal_slope_lookback=1,
    )

    features = prepare_trend_v2_features(bars, config)

    assert len(features.hourly_bars) == 5
    assert features.complete_hour_streak[-1] == 4
