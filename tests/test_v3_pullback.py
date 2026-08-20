from __future__ import annotations

from dataclasses import replace

import pytest

import eba_trader.v3_pullback as v3
from eba_trader.history import Candle
from eba_trader.v3_pullback import (
    V3PullbackFeatures,
    _arm_eligible,
    _recovery_eligible,
    _source_ready,
    resample_complete_4h,
    rolling_prior_vwap,
    run_v3_pullback_backtest,
)
from eba_trader.v3_pullback_policy import BASELINE_V3_PULLBACK_CONFIG


def _bar(
    index: int,
    *,
    open_price: float = 100.0,
    high: float = 101.0,
    low: float = 99.0,
    close: float = 100.0,
    volume: float = 10.0,
) -> Candle:
    open_time = index * v3.FIFTEEN_MINUTES_MS
    return Candle(
        open_time_ms=open_time,
        open=open_price,
        high=high,
        low=low,
        close=close,
        volume=volume,
        close_time_ms=open_time + v3.FIFTEEN_MINUTES_MS - 1,
        quote_volume=volume * close,
        trade_count=1,
    )


def _small_config(**changes: float | int):
    return replace(
        BASELINE_V3_PULLBACK_CONFIG,
        regime_fast_ema_4h=2,
        regime_slow_ema_4h=3,
        regime_slope_lookback_4h=1,
        atr_period=2,
        rolling_vwap_bars=2,
        arm_lifetime_bars=2,
        recovery_high_lookback=1,
        complete_15m_after_gap=1,
        reentry_cooldown_bars=1,
        max_holding_bars=4,
        fee_bps=0.0,
        slippage_bps=0.0,
        **changes,
    )


def test_resample_complete_4h_requires_all_sixteen_15m_bars() -> None:
    bars = tuple(_bar(index, close=100.0 + index) for index in range(16))

    result = resample_complete_4h(bars)

    assert len(result) == 1
    assert result[0].open == bars[0].open
    assert result[0].close == bars[-1].close
    assert result[0].volume == pytest.approx(sum(bar.volume for bar in bars))
    assert resample_complete_4h(bars[:-1]) == ()


def test_rolling_prior_vwap_excludes_current_bar() -> None:
    bars = (
        _bar(0, high=101.0, low=99.0, close=100.0, volume=1.0),
        _bar(1, high=103.0, low=101.0, close=102.0, volume=3.0),
        _bar(2, high=1001.0, low=999.0, close=1000.0, volume=100.0),
    )

    values = rolling_prior_vwap(bars, 2)

    assert values[:2] == (None, None)
    expected = (100.0 * 1.0 + 102.0 * 3.0) / 4.0
    assert values[2] == pytest.approx(expected)


def _eligible_features(
    *,
    close: float = 99.0,
    volume: float = 10.0,
) -> tuple[V3PullbackFeatures, object]:
    config = _small_config()
    bars = (
        _bar(0, close=100.0),
        _bar(1, close=100.0),
        _bar(2, open_price=99.0, high=100.0, low=98.5, close=close, volume=volume),
        _bar(3, open_price=99.0, high=101.0, low=98.8, close=100.5, volume=volume),
    )
    four_hour_bars = (
        _bar(0, close=90.0),
        replace(
            _bar(16, close=110.0),
            open_time_ms=v3.FOUR_HOURS_MS,
            close_time_ms=2 * v3.FOUR_HOURS_MS - 1,
        ),
    )
    features = V3PullbackFeatures(
        bars=bars,
        four_hour_bars=four_hour_bars,
        atr_15m=(1.0,) * 4,
        prior_vwap_15m=(None, None, 100.0, 100.0),
        prior_median_volume_15m=(None, None, 10.0, 10.0),
        ema50_4h=(85.0, 100.0),
        ema200_4h=(80.0, 90.0),
        latest_4h_index=(1, 1, 1, 1),
        invalid_4h_streak=(0, 0),
        contiguous_15m_streak=(1, 2, 3, 4),
    )
    return features, config


def test_arm_requires_bounded_pullback_but_control_keeps_shock_veto() -> None:
    features, config = _eligible_features(close=99.0)

    assert _arm_eligible(features, 2, config, filters_enabled=True) is True

    shallow = replace(
        features,
        bars=features.bars[:2] + (replace(features.bars[2], close=99.5),) + features.bars[3:],
    )
    assert _arm_eligible(shallow, 2, config, filters_enabled=True) is False
    assert _arm_eligible(shallow, 2, config, filters_enabled=False) is True

    shock_bar = replace(features.bars[2], high=104.0, low=98.0, close=99.0)
    shock = replace(features, bars=features.bars[:2] + (shock_bar,) + features.bars[3:])
    assert _arm_eligible(shock, 2, config, filters_enabled=False) is False


def test_recovery_requires_local_high_reclaim_and_volume_filter() -> None:
    features, config = _eligible_features()

    assert _recovery_eligible(features, 3, config, filters_enabled=True) is True

    low_volume_bar = replace(features.bars[3], volume=9.0)
    low_volume = replace(features, bars=features.bars[:3] + (low_volume_bar,))
    assert _recovery_eligible(low_volume, 3, config, filters_enabled=True) is False
    assert _recovery_eligible(low_volume, 3, config, filters_enabled=False) is True


