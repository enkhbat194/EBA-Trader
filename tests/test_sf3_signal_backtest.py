from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pytest

from eba_trader.history import Candle
from eba_trader.orderflow_feature_dataset import OrderFlowFeatureRow
from eba_trader.sf3_protocol import SF3Candidate, load_sf3_protocol
from eba_trader.sf3_signal_backtest import (
    SF3ExecutionConfig,
    run_sf3_candidate_backtest,
    sf3_candidate_signals,
)

STEP_MS = 60_000
ROOT = Path(__file__).resolve().parents[1]


def _rows(
    count: int = 180,
    *,
    candle_return: float = 0.0012,
    delta_ratio: float = 0.2,
) -> list[OrderFlowFeatureRow]:
    rows: list[OrderFlowFeatureRow] = []
    price = 100.0
    for index in range(count):
        open_price = price
        close = open_price * (1.0 + candle_return)
        candle = Candle(
            open_time_ms=index * STEP_MS,
            open=open_price,
            high=max(open_price, close) * 1.001,
            low=min(open_price, close) * 0.999,
            close=close,
            volume=100.0,
            close_time_ms=(index + 1) * STEP_MS - 1,
            quote_volume=10_000.0,
            trade_count=100,
        )
        total = 100.0
        buy = total * (1.0 + delta_ratio) / 2.0
        sell = total - buy
        rows.append(
            OrderFlowFeatureRow(
                candle=candle,
                of_buy_volume=buy,
                of_sell_volume=sell,
                of_delta=buy - sell,
                of_delta_ratio=delta_ratio,
                of_cvd=0.0,
                of_poc_price=open_price,
                footprint_available_at_ms=candle.open_time_ms,
            )
        )
        price = close
    return rows


def _candidate(family: str, side: int = 1) -> SF3Candidate:
    if family == "rolling_flow_trend_v1":
        params: dict[str, float | int] = {
            "side": side,
            "lookback": 8,
            "minimum_flow_ratio": 0.08,
            "minimum_price_return": 0.001,
        }
    elif family == "volume_shock_momentum_v1":
        params = {
            "side": side,
            "lookback": 20,
            "volume_multiple": 1.5,
            "minimum_price_return": 0.001,
        }
    elif family == "vwap_reversion_flow_v1":
        params = {
            "side": side,
            "lookback": 20,
            "entry_deviation_bps": 10.0,
            "minimum_reversal_delta_ratio": 0.05,
        }
    elif family == "compression_expansion_v1":
        params = {
            "side": side,
            "short_lookback": 8,
            "long_lookback": 32,
            "compression_ratio_max": 0.75,
            "minimum_price_return": 0.001,
        }
    else:
        raise AssertionError(family)
    return SF3Candidate(candidate_id=f"test-{family}-{side}", family=family, parameters=params)


def _set_flow(row: OrderFlowFeatureRow, *, total: float, delta_ratio: float) -> OrderFlowFeatureRow:
    buy = total * (1.0 + delta_ratio) / 2.0
    sell = total - buy
    return replace(
        row,
        of_buy_volume=buy,
        of_sell_volume=sell,
        of_delta=buy - sell,
        of_delta_ratio=delta_ratio,
    )


def test_every_preregistered_sf3_candidate_has_a_deterministic_signal_path() -> None:
    protocol = load_sf3_protocol(ROOT / "config/sf3_research_protocol_v1.json")
    rows = _rows()

    assert len(protocol.candidates) == 24
    for candidate in protocol.candidates:
        first = sf3_candidate_signals(rows, candidate)
        second = sf3_candidate_signals(rows, candidate)
        assert first == second
        assert len(first) == len(rows)


def test_rolling_flow_trend_generates_independent_entries() -> None:
    rows = _rows()
    candidate = _candidate("rolling_flow_trend_v1")
    signals = sf3_candidate_signals(rows, candidate)

    assert any(signal.entry for signal in signals)
    result = run_sf3_candidate_backtest(
        rows,
        candidate,
        execution=SF3ExecutionConfig(side=1, fee_bps=0.0, slippage_bps=0.0),
    )
    assert result.trade_count >= 1


def test_volume_shock_uses_previous_closed_price_and_current_completed_flow() -> None:
    rows = _rows(candle_return=0.0012)
    index = 50
    rows[index] = _set_flow(rows[index], total=300.0, delta_ratio=0.2)
    candidate = _candidate("volume_shock_momentum_v1")
    baseline = sf3_candidate_signals(rows, candidate)

    assert baseline[index].entry is True
    mutated = list(rows)
    mutated[index] = replace(
        rows[index],
        candle=replace(rows[index].candle, close=rows[index].candle.close * 1.5),
    )
    changed = sf3_candidate_signals(mutated, candidate)
    assert changed[index] == baseline[index]


