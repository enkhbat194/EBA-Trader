from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pytest

from eba_trader.history import Candle
from eba_trader.orderflow_feature_dataset import OrderFlowFeatureRow
from eba_trader.sf2_protocol import SF2Candidate, load_sf2_protocol
from eba_trader.sf2_signal_backtest import (
    SF2ExecutionConfig,
    run_sf2_candidate_backtest,
    sf2_candidate_signals,
)

STEP_MS = 60_000
ROOT = Path(__file__).resolve().parents[1]


def _rows(count: int = 96) -> list[OrderFlowFeatureRow]:
    rows: list[OrderFlowFeatureRow] = []
    price = 100.0
    for index in range(count):
        direction = 1.0 if index % 8 < 4 else -1.0
        open_price = price
        close = max(10.0, open_price * (1.0 + direction * 0.001))
        candle = Candle(
            open_time_ms=index * STEP_MS,
            open=open_price,
            high=max(open_price, close) * 1.0002,
            low=min(open_price, close) * 0.9998,
            close=close,
            volume=100.0,
            close_time_ms=(index + 1) * STEP_MS - 1,
            quote_volume=10_000.0,
            trade_count=100,
        )
        delta_ratio = 0.3 * direction
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
                of_stacked_buy_levels=4 if direction > 0 else 0,
                of_stacked_sell_levels=4 if direction < 0 else 0,
                of_stacked_imbalance=4 if direction > 0 else -4,
                of_absorption=0.3 * direction,
                of_exhaustion=0.0,
                of_bullish_price_delta_divergence=0.06 if direction > 0 else 0.0,
                of_bearish_price_delta_divergence=0.06 if direction < 0 else 0.0,
                of_price_delta_divergence=0.06 * direction,
            )
        )
        price = close
    return rows


def _candidate(family: str, side: int = 1) -> SF2Candidate:
    if family in {"divergence_reversal_v1", "absorption_reversal_v1"}:
        params: dict[str, float | int] = {"side": side, "signal_threshold": 0.05}
    elif family == "stacked_delta_continuation_v1":
        params = {"side": side, "minimum_stacked_levels": 3, "minimum_delta_ratio": 0.15}
    elif family == "flow_price_continuation_v1":
        params = {"side": side, "minimum_delta_ratio": 0.2, "minimum_price_return": 0.0005}
    else:
        raise AssertionError(family)
    return SF2Candidate(candidate_id=f"test-{family}-{side}", family=family, parameters=params)


def test_every_preregistered_sf2_candidate_has_a_valid_signal_path() -> None:
    protocol = load_sf2_protocol(ROOT / "config/sf2_research_protocol_v1.json")
    rows = _rows()

    assert len(protocol.candidates) == 24
    for candidate in protocol.candidates:
        signals = sf2_candidate_signals(rows, candidate)
        assert len(signals) == len(rows)
        assert any(signal.entry for signal in signals), candidate.candidate_id
        result = run_sf2_candidate_backtest(rows, candidate)
        assert result.trade_count >= 1, candidate.candidate_id


def test_divergence_and_absorption_signals_ignore_still_forming_candle_prices() -> None:
    rows = _rows(24)
    for family in ("divergence_reversal_v1", "absorption_reversal_v1"):
        candidate = _candidate(family)
        baseline = sf2_candidate_signals(rows, candidate)
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
        changed = sf2_candidate_signals(mutated, candidate)
        assert baseline == changed


def test_flow_price_signal_uses_only_previous_closed_candle() -> None:
    rows = _rows(24)
    candidate = _candidate("flow_price_continuation_v1")
    baseline = sf2_candidate_signals(rows, candidate)
    index = 8
    mutated = list(rows)
    mutated[index] = replace(
        rows[index],
        candle=replace(
            rows[index].candle,
            high=rows[index].candle.high + 1000.0,
            low=max(0.01, rows[index].candle.low - 50.0),
            close=rows[index].candle.close + 500.0,
        ),
    )
    changed = sf2_candidate_signals(mutated, candidate)

    # Row i signal cannot see row i high/low/close. Row i+1 may legitimately use row i
    # after it has closed, so only the same-row causal invariant is asserted here.
    assert baseline[index] == changed[index]


