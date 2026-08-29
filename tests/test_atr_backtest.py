from __future__ import annotations

from eba_trader.atr_backtest import (
    AtrTrailingConfig,
    atr_trailing_regime,
    run_atr_trailing_backtest,
    wilder_atr,
)
from eba_trader.history import Candle


def _series(count: int = 220, step_ms: int = 900_000) -> list[Candle]:
    rows: list[Candle] = []
    price = 100.0
    for index in range(count):
        phase = index % 80
        if phase < 20:
            drift = -0.8
        elif phase < 55:
            drift = 1.15
        else:
            drift = -1.0
        open_price = price
        close = max(10.0, open_price + drift)
        rows.append(
            Candle(
                open_time_ms=index * step_ms,
                open=open_price,
                high=max(open_price, close) + 0.45,
                low=min(open_price, close) - 0.45,
                close=close,
                volume=100.0 + index,
                close_time_ms=(index + 1) * step_ms - 1,
                quote_volume=(100.0 + index) * close,
                trade_count=100 + index,
            )
        )
        price = close
    return rows


def test_wilder_atr_warms_up_without_future_values() -> None:
    rows = _series(40)
    values = wilder_atr(rows, 14)
    assert values[:13] == [None] * 13
    assert values[13] is not None
    assert all(value is not None and value > 0.0 for value in values[13:])


def test_atr_trailing_backtest_generates_independent_trades_at_next_opens() -> None:
    rows = _series()
    cfg = AtrTrailingConfig(atr_period=14, atr_multiplier=2.0, fee_bps=0.0, slippage_bps=0.0)
    result = run_atr_trailing_backtest(rows, cfg)

    assert result.trade_count >= 1
    assert result.final_equity > 0.0
    assert result.max_drawdown <= 0.0
    assert 0.0 <= result.exposure <= 1.0
    valid_opens = {bar.open_time_ms for bar in rows[cfg.atr_period + 1 :]}
    assert all(trade.entry_time_ms in valid_opens for trade in result.trades)
    assert all(
        trade.exit_time_ms in valid_opens or trade.exit_time_ms == rows[-1].close_time_ms
        for trade in result.trades
    )


def test_atr_costs_cannot_improve_equity() -> None:
    rows = _series()
    free = run_atr_trailing_backtest(
        rows,
        AtrTrailingConfig(atr_period=14, atr_multiplier=2.0, fee_bps=0.0, slippage_bps=0.0),
    )
    costly = run_atr_trailing_backtest(
        rows,
        AtrTrailingConfig(atr_period=14, atr_multiplier=2.0, fee_bps=4.0, slippage_bps=1.5),
    )
    assert costly.final_equity <= free.final_equity
    assert costly.total_cost > 0.0


def test_atr_regime_is_prefix_causal_when_future_tail_changes() -> None:
    prefix = _series(150)
    extended = prefix + _series(60, step_ms=900_000)
    # Shift the appended timestamps and mutate prices heavily. None of this may alter prefix state.
    shifted: list[Candle] = prefix.copy()
    base_time = prefix[-1].close_time_ms + 1
    price = prefix[-1].close
    for index in range(60):
        open_price = price
        close = max(10.0, open_price + (15.0 if index % 2 == 0 else -14.0))
        shifted.append(
            Candle(
                open_time_ms=base_time + index * 900_000,
                open=open_price,
                high=max(open_price, close) + 3.0,
                low=min(open_price, close) - 3.0,
                close=close,
                volume=10_000.0,
                close_time_ms=base_time + (index + 1) * 900_000 - 1,
                quote_volume=10_000.0 * close,
                trade_count=10_000,
            )
        )
        price = close

    cfg = AtrTrailingConfig(atr_period=14, atr_multiplier=2.5)
    prefix_stops, prefix_regimes = atr_trailing_regime(prefix, cfg)
    extended_stops, extended_regimes = atr_trailing_regime(shifted, cfg)
    assert extended_stops[: len(prefix)] == prefix_stops
    assert extended_regimes[: len(prefix)] == prefix_regimes
    assert len(extended) == len(shifted)


def test_trade_start_uses_warmup_without_prestart_orders() -> None:
    rows = _series()
    cfg = AtrTrailingConfig(atr_period=14, atr_multiplier=2.0, fee_bps=0.0, slippage_bps=0.0)
    start_ms = rows[80].open_time_ms
    result = run_atr_trailing_backtest(rows, cfg, trade_start_time_ms=start_ms)
    assert all(trade.entry_time_ms >= start_ms for trade in result.trades)
