from __future__ import annotations

from dataclasses import replace

import pytest

import eba_trader.trend_v2 as trend_v2
from eba_trader.history import Candle
from eba_trader.trend_v2 import TrendV2Features, _entry_conditions, run_trend_v2_backtest
from eba_trader.trend_v2_policy import BASELINE_TREND_V2_CONFIG


def _bar(index: int, *, open_price: float, high: float, low: float, close: float) -> Candle:
    open_time = index * trend_v2.FIFTEEN_MINUTES_MS
    return Candle(
        open_time_ms=open_time,
        open=open_price,
        high=high,
        low=low,
        close=close,
        volume=1.0,
        close_time_ms=open_time + trend_v2.FIFTEEN_MINUTES_MS - 1,
        quote_volume=100.0,
        trade_count=1,
    )


def _small_config(**changes: float | int):
    return replace(
        BASELINE_TREND_V2_CONFIG,
        hour_fast_ema=2,
        hour_slow_ema=3,
        hour_slope_lookback=1,
        adx_period=2,
        atr_period=2,
        volatility_median_bars=3,
        donchian_lookback=3,
        signal_fast_ema=2,
        signal_slow_ema=3,
        signal_slope_lookback=1,
        complete_hours_after_gap=1,
        fee_bps=0.0,
        slippage_bps=0.0,
        **changes,
    )


def _eligible_features() -> tuple[TrendV2Features, object]:
    config = _small_config()
    bars = (
        _bar(0, open_price=99.0, high=100.0, low=98.0, close=99.0),
        _bar(1, open_price=99.0, high=100.0, low=98.0, close=99.0),
        _bar(2, open_price=99.0, high=100.0, low=98.0, close=99.0),
        _bar(3, open_price=100.0, high=101.0, low=99.0, close=100.0),
        _bar(4, open_price=101.0, high=103.0, low=100.0, close=102.0),
    )
    features = TrendV2Features(
        bars=bars,
        hourly_bars=(bars[0], replace(bars[0], close=110.0)),
        atr_15m=(1.0,) * 5,
        atr_pct_median=(0.01,) * 5,
        ema20_15m=(8.0, 8.0, 8.0, 9.0, 10.0),
        ema50_15m=(7.0,) * 5,
        ema50_1h=(99.0, 100.0),
        ema200_1h=(89.0, 90.0),
        plus_di_1h=(30.0, 30.0),
        minus_di_1h=(10.0, 10.0),
        adx_1h=(25.0, 25.0),
        latest_hour_index=(1,) * 5,
        complete_hour_streak=(4,) * 5,
        invalid_hour_streak=(0, 0),
        contiguous_15m_streak=(1, 2, 3, 4, 5),
    )
    return features, config


def test_entry_requires_fresh_breakout_and_all_filters() -> None:
    features, config = _eligible_features()

    ready, eligible = _entry_conditions(features, 4, config, filters_enabled=True)

    assert ready is True
    assert eligible is True
    weak_adx = replace(features, adx_1h=(25.0, 24.9))
    assert _entry_conditions(weak_adx, 4, config, filters_enabled=True) == (True, False)
    assert _entry_conditions(weak_adx, 4, config, filters_enabled=False) == (True, True)


def _execution_features(bars: tuple[Candle, ...], atr_value: float) -> TrendV2Features:
    size = len(bars)
    return TrendV2Features(
        bars=bars,
        hourly_bars=(bars[0],),
        atr_15m=(atr_value,) * size,
        atr_pct_median=(0.01,) * size,
        ema20_15m=(90.0,) * size,
        ema50_15m=(80.0,) * size,
        ema50_1h=(80.0,),
        ema200_1h=(70.0,),
        plus_di_1h=(30.0,),
        minus_di_1h=(10.0,),
        adx_1h=(30.0,),
        latest_hour_index=(0,) * size,
        complete_hour_streak=(4,) * size,
        invalid_hour_streak=(0,),
        contiguous_15m_streak=tuple(range(1, size + 1)),
    )


def _patch_single_signal(monkeypatch, bars: tuple[Candle, ...], atr_value: float) -> None:
    monkeypatch.setattr(
        trend_v2,
        "prepare_trend_v2_features",
        lambda supplied, config: _execution_features(tuple(supplied), atr_value),
    )
    monkeypatch.setattr(trend_v2, "_features_ready", lambda features, index, config: True)
    monkeypatch.setattr(
        trend_v2,
        "_entry_conditions",
        lambda features, index, config, filters_enabled: (True, index == 0),
    )


def test_entry_is_next_open_and_trailing_stop_only_ratchets(monkeypatch) -> None:
    bars = (
        _bar(0, open_price=100.0, high=101.0, low=99.0, close=100.0),
        _bar(1, open_price=100.0, high=102.0, low=99.5, close=101.0),
        _bar(2, open_price=101.0, high=101.5, low=98.0, close=99.0),
        _bar(3, open_price=99.0, high=100.0, low=98.0, close=99.0),
    )
    _patch_single_signal(monkeypatch, bars, 1.0)

    result = run_trend_v2_backtest(bars, _small_config())

    assert result.trade_count == 1
    assert result.trades[0].trade.entry_time_ms == bars[1].open_time_ms
    assert result.trades[0].trade.entry_price == 100.0
    assert result.trades[0].trade.exit_price == 99.0
    assert result.trades[0].exit_reason == "stop"


def test_favorable_gap_cancels_pending_entry(monkeypatch) -> None:
    bars = (
        _bar(0, open_price=100.0, high=101.0, low=99.0, close=100.0),
        _bar(1, open_price=100.6, high=102.0, low=100.0, close=101.0),
        _bar(2, open_price=101.0, high=102.0, low=100.0, close=101.0),
    )
    _patch_single_signal(monkeypatch, bars, 1.0)

    result = run_trend_v2_backtest(bars, _small_config())

    assert result.trade_count == 0


def test_risk_size_and_entry_notional_caps_are_hard(monkeypatch) -> None:
    bars = (
        _bar(0, open_price=100.0, high=100.1, low=99.9, close=100.0),
        _bar(1, open_price=100.0, high=101.0, low=99.8, close=100.5),
        _bar(2, open_price=100.5, high=101.0, low=100.0, close=100.5),
    )
    _patch_single_signal(monkeypatch, bars, 0.1)

    result = run_trend_v2_backtest(bars, _small_config(), risk_sized=True)

    assert result.trade_count == 1
    assert result.max_notional_fraction == pytest.approx(0.50)
    assert result.max_planned_risk_fraction <= 0.0035 + 1e-12
