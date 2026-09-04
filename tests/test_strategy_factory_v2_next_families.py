from __future__ import annotations

from dataclasses import replace

import pytest

from eba_trader.history import Candle
from eba_trader.orderflow_feature_dataset import OrderFlowFeatureRow
from eba_trader.strategy_factory_v2_next_families import (
    BreakoutRetestConfig,
    LowTurnoverFlowPersistenceConfig,
    MtfTrendPullbackConfig,
    NextExecutionPolicy,
    NextFamilySignal,
    PathEfficiencyConfig,
    aggregate_closed_candles,
    breakout_retest_signals,
    low_turnover_flow_persistence_signals,
    mtf_trend_pullback_signals,
    path_efficiency_signals,
    run_next_family_backtest,
)

MINUTE = 60_000


def _candle(
    minute: int,
    *,
    open_price: float = 100.0,
    high: float | None = None,
    low: float | None = None,
    close: float | None = None,
    volume: float = 10.0,
) -> Candle:
    close_price = open_price if close is None else close
    return Candle(
        open_time_ms=minute * MINUTE,
        open=open_price,
        high=max(open_price, close_price) if high is None else high,
        low=min(open_price, close_price) if low is None else low,
        close=close_price,
        volume=volume,
        close_time_ms=(minute + 1) * MINUTE - 1,
        quote_volume=volume * open_price,
        trade_count=10,
    )


def _flat_candles(count: int, price: float = 100.0) -> tuple[Candle, ...]:
    return tuple(_candle(index, open_price=price) for index in range(count))


def _flow_row(candle: Candle, ratio: float) -> OrderFlowFeatureRow:
    total = 100.0
    delta = total * ratio
    buy = (total + delta) / 2.0
    sell = (total - delta) / 2.0
    return OrderFlowFeatureRow(
        candle=candle,
        of_buy_volume=buy,
        of_sell_volume=sell,
        of_delta=delta,
        of_delta_ratio=ratio,
        of_cvd=0.0,
        of_poc_price=candle.open,
        footprint_available_at_ms=candle.open_time_ms,
    )


def test_aggregation_skips_gap_bucket_and_never_bridges_missing_minute() -> None:
    candles = tuple(_candle(index) for index in range(20) if index != 7)
    aggregated = aggregate_closed_candles(candles, interval_minutes=5)
    assert [bar.open_time_ms for bar in aggregated] == [0, 10 * MINUTE, 15 * MINUTE]
    assert all(bar.close_time_ms - bar.open_time_ms == 5 * MINUTE - 1 for bar in aggregated)


def test_aggregation_requires_supported_closed_interval() -> None:
    with pytest.raises(ValueError, match="5, 15 or 60"):
        aggregate_closed_candles(_flat_candles(20), interval_minutes=10)


def test_mtf_signal_does_not_read_current_candle_ohlc() -> None:
    candles = list(_flat_candles(120))
    changed = list(candles)
    decision_index = 90
    changed[decision_index] = _candle(
        decision_index,
        open_price=100.0,
        high=250.0,
        low=1.0,
        close=200.0,
        volume=1_000_000.0,
    )
    config = MtfTrendPullbackConfig(
        side=1,
        regime_lookback_15m=4,
        pullback_lookback_5m=2,
        minimum_regime_return=0.001,
        minimum_pullback_return=0.001,
        minimum_resume_return=0.0,
        minimum_hold_minutes=30,
        max_hold_minutes=180,
        cooldown_minutes=15,
    )
    baseline = mtf_trend_pullback_signals(tuple(candles), config)
    altered = mtf_trend_pullback_signals(tuple(changed), config)
    assert baseline[decision_index] == altered[decision_index]


def test_breakout_cannot_enter_until_later_retest_bar_has_closed() -> None:
    candles = list(_flat_candles(80))
    for minute in range(60, 65):
        candles[minute] = _candle(
            minute,
            open_price=101.0,
            high=103.0,
            low=100.8,
            close=102.0,
        )
    for minute in range(65, 70):
        candles[minute] = _candle(
            minute,
            open_price=100.2,
            high=100.5,
            low=99.95,
            close=100.2,
        )
    config = BreakoutRetestConfig(
        side=1,
        range_lookback_15m=4,
        minimum_breakout_bps=50.0,
        retest_tolerance_bps=10.0,
        max_retest_wait_5m=3,
        minimum_hold_minutes=30,
        max_hold_minutes=180,
        cooldown_minutes=15,
    )
    signals = breakout_retest_signals(tuple(candles), config)
    assert signals[65].entry is False
    assert signals[70].entry is True
    assert all(not signals[index].entry for index in range(61, 70))


