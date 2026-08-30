from __future__ import annotations

from dataclasses import replace

import pytest

from eba_trader.history import Candle
from eba_trader.orderflow_feature_dataset import OrderFlowFeatureRow
from eba_trader.orderflow_impulse_backtest import (
    OrderFlowDeltaImpulseConfig,
    orderflow_delta_signals,
    run_orderflow_delta_impulse_backtest,
)

STEP_MS = 900_000


def _rows(count: int = 96) -> list[OrderFlowFeatureRow]:
    rows: list[OrderFlowFeatureRow] = []
    price = 100.0
    cvd = 0.0
    pattern = (0.35, 0.25, 0.15, -0.15, -0.25, -0.35, -0.2, 0.2)
    for index in range(count):
        ratio = pattern[index % len(pattern)]
        open_price = price
        drift = 0.45 if index % 6 < 3 else -0.30
        close = max(20.0, open_price + drift)
        candle = Candle(
            open_time_ms=index * STEP_MS,
            open=open_price,
            high=max(open_price, close) + 0.2,
            low=min(open_price, close) - 0.2,
            close=close,
            volume=100.0 + index,
            close_time_ms=(index + 1) * STEP_MS - 1,
            quote_volume=(100.0 + index) * close,
            trade_count=100 + index,
        )
        total = 100.0
        buy = total * (1.0 + ratio) / 2.0
        sell = total - buy
        delta = buy - sell
        cvd += delta
        rows.append(
            OrderFlowFeatureRow(
                candle=candle,
                of_buy_volume=buy,
                of_sell_volume=sell,
                of_delta=delta,
                of_delta_ratio=ratio,
                of_cvd=cvd,
                of_poc_price=open_price,
                footprint_available_at_ms=candle.open_time_ms,
            )
        )
        price = close
    return rows


def test_orderflow_impulse_signals_depend_only_on_closed_delta() -> None:
    rows = _rows(24)
    cfg = OrderFlowDeltaImpulseConfig(side=1, entry_delta_ratio=0.2, exit_delta_ratio=0.05)
    entries, exits, scores = orderflow_delta_signals(rows, cfg)

    mutated = [
        replace(
            row,
            candle=replace(
                row.candle,
                high=row.candle.high + 1000.0,
                low=max(0.01, row.candle.low - 50.0),
                close=row.candle.close + 500.0,
            ),
        )
        for row in rows
    ]
    mutated_entries, mutated_exits, mutated_scores = orderflow_delta_signals(mutated, cfg)

    assert entries == mutated_entries
    assert exits == mutated_exits
    assert scores == mutated_scores
    assert any(entries)
    assert any(exits)


def test_orderflow_impulse_rejects_feature_not_available_at_open() -> None:
    rows = _rows(12)
    rows[4] = replace(
        rows[4],
        footprint_available_at_ms=rows[4].candle.open_time_ms + 1,
    )
    with pytest.raises(ValueError, match="not available by candle open"):
        orderflow_delta_signals(rows)


def test_orderflow_impulse_executes_one_bar_after_signal() -> None:
    rows = _rows()
    cfg = OrderFlowDeltaImpulseConfig(
        side=1,
        entry_delta_ratio=0.2,
        exit_delta_ratio=0.05,
        fee_bps=0.0,
        slippage_bps=0.0,
    )
    entries, exits, _ = orderflow_delta_signals(rows, cfg)
    result = run_orderflow_delta_impulse_backtest(rows, cfg)

    assert result.trade_count >= 1
    open_to_index = {row.candle.open_time_ms: index for index, row in enumerate(rows)}
    for trade in result.trades:
        entry_index = open_to_index[trade.entry_time_ms]
        assert entry_index >= 1
        assert entries[entry_index - 1] is True
        if trade.exit_time_ms != rows[-1].candle.close_time_ms:
            exit_index = open_to_index[trade.exit_time_ms]
            assert exit_index >= 1
            assert exits[exit_index - 1] is True


def test_orderflow_impulse_supports_independent_short_signals() -> None:
    rows = _rows()
    cfg = OrderFlowDeltaImpulseConfig(
        side=-1,
        entry_delta_ratio=0.2,
        exit_delta_ratio=0.05,
        fee_bps=0.0,
        slippage_bps=0.0,
    )
    entries, exits, scores = orderflow_delta_signals(rows, cfg)
    result = run_orderflow_delta_impulse_backtest(rows, cfg)

    assert any(entries)
    assert any(exits)
    assert min(scores) < 0.0 < max(scores)
    assert result.trade_count >= 1


def test_orderflow_impulse_costs_cannot_improve_equity() -> None:
    rows = _rows()
    free = run_orderflow_delta_impulse_backtest(
        rows,
        OrderFlowDeltaImpulseConfig(
            side=1,
            entry_delta_ratio=0.2,
            exit_delta_ratio=0.05,
            fee_bps=0.0,
            slippage_bps=0.0,
        ),
    )
    costly = run_orderflow_delta_impulse_backtest(
        rows,
        OrderFlowDeltaImpulseConfig(
            side=1,
            entry_delta_ratio=0.2,
            exit_delta_ratio=0.05,
            fee_bps=4.0,
            slippage_bps=1.5,
        ),
    )

    assert costly.final_equity <= free.final_equity
    assert costly.total_cost > 0.0


def test_orderflow_impulse_trade_start_blocks_prestart_orders() -> None:
    rows = _rows()
    start_ms = rows[40].candle.open_time_ms
    result = run_orderflow_delta_impulse_backtest(
        rows,
        OrderFlowDeltaImpulseConfig(side=-1, entry_delta_ratio=0.2, exit_delta_ratio=0.05),
        trade_start_time_ms=start_ms,
    )
    assert all(trade.entry_time_ms >= start_ms for trade in result.trades)