def test_source_ready_requires_post_gap_contiguous_rebuild() -> None:
    features, config = _eligible_features()
    config = replace(config, complete_15m_after_gap=3)
    gapped = replace(features, contiguous_15m_streak=(1, 2, 1, 2))

    assert _source_ready(gapped, 2, config) is False
    assert _source_ready(features, 2, config) is True


def _execution_features(bars: tuple[Candle, ...], atr_value: float) -> V3PullbackFeatures:
    size = len(bars)
    return V3PullbackFeatures(
        bars=bars,
        four_hour_bars=(bars[0],),
        atr_15m=(atr_value,) * size,
        prior_vwap_15m=(100.0,) * size,
        prior_median_volume_15m=(1.0,) * size,
        ema50_4h=(90.0,),
        ema200_4h=(80.0,),
        latest_4h_index=(0,) * size,
        invalid_4h_streak=(0,),
        contiguous_15m_streak=tuple(range(1, size + 1)),
    )


def _patch_single_setup(monkeypatch, bars: tuple[Candle, ...], atr_value: float) -> None:
    monkeypatch.setattr(
        v3,
        "prepare_v3_pullback_features",
        lambda supplied, config: _execution_features(tuple(supplied), atr_value),
    )
    monkeypatch.setattr(v3, "_features_ready", lambda features, index, config: True)
    monkeypatch.setattr(v3, "_bull_regime", lambda features, index, config: True)
    monkeypatch.setattr(
        v3,
        "_arm_eligible",
        lambda features, index, config, filters_enabled: index == 0,
    )
    monkeypatch.setattr(
        v3,
        "_recovery_eligible",
        lambda features, index, config, filters_enabled: index == 1,
    )


def test_entry_is_next_open_and_same_bar_stop_target_uses_stop_first(monkeypatch) -> None:
    bars = (
        _bar(0, open_price=100.0, high=100.5, low=99.0, close=99.5),
        _bar(1, open_price=99.5, high=101.0, low=99.2, close=100.5),
        _bar(2, open_price=100.5, high=105.0, low=98.0, close=103.0),
        _bar(3, open_price=103.0, high=104.0, low=102.0, close=103.0),
    )
    _patch_single_setup(monkeypatch, bars, 1.0)

    result = run_v3_pullback_backtest(bars, _small_config())

    assert result.trade_count == 1
    trade = result.trades[0]
    assert trade.trade.entry_time_ms == bars[2].open_time_ms
    assert trade.trade.entry_price == pytest.approx(100.5)
    assert trade.exit_reason == "stop"
    assert trade.trade.exit_price == pytest.approx(98.75)


def test_pending_entry_is_cancelled_when_source_health_breaks(monkeypatch) -> None:
    bars = (
        _bar(0, open_price=100.0, high=100.5, low=99.0, close=99.5),
        _bar(1, open_price=99.5, high=101.0, low=99.2, close=100.5),
        _bar(2, open_price=100.5, high=102.0, low=100.0, close=101.0),
        _bar(3, open_price=101.0, high=102.0, low=100.0, close=101.0),
    )
    _patch_single_setup(monkeypatch, bars, 1.0)
    monkeypatch.setattr(v3, "_source_ready", lambda features, index, config: index != 2)

    result = run_v3_pullback_backtest(bars, _small_config())

    assert result.trade_count == 0


def test_armed_setup_is_cancelled_immediately_on_source_gap(monkeypatch) -> None:
    bars = (
        _bar(0, close=99.0),
        _bar(1, close=99.0),
        _bar(2, close=101.0),
        _bar(3, close=101.0),
    )
    monkeypatch.setattr(
        v3,
        "prepare_v3_pullback_features",
        lambda supplied, config: _execution_features(tuple(supplied), 1.0),
    )
    monkeypatch.setattr(v3, "_features_ready", lambda features, index, config: True)
    monkeypatch.setattr(v3, "_bull_regime", lambda features, index, config: True)
    monkeypatch.setattr(
        v3,
        "_source_ready",
        lambda features, index, config: index != 1,
    )
    monkeypatch.setattr(
        v3,
        "_arm_eligible",
        lambda features, index, config, filters_enabled: index == 0,
    )
    monkeypatch.setattr(
        v3,
        "_recovery_eligible",
        lambda features, index, config, filters_enabled: index == 2,
    )

    result = run_v3_pullback_backtest(bars, _small_config())

    assert result.trade_count == 0


def test_risk_sizing_obeys_risk_and_notional_caps(monkeypatch) -> None:
    bars = (
        _bar(0, open_price=100.0, high=100.1, low=99.95, close=99.98),
        _bar(1, open_price=99.98, high=100.1, low=99.96, close=100.0),
        _bar(2, open_price=100.0, high=100.2, low=99.95, close=100.1),
        _bar(3, open_price=100.1, high=100.2, low=100.0, close=100.1),
    )
    _patch_single_setup(monkeypatch, bars, 0.1)
    config = _small_config(
        stop_buffer_atr=0.25,
        min_stop_distance_atr=0.1,
        max_stop_distance_atr=3.0,
    )

    result = run_v3_pullback_backtest(bars, config, risk_sized=True)

    assert result.trade_count == 1
    assert result.max_notional_fraction <= 0.50 + 1e-12
    assert result.max_planned_risk_fraction <= 0.0035 + 1e-12
