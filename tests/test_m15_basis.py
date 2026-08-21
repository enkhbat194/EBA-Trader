from __future__ import annotations

from eba_trader.derivatives_audit import DerivativeKline, FundingRecord
from eba_trader.history import Candle, parse_utc
from eba_trader.m15_basis import (
    STEP_MS,
    basis_value,
    generate_non_overlapping_trades,
)
from eba_trader.m15_basis_policy import verify_m15_freeze


def _spot_bar(open_time: int, *, open_price: float, close_price: float) -> Candle:
    high = max(open_price, close_price) * 1.001
    low = min(open_price, close_price) * 0.999
    return Candle(
        open_time_ms=open_time,
        open=open_price,
        high=high,
        low=low,
        close=close_price,
        volume=10.0,
        close_time_ms=open_time + STEP_MS - 1,
        quote_volume=1000.0,
        trade_count=10,
    )


def _perp_bar(open_time: int, *, open_price: float, close_price: float) -> DerivativeKline:
    high = max(open_price, close_price) * 1.001
    low = min(open_price, close_price) * 0.999
    return DerivativeKline(
        open_time_ms=open_time,
        open=open_price,
        high=high,
        low=low,
        close=close_price,
        close_time_ms=open_time + STEP_MS - 1,
        volume=10.0,
        quote_volume=1000.0,
        trade_count=10,
        taker_buy_base_volume=5.0,
        taker_buy_quote_volume=500.0,
    )


def test_m15_freeze_manifest_verifies() -> None:
    manifest = verify_m15_freeze()
    assert manifest["status"] == "FROZEN_PREDECLARED_NOT_RUN"
    assert manifest["configuration_count"] == 9
    assert manifest["oos_2025"] == "LOCKED_NOT_ACCESSED"
    assert manifest["leverage"] == "forbidden"
    assert manifest["naked_short"] == "forbidden"


def test_basis_value_is_perp_over_spot_minus_one() -> None:
    assert basis_value(100.0, 102.0) == 0.020000000000000018


def test_convergence_trade_uses_next_open_and_excludes_entry_timestamp_funding() -> None:
    start = parse_utc("2021-01-01T00:00:00Z")
    times = [start + index * STEP_MS for index in range(5)]
    spot = tuple(
        _spot_bar(time, open_price=100.0, close_price=100.0)
        for time in times
    )
    perp_closes = (102.0, 101.5, 100.05, 100.04, 100.03)
    futures = tuple(
        _perp_bar(time, open_price=close_price, close_price=close_price)
        for time, close_price in zip(times, perp_closes, strict=True)
    )
    funding = (
        FundingRecord(
            symbol="BTCUSDT",
            funding_time_ms=times[1],
            funding_rate=0.10,
            mark_price=101.5,
        ),
        FundingRecord(
            symbol="BTCUSDT",
            funding_time_ms=times[2],
            funding_rate=0.001,
            mark_price=100.05,
        ),
    )

    trades = generate_non_overlapping_trades(
        entry_basis_threshold=0.0075,
        max_hold_bars=96,
        funding=funding,
        spot=spot,
        futures=futures,
        window_start_ms=start,
        window_end_ms=start + 200 * STEP_MS,
    )

    assert len(trades) == 1
    trade = trades[0]
    assert trade.signal_open_time_ms == times[0]
    assert trade.entry_time_ms == times[1]
    assert trade.exit_time_ms == times[3]
    assert trade.exit_reason == "CONVERGENCE"
    assert trade.actual_hold_bars == 2
    assert 0 < trade.funding_pnl < 0.01


def test_time_stop_exit_is_deterministic_when_basis_does_not_converge() -> None:
    start = parse_utc("2021-01-01T00:00:00Z")
    times = [start + index * STEP_MS for index in range(5)]
    spot = tuple(
        _spot_bar(time, open_price=100.0, close_price=100.0)
        for time in times
    )
    futures = tuple(
        _perp_bar(time, open_price=102.0, close_price=102.0)
        for time in times
    )

    trades = generate_non_overlapping_trades(
        entry_basis_threshold=0.0075,
        max_hold_bars=2,
        funding=(),
        spot=spot,
        futures=futures,
        window_start_ms=start,
        window_end_ms=start + 10 * STEP_MS,
    )

    assert len(trades) == 1
    trade = trades[0]
    assert trade.entry_time_ms == times[1]
    assert trade.exit_time_ms == times[3]
    assert trade.exit_reason == "TIME_STOP"
    assert trade.actual_hold_bars == 2
