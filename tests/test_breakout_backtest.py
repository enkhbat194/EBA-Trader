from __future__ import annotations

from eba_trader.breakout_backtest import (
    DonchianBreakoutConfig,
    donchian_signals,
    run_donchian_breakout_backtest,
)
from eba_trader.history import Candle


def _series(count: int = 260, step_ms: int = 900_000) -> list[Candle]:
    rows: list[Candle] = []
    price = 100.0
    for index in range(count):
        phase = index % 100
        if phase < 25:
            drift = -0.35
        elif phase < 60:
            drift = 1.2
        elif phase < 78:
            drift = 0.05
        else:
            drift = -1.05
        open_price = price
        close = max(10.0, open_price + drift)
        rows.append(
            Candle(
                open_time_ms=index * step_ms,
                open=open_price,
                high=max(open_price, close) + 0.3,
                low=min(open_price, close) - 0.3,
                close=close,
                volume=100.0 + index,
                close_time_ms=(index + 1) * step_ms - 1,
                quote_volume=(100.0 + index) * close,
                trade_count=100 + index,
            )
        )
        price = close
    return rows


def test_donchian_signals_use_only_prior_channel_values() -> None:
    rows = _series(90)
    cfg = DonchianBreakoutConfig(entry_lookback=16, exit_lookback=8)
    entries, exits = donchian_signals(rows, cfg)
    assert entries[:16] == (False,) * 16
    assert exits[:16] == (False,) * 16
    assert any(entries[16:])
    assert any(exits[16:])


def test_breakout_executes_only_at_next_opens() -> None:
    rows = _series()
    cfg = DonchianBreakoutConfig(
        entry_lookback=16,
        exit_lookback=8,
        fee_bps=0.0,
        slippage_bps=0.0,
    )
    result = run_donchian_breakout_backtest(rows, cfg)
    assert result.trade_count >= 1
    assert result.final_equity > 0.0
    valid_opens = {bar.open_time_ms for bar in rows[max(cfg.entry_lookback, cfg.exit_lookback) + 1 :]}
    assert all(trade.entry_time_ms in valid_opens for trade in result.trades)
    assert all(
        trade.exit_time_ms in valid_opens or trade.exit_time_ms == rows[-1].close_time_ms
        for trade in result.trades
    )


def test_breakout_future_tail_cannot_change_prefix_signals() -> None:
    prefix = _series(150)
    shifted = prefix.copy()
    base_time = prefix[-1].close_time_ms + 1
    price = prefix[-1].close
    for index in range(60):
        open_price = price
        close = max(10.0, open_price + (20.0 if index % 2 == 0 else -19.0))
        shifted.append(
            Candle(
                open_time_ms=base_time + index * 900_000,
                open=open_price,
                high=max(open_price, close) + 4.0,
                low=min(open_price, close) - 4.0,
                close=close,
                volume=50_000.0,
                close_time_ms=base_time + (index + 1) * 900_000 - 1,
                quote_volume=50_000.0 * close,
                trade_count=50_000,
            )
        )
        price = close

    cfg = DonchianBreakoutConfig(entry_lookback=32, exit_lookback=16)
    prefix_entries, prefix_exits = donchian_signals(prefix, cfg)
    full_entries, full_exits = donchian_signals(shifted, cfg)
    assert full_entries[: len(prefix)] == prefix_entries
    assert full_exits[: len(prefix)] == prefix_exits


def test_breakout_costs_cannot_improve_equity() -> None:
    rows = _series()
    free = run_donchian_breakout_backtest(
        rows,
        DonchianBreakoutConfig(
            entry_lookback=16,
            exit_lookback=8,
            fee_bps=0.0,
            slippage_bps=0.0,
        ),
    )
    costly = run_donchian_breakout_backtest(
        rows,
        DonchianBreakoutConfig(entry_lookback=16, exit_lookback=8),
    )
    assert costly.final_equity <= free.final_equity
    assert costly.total_cost > 0.0


def test_breakout_trade_start_blocks_prestart_orders() -> None:
    rows = _series()
    cfg = DonchianBreakoutConfig(entry_lookback=16, exit_lookback=8)
    start_ms = rows[90].open_time_ms
    result = run_donchian_breakout_backtest(rows, cfg, trade_start_time_ms=start_ms)
    assert all(trade.entry_time_ms >= start_ms for trade in result.trades)
