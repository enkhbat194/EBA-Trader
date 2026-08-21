from dataclasses import replace
from datetime import UTC, datetime

import pytest

from eba_trader.derivatives_audit import DerivativeKline, FundingRecord
from eba_trader.history import Candle
from eba_trader.m14_carry import (
    CarryStats,
    YearStats,
    _passes_challenge,
    _passes_discovery,
    benjamini_hochberg,
    generate_non_overlapping_trades,
)

STEP = 15 * 60 * 1000
HOUR = 60 * 60 * 1000
START = int(datetime(2021, 1, 1, tzinfo=UTC).timestamp() * 1000)


def _spot_bar(index: int, price: float = 100.0) -> Candle:
    open_time = START + index * STEP
    return Candle(
        open_time_ms=open_time,
        open=price,
        high=price,
        low=price,
        close=price,
        volume=10.0,
        close_time_ms=open_time + STEP - 1,
        quote_volume=1000.0,
        trade_count=100,
    )


def _future_bar(index: int, price: float = 100.0) -> DerivativeKline:
    open_time = START + index * STEP
    return DerivativeKline(
        open_time_ms=open_time,
        open=price,
        high=price,
        low=price,
        close=price,
        close_time_ms=open_time + STEP - 1,
        volume=10.0,
        quote_volume=1000.0,
        trade_count=100,
        taker_buy_base_volume=5.0,
        taker_buy_quote_volume=500.0,
    )


def _funding(count: int, rate: float = 0.01) -> tuple[FundingRecord, ...]:
    return tuple(
        FundingRecord(
            symbol="BTCUSDT",
            funding_time_ms=START + index * 8 * HOUR,
            funding_rate=rate,
            mark_price=100.0,
        )
        for index in range(count)
    )


def test_market_neutral_pair_cancels_equal_price_move_and_collects_funding() -> None:
    bars = 200
    spot = tuple(_spot_bar(index, 110.0 if index >= 97 else 100.0) for index in range(bars))
    futures = tuple(
        _future_bar(index, 110.0 if index >= 97 else 100.0) for index in range(bars)
    )
    trades = generate_non_overlapping_trades(
        threshold=0.0001,
        hold_records=3,
        funding=_funding(4, rate=0.01),
        spot=spot,
        futures=futures,
        window_start_ms=START,
        window_end_ms=START + 40 * HOUR,
    )
    assert len(trades) == 1
    trade = trades[0]
    assert trade.spot_pnl == pytest.approx(0.1)
    assert trade.perp_pnl == pytest.approx(-0.1)
    assert trade.funding_pnl == pytest.approx(0.03)
    assert trade.base_net_return > 0
    assert trade.severe_net_return > 0


def test_positions_never_overlap() -> None:
    spot = tuple(_spot_bar(index) for index in range(500))
    futures = tuple(_future_bar(index) for index in range(500))
    trades = generate_non_overlapping_trades(
        threshold=0.0001,
        hold_records=3,
        funding=_funding(12, rate=0.001),
        spot=spot,
        futures=futures,
        window_start_ms=START,
        window_end_ms=START + 100 * HOUR,
    )
    assert len(trades) >= 2
    assert all(
        left.exit_time_ms <= right.entry_time_ms
        for left, right in zip(trades, trades[1:], strict=False)
    )


def test_benjamini_hochberg_is_monotone() -> None:
    q = benjamini_hochberg({"a": 0.001, "b": 0.02, "c": 0.5})
    assert 0 <= q["a"] <= q["b"] <= q["c"] <= 1
    assert q["a"] == pytest.approx(0.003)


def _passing_stats() -> CarryStats:
    yearly = tuple(
        YearStats(year, 5, 0.004, 0.002)
        for year in (2021, 2022, 2023)
    )
    return CarryStats(
        trade_count=20,
        distinct_entry_days=15,
        mean_gross_return=0.009,
        mean_base_net=0.006,
        mean_severe_net=0.002,
        median_base_net=0.004,
        profit_factor_base=1.5,
        win_rate_base=0.7,
        daily_mean_p_value=0.001,
        fdr_q_value=0.01,
        yearly=yearly,
        discovery_pass=False,
        challenge_pass=False,
        status="MEASURED",
    )


def test_discovery_gates_require_severe_years_pf_and_fdr() -> None:
    stats = _passing_stats()
    assert _passes_discovery(stats)
    assert not _passes_discovery(replace(stats, mean_severe_net=-0.001))
    assert not _passes_discovery(replace(stats, profit_factor_base=1.1))
    assert not _passes_discovery(replace(stats, fdr_q_value=0.11))


def test_challenge_gates_are_strict() -> None:
    stats = replace(
        _passing_stats(),
        trade_count=6,
        yearly=(YearStats(2024, 6, 0.004, 0.002),),
    )
    assert _passes_challenge(stats)
    assert not _passes_challenge(replace(stats, mean_severe_net=-0.001))