def test_path_efficiency_only_decides_when_new_15m_bar_is_available() -> None:
    candles = []
    for minute in range(120):
        price = 100.0 + minute * 0.02
        candles.append(_candle(minute, open_price=price, close=price + 0.01))
    config = PathEfficiencyConfig(
        side=1,
        lookback_15m=4,
        minimum_efficiency=0.2,
        minimum_directional_return=0.001,
        minimum_hold_minutes=30,
        max_hold_minutes=180,
        cooldown_minutes=15,
    )
    signals = path_efficiency_signals(tuple(candles), config)
    assert any(item.entry for item in signals)
    assert all(
        not item.entry and not item.opposite
        for index, item in enumerate(signals)
        if (index * MINUTE) % (15 * MINUTE) != 0
    )


def test_low_turnover_flow_requires_longer_structural_horizons() -> None:
    with pytest.raises(ValueError, match="short_flow_lookback_minutes"):
        LowTurnoverFlowPersistenceConfig(
            side=1,
            short_flow_lookback_minutes=5,
            long_flow_lookback_minutes=30,
            price_lookback_minutes=15,
            minimum_short_flow_ratio=0.05,
            minimum_long_flow_ratio=0.03,
            minimum_directional_price_return=0.0,
            minimum_hold_minutes=30,
            max_hold_minutes=180,
            cooldown_minutes=15,
        )
    with pytest.raises(ValueError, match="minimum_hold_minutes"):
        LowTurnoverFlowPersistenceConfig(
            side=1,
            short_flow_lookback_minutes=15,
            long_flow_lookback_minutes=30,
            price_lookback_minutes=15,
            minimum_short_flow_ratio=0.05,
            minimum_long_flow_ratio=0.03,
            minimum_directional_price_return=0.0,
            minimum_hold_minutes=15,
            max_hold_minutes=180,
            cooldown_minutes=15,
        )


def test_low_turnover_flow_uses_feature_available_at_current_open() -> None:
    candles = _flat_candles(90)
    rows = tuple(_flow_row(candle, 0.10) for candle in candles)
    config = LowTurnoverFlowPersistenceConfig(
        side=1,
        short_flow_lookback_minutes=15,
        long_flow_lookback_minutes=30,
        price_lookback_minutes=15,
        minimum_short_flow_ratio=0.05,
        minimum_long_flow_ratio=0.03,
        minimum_directional_price_return=0.0,
        minimum_hold_minutes=30,
        max_hold_minutes=180,
        cooldown_minutes=15,
    )
    signals = low_turnover_flow_persistence_signals(candles, rows, config)
    assert signals[30].entry is True
    assert all(not signals[index].entry for index in range(31, 45))

    future_leaking_rows = list(rows)
    future_leaking_rows[30] = replace(
        future_leaking_rows[30],
        footprint_available_at_ms=candles[30].open_time_ms + 1,
    )
    with pytest.raises(ValueError, match="not causal"):
        low_turnover_flow_persistence_signals(candles, future_leaking_rows, config)


def test_execution_policy_enforces_minimum_hold_and_cooldown() -> None:
    candles = _flat_candles(120)
    signals = tuple(NextFamilySignal(entry=True) for _ in candles)
    policy = NextExecutionPolicy(
        side=1,
        minimum_hold_minutes=15,
        max_hold_minutes=15,
        cooldown_minutes=30,
    )
    result = run_next_family_backtest(candles, signals, policy)
    assert len(result.trades) >= 2
    for trade in result.trades[:-1]:
        assert trade.exit_time_ms - trade.entry_time_ms >= 15 * MINUTE
    for left, right in zip(result.trades, result.trades[1:], strict=False):
        assert right.entry_time_ms - left.exit_time_ms >= 30 * MINUTE