def test_vwap_reversion_uses_only_closed_price_history() -> None:
    rows = _rows(candle_return=0.0)
    candidate = _candidate("vwap_reversion_flow_v1")
    index = 80
    prior = rows[index - 1]
    rows[index - 1] = replace(
        prior,
        candle=replace(
            prior.candle,
            low=97.5,
            close=98.0,
        ),
    )
    rows[index] = _set_flow(rows[index], total=100.0, delta_ratio=0.2)
    baseline = sf3_candidate_signals(rows, candidate)

    assert baseline[index].entry is True
    mutated = list(rows)
    mutated[index] = replace(
        rows[index],
        candle=replace(rows[index].candle, close=150.0, high=151.0),
    )
    changed = sf3_candidate_signals(mutated, candidate)
    assert changed[index] == baseline[index]


def test_compression_expansion_ignores_current_forming_candle() -> None:
    rows = _rows(candle_return=0.0)
    candidate = _candidate("compression_expansion_v1")
    index = 70
    start = index - 33
    for offset in range(32):
        row_index = start + offset
        candle = rows[row_index].candle
        width = 0.01 if offset < 24 else 0.001
        rows[row_index] = replace(
            rows[row_index],
            candle=replace(
                candle,
                high=candle.open * (1.0 + width),
                low=candle.open * (1.0 - width),
                close=candle.open,
            ),
        )
    expansion = rows[index - 1].candle
    rows[index - 1] = replace(
        rows[index - 1],
        candle=replace(
            expansion,
            high=expansion.open * 1.002,
            low=expansion.open * 0.999,
            close=expansion.open * 1.0015,
        ),
    )
    baseline = sf3_candidate_signals(rows, candidate)

    assert baseline[index].entry is True
    mutated = list(rows)
    mutated[index] = replace(
        rows[index],
        candle=replace(rows[index].candle, close=50.0, low=49.0),
    )
    changed = sf3_candidate_signals(mutated, candidate)
    assert changed[index] == baseline[index]


def test_sf3_execution_waits_one_bar_after_signal() -> None:
    rows = _rows()
    candidate = _candidate("rolling_flow_trend_v1")
    signals = sf3_candidate_signals(rows, candidate)
    result = run_sf3_candidate_backtest(
        rows,
        candidate,
        execution=SF3ExecutionConfig(side=1, fee_bps=0.0, slippage_bps=0.0),
    )
    open_to_index = {row.candle.open_time_ms: index for index, row in enumerate(rows)}

    assert result.trade_count >= 1
    for trade in result.trades:
        entry_index = open_to_index[trade.entry_time_ms]
        assert entry_index >= 1
        assert signals[entry_index - 1].entry is True


def test_sf3_default_hold_contract_is_slower_than_sf2() -> None:
    config = SF3ExecutionConfig(side=1)
    assert config.minimum_hold_bars == 4
    assert config.max_hold_bars == 30
    assert config.signal_to_execution_delay_bars == 1


def test_costs_cannot_improve_sf3_equity() -> None:
    rows = _rows()
    candidate = _candidate("rolling_flow_trend_v1")
    free = run_sf3_candidate_backtest(
        rows,
        candidate,
        execution=SF3ExecutionConfig(side=1, fee_bps=0.0, slippage_bps=0.0),
    )
    costly = run_sf3_candidate_backtest(rows, candidate)

    assert costly.final_equity <= free.final_equity
    assert costly.total_cost > 0.0


def test_short_sf3_candidate_is_supported() -> None:
    rows = _rows(candle_return=-0.0012, delta_ratio=-0.2)
    candidate = _candidate("rolling_flow_trend_v1", side=-1)
    result = run_sf3_candidate_backtest(
        rows,
        candidate,
        execution=SF3ExecutionConfig(side=-1, fee_bps=0.0, slippage_bps=0.0),
    )
    assert result.trade_count >= 1


def test_sf3_rejects_late_flow_feature() -> None:
    rows = _rows(40)
    rows[10] = replace(
        rows[10],
        footprint_available_at_ms=rows[10].candle.open_time_ms + 1,
    )
    with pytest.raises(ValueError, match="not available by candle open"):
        sf3_candidate_signals(rows, _candidate("rolling_flow_trend_v1"))


def test_trade_start_blocks_prestart_sf3_entries() -> None:
    rows = _rows()
    candidate = _candidate("rolling_flow_trend_v1")
    start_ms = rows[100].candle.open_time_ms
    result = run_sf3_candidate_backtest(
        rows,
        candidate,
        trade_start_time_ms=start_ms,
    )
    assert all(trade.entry_time_ms >= start_ms for trade in result.trades)
