from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime

from eba_trader.derivatives_audit import DerivativeKline
from eba_trader.history import Candle
from eba_trader.m16_delivery_policy import DeliveryContract
from eba_trader.m17_delivery_carry import (
    DeliveryCarryTrade,
    _passes_challenge,
    _passes_discovery,
    benjamini_hochberg,
    build_trade,
    exact_sign_flip_p_value,
    summarize_trades,
)
from eba_trader.m17_delivery_carry_policy import (
    ENTRY_OFFSETS_DAYS,
    USDM_NORMALIZED_SHA256,
    verify_m17_freeze,
)

INTERVAL_MS = 15 * 60 * 1000


def _candle(timestamp: int, price: float) -> Candle:
    return Candle(
        open_time_ms=timestamp,
        open=price,
        high=price * 1.01,
        low=price * 0.99,
        close=price,
        volume=1.0,
        close_time_ms=timestamp + INTERVAL_MS - 1,
        quote_volume=price,
        trade_count=10,
    )


def _future(timestamp: int, price: float, high: float | None = None) -> DerivativeKline:
    return DerivativeKline(
        open_time_ms=timestamp,
        open=price,
        high=high if high is not None else price * 1.01,
        low=price * 0.99,
        close=price,
        close_time_ms=timestamp + INTERVAL_MS - 1,
        volume=1.0,
        quote_volume=price,
        trade_count=10,
        taker_buy_base_volume=0.5,
        taker_buy_quote_volume=price * 0.5,
    )


def _trade(year: int, value: float, severe: float | None = None) -> DeliveryCarryTrade:
    severe_value = value if severe is None else severe
    return DeliveryCarryTrade(
        symbol=f"BTCUSDT_{year}TEST",
        year=year,
        entry_offset_days=7,
        entry_time_ms=1,
        exit_time_ms=2,
        spot_entry=100.0,
        spot_exit=101.0,
        futures_entry=102.0,
        futures_exit=101.0,
        btc_quantity=0.01,
        capital_usd=2.02,
        entry_basis=0.02,
        exit_basis=0.0,
        gross_return=value + 0.01,
        base_net_return=value,
        severe_net_return=severe_value,
        margin_remaining_ratio=0.9,
        margin_safe=True,
    )


def test_m17_freeze_manifest_verifies() -> None:
    manifest = verify_m17_freeze()
    assert manifest["status"] == "FROZEN_PREDECLARED_NOT_RUN"
    assert manifest["entry_offsets_days"] == [28, 14, 7]
    assert tuple(manifest["entry_offsets_days"]) == ENTRY_OFFSETS_DAYS
    assert len(USDM_NORMALIZED_SHA256) == 16
    assert manifest["oos_2025"] == "LOCKED_NOT_ACCESSED"
    assert manifest["coin_m"] == "forbidden"


def test_exact_sign_flip_and_bh_are_deterministic() -> None:
    p_value = exact_sign_flip_p_value([0.01] * 12)
    assert p_value == 1 / 4096
    adjusted = benjamini_hochberg({"a": p_value, "b": 0.5, "c": 1.0})
    assert 0 < adjusted["a"] <= 0.001
    assert adjusted["b"] <= adjusted["c"]


def test_same_quantity_pair_captures_basis_convergence_and_is_margin_safe() -> None:
    delivery = int(datetime(2023, 3, 31, 8, tzinfo=UTC).timestamp() * 1000)
    contract = DeliveryContract(
        suffix="230331",
        delivery_time_ms=delivery,
        year=2023,
        discovery=True,
    )
    entry = delivery - 7 * 24 * 60 * 60 * 1000
    exit_time = delivery - INTERVAL_MS
    spot_by_time = {
        entry: _candle(entry, 100.0),
        exit_time: _candle(exit_time, 110.0),
    }
    futures_by_time = {
        entry: _future(entry, 105.0, high=120.0),
        exit_time - INTERVAL_MS: _future(exit_time - INTERVAL_MS, 111.0, high=112.0),
        exit_time: _future(exit_time, 110.5, high=111.0),
    }
    trade = build_trade(
        contract=contract,
        entry_offset_days=7,
        spot_by_time=spot_by_time,
        futures_by_time=futures_by_time,
    )
    assert trade is not None
    assert trade.btc_quantity == 0.01
    assert abs(trade.entry_basis - 0.05) < 1e-12
    assert trade.exit_basis > 0
    assert trade.gross_return > 0
    assert trade.base_net_return > trade.severe_net_return
    assert trade.margin_safe is True
    assert trade.margin_remaining_ratio > 0.5


def test_discovery_gate_requires_all_years_and_severe_economics() -> None:
    trades = tuple(
        _trade(year, 0.02)
        for year in (2021, 2022, 2023)
        for _ in range(4)
    )
    stats = summarize_trades(trades, years=(2021, 2022, 2023), q_value=0.01)
    assert _passes_discovery(stats) is True

    bad = list(trades)
    bad[4] = _trade(2022, 0.02, severe=-0.50)
    bad_stats = summarize_trades(tuple(bad), years=(2021, 2022, 2023), q_value=0.01)
    assert _passes_discovery(bad_stats) is False


def test_challenge_requires_three_severe_wins_and_margin_safety() -> None:
    trades = (
        _trade(2024, 0.02),
        _trade(2024, 0.02),
        _trade(2024, 0.02),
        _trade(2024, 0.01, severe=-0.001),
    )
    stats = summarize_trades(trades, years=(2024,))
    assert _passes_challenge(stats) is True

    unsafe_trade = replace(trades[0], margin_safe=False, margin_remaining_ratio=0.4)
    unsafe = summarize_trades((unsafe_trade, *trades[1:]), years=(2024,))
    assert _passes_challenge(unsafe) is False