def test_sf2_rejects_feature_that_arrives_after_candle_open() -> None:
    rows = _rows(12)
    rows[5] = replace(
        rows[5],
        footprint_available_at_ms=rows[5].candle.open_time_ms + 1,
    )
    with pytest.raises(ValueError, match="not available by candle open"):
        sf2_candidate_signals(rows, _candidate("absorption_reversal_v1"))


def test_sf2_execution_waits_one_bar_after_signal() -> None:
    rows = _rows()
    candidate = _candidate("absorption_reversal_v1")
    signals = sf2_candidate_signals(rows, candidate)
    result = run_sf2_candidate_backtest(
        rows,
        candidate,
        execution=SF2ExecutionConfig(side=1, fee_bps=0.0, slippage_bps=0.0),
    )
    open_to_index = {row.candle.open_time_ms: index for index, row in enumerate(rows)}

    assert result.trade_count >= 1
    for trade in result.trades:
        entry_index = open_to_index[trade.entry_time_ms]
        assert entry_index >= 1
        assert signals[entry_index - 1].entry is True


def test_minimum_hold_blocks_immediate_opposite_signal() -> None:
    rows = _rows(20)
    # Force a single entry signal at row 4 followed by immediate opposite evidence.
    for index in range(len(rows)):
        score = 0.0
        if index == 4:
            score = 0.5
        elif index in (5, 6, 7):
            score = -0.5
        rows[index] = replace(rows[index], of_absorption=score)
    candidate = _candidate("absorption_reversal_v1")
    result = run_sf2_candidate_backtest(
        rows,
        candidate,
        execution=SF2ExecutionConfig(
            side=1,
            fee_bps=0.0,
            slippage_bps=0.0,
            minimum_hold_bars=2,
            max_hold_bars=12,
        ),
    )

    assert result.trade_count == 1
    trade = result.trades[0]
    assert trade.entry_time_ms == rows[5].candle.open_time_ms
    # Opposite row 5 would execute at row 6 (only one bar held), so it is ignored.
    # Opposite row 6 executes at row 7 after the fixed two-bar minimum.
    assert trade.exit_time_ms == rows[7].candle.open_time_ms


def test_maximum_hold_forces_exit_without_opposite_signal() -> None:
    rows = _rows(20)
    for index in range(len(rows)):
        rows[index] = replace(rows[index], of_absorption=0.5 if index == 4 else 0.0)
    candidate = _candidate("absorption_reversal_v1")
    result = run_sf2_candidate_backtest(
        rows,
        candidate,
        execution=SF2ExecutionConfig(
            side=1,
            fee_bps=0.0,
            slippage_bps=0.0,
            minimum_hold_bars=2,
            max_hold_bars=3,
        ),
    )

    assert result.trade_count == 1
    trade = result.trades[0]
    assert trade.entry_time_ms == rows[5].candle.open_time_ms
    assert trade.exit_time_ms == rows[8].candle.open_time_ms


def test_costs_cannot_improve_sf2_equity() -> None:
    rows = _rows()
    candidate = _candidate("stacked_delta_continuation_v1")
    free = run_sf2_candidate_backtest(
        rows,
        candidate,
        execution=SF2ExecutionConfig(side=1, fee_bps=0.0, slippage_bps=0.0),
    )
    costly = run_sf2_candidate_backtest(rows, candidate)

    assert costly.final_equity <= free.final_equity
    assert costly.total_cost > 0.0


def test_short_candidate_is_supported_without_live_authority() -> None:
    rows = _rows()
    candidate = _candidate("divergence_reversal_v1", side=-1)
    result = run_sf2_candidate_backtest(
        rows,
        candidate,
        execution=SF2ExecutionConfig(side=-1, fee_bps=0.0, slippage_bps=0.0),
    )
    assert result.trade_count >= 1


def test_trade_start_blocks_prestart_entries() -> None:
    rows = _rows()
    candidate = _candidate("absorption_reversal_v1")
    start_ms = rows[40].candle.open_time_ms
    result = run_sf2_candidate_backtest(
        rows,
        candidate,
        trade_start_time_ms=start_ms,
    )
    assert all(trade.entry_time_ms >= start_ms for trade in result.trades)
