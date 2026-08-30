from __future__ import annotations

from eba_trader.history import Candle
from eba_trader.mean_reversion_backtest import (
    MeanReversionConfig,
    mean_reversion_signals,
    run_mean_reversion_backtest,
)


def _series(count: int = 320, step_ms: int = 900_000) -> list[Candle]:
    rows: list[Candle] = []
    price = 100.0
    for index in range(count):
        phase = index % 80
        if phase < 24:
            drift = 0.12
        elif phase < 32:
            drift = -1.6
        elif phase < 52:
            drift = 0.85
        elif phase < 64:
            drift = 0.04
        else:
            drift = -0.18
        open_price = price
        close = max(10.0, open_price + drift)
        rows.append(
            Candle(
                open_time_ms=index * step_ms,
                open=open_price,
                high=max(open_price, close) + 0.25,
                low=min(open_price, close) - 0.25,
                close=close,
                volume=100.0 + index,
                close_time_ms=(index + 1) * step_ms - 1,
                quote_volume=(100.0 + index) * close,
                trade_count=100 + index,
            )
        )
        price = close
    return rows


def test_mean_reversion_signals_use_only_prior_distribution() -> None:
    rows = _series(180)
    cfg = MeanReversionConfig(lookback=24, entry_z=1.5, exit_z=0.2)
    entries, exits, z_scores = mean_reversion_signals(rows, cfg)
    assert entries[:24] == (False,) * 24
    assert exits[:24] == (False,) * 24
    assert all(value is None for value in z_scores[:24])
    assert any(entries[24:])
    assert any(exits[24:])


def test_mean_reversion_executes_only_on_next_opens() -> None:
    rows = _series()
    cfg = MeanReversionConfig(
        lookback=24,
        entry_z=1.5,
        exit_z=0.2,
        fee_bps=0.0,
        slippage_bps=0.0,
    )
    result = run_mean_reversion_backtest(rows, cfg)
    assert result.trade_count >= 1
    valid_opens = {bar.open_time_ms for bar in rows[cfg.lookback + 1 :]}
    assert all(trade.entry_time_ms in valid_opens for trade in result.trades)
    assert all(
        trade.exit_time_ms in valid_opens or trade.exit_time_ms == rows[-1].close_time_ms
        for trade in result.trades
    )


def test_future_tail_cannot_change_mean_reversion_prefix_signals() -> None:
    prefix = _series(180)
    extended = prefix.copy()
    price = prefix[-1].close
    base_time = prefix[-1].close_time_ms + 1
    for index in range(60):
        open_price = price
        close = max(10.0, open_price + (25.0 if index % 2 == 0 else -24.0))
        extended.append(
            Candle(
                open_time_ms=base_time + index * 900_000,
                open=open_price,
                high=max(open_price, close) + 3.0,
                low=min(open_price, close) - 3.0,
                close=close,
                volume=50_000.0,
                close_time_ms=base_time + (index + 1) * 900_000 - 1,
                quote_volume=50_000.0 * close,
                trade_count=50_000,
            )
        )
        price = close

    cfg = MeanReversionConfig(lookback=32, entry_z=1.8, exit_z=0.25)
    prefix_entries, prefix_exits, prefix_z = mean_reversion_signals(prefix, cfg)
    full_entries, full_exits, full_z = mean_reversion_signals(extended, cfg)
    assert full_entries[: len(prefix)] == prefix_entries
    assert full_exits[: len(prefix)] == prefix_exits
    assert full_z[: len(prefix)] == prefix_z


def test_mean_reversion_costs_cannot_improve_equity() -> None:
    rows = _series()
    free = run_mean_reversion_backtest(
        rows,
        MeanReversionConfig(
            lookback=24,
            entry_z=1.5,
            exit_z=0.2,
            fee_bps=0.0,
            slippage_bps=0.0,
        ),
    )
    costly = run_mean_reversion_backtest(
        rows,
        MeanReversionConfig(lookback=24, entry_z=1.5, exit_z=0.2),
    )
    assert costly.final_equity <= free.final_equity
    assert costly.total_cost > 0.0


def test_mean_reversion_trade_start_blocks_prestart_orders() -> None:
    rows = _series()
    cfg = MeanReversionConfig(lookback=24, entry_z=1.5, exit_z=0.2)
    start_ms = rows[120].open_time_ms
    result = run_mean_reversion_backtest(rows, cfg, trade_start_time_ms=start_ms)
    assert all(trade.entry_time_ms >= start_ms for trade in result.trades)
