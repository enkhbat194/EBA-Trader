from __future__ import annotations

import pytest

from eba_trader.orderflow import AggressorSide, PriceLevelFlow
from eba_trader.orderflow_dataset import AggregateTradeRecord
from eba_trader.orderflow_response import executed_flow_response


def _trade(
    trade_id: int,
    timestamp_ms: int,
    price: float,
    quantity: float,
    side: AggressorSide,
) -> AggregateTradeRecord:
    return AggregateTradeRecord(trade_id, timestamp_ms, price, quantity, side)


def _level(price: float, buy: float, sell: float) -> PriceLevelFlow:
    return PriceLevelFlow(price=price, buy_volume=buy, sell_volume=sell)


def test_sell_pressure_that_fails_to_move_down_is_bullish_absorption_proxy() -> None:
    records = (
        _trade(1, 100, 100.0, 4.0, AggressorSide.SELL),
        _trade(2, 200, 100.0, 4.0, AggressorSide.SELL),
        _trade(3, 300, 101.0, 1.0, AggressorSide.BUY),
    )

    result = executed_flow_response(records, (), start_ms=0, end_ms=1_000, price_step=1.0)

    assert result.absorption > 0.0
    assert result.absorption <= 1.0


def test_sell_pressure_with_full_downward_progress_is_not_absorption() -> None:
    records = (
        _trade(1, 100, 101.0, 4.0, AggressorSide.SELL),
        _trade(2, 200, 100.0, 4.0, AggressorSide.SELL),
        _trade(3, 300, 100.0, 1.0, AggressorSide.BUY),
    )

    result = executed_flow_response(records, (), start_ms=0, end_ms=1_000, price_step=1.0)

    assert result.absorption == pytest.approx(0.0)


def test_buy_pressure_that_fails_to_move_up_is_bearish_absorption_proxy() -> None:
    records = (
        _trade(1, 100, 101.0, 4.0, AggressorSide.BUY),
        _trade(2, 200, 101.0, 4.0, AggressorSide.BUY),
        _trade(3, 300, 100.0, 1.0, AggressorSide.SELL),
    )

    result = executed_flow_response(records, (), start_ms=0, end_ms=1_000, price_step=1.0)

    assert result.absorption < 0.0
    assert result.absorption >= -1.0


def test_down_move_with_depleted_sell_flow_at_low_is_bullish_exhaustion() -> None:
    records = (
        _trade(1, 100, 102.0, 1.0, AggressorSide.SELL),
        _trade(2, 200, 101.0, 5.0, AggressorSide.SELL),
        _trade(3, 300, 100.0, 1.0, AggressorSide.SELL),
    )
    levels = (
        _level(100.0, 0.0, 1.0),
        _level(101.0, 0.0, 5.0),
        _level(102.0, 0.0, 1.0),
    )

    result = executed_flow_response(records, levels, start_ms=0, end_ms=1_000, price_step=1.0)

    assert result.exhaustion > 0.0
    assert result.exhaustion <= 1.0


def test_up_move_with_depleted_buy_flow_at_high_is_bearish_exhaustion() -> None:
    records = (
        _trade(1, 100, 100.0, 1.0, AggressorSide.BUY),
        _trade(2, 200, 101.0, 5.0, AggressorSide.BUY),
        _trade(3, 300, 102.0, 1.0, AggressorSide.BUY),
    )
    levels = (
        _level(100.0, 1.0, 0.0),
        _level(101.0, 5.0, 0.0),
        _level(102.0, 1.0, 0.0),
    )

    result = executed_flow_response(records, levels, start_ms=0, end_ms=1_000, price_step=1.0)

    assert result.exhaustion < 0.0
    assert result.exhaustion >= -1.0


def test_missing_exact_edge_bucket_makes_exhaustion_neutral() -> None:
    records = (
        _trade(1, 100, 102.0, 2.0, AggressorSide.SELL),
        _trade(2, 200, 100.0, 1.0, AggressorSide.SELL),
    )
    levels = (
        _level(100.0, 0.0, 1.0),
        _level(102.0, 0.0, 2.0),
    )

    result = executed_flow_response(records, levels, start_ms=0, end_ms=1_000, price_step=1.0)

    assert result.exhaustion == 0.0


def test_trade_input_order_does_not_change_response() -> None:
    records = [
        _trade(10, 100, 100.0, 4.0, AggressorSide.SELL),
        _trade(11, 200, 100.0, 4.0, AggressorSide.SELL),
        _trade(12, 300, 101.0, 1.0, AggressorSide.BUY),
    ]

    first = executed_flow_response(records, (), start_ms=0, end_ms=1_000, price_step=1.0)
    second = executed_flow_response(
        list(reversed(records)), (), start_ms=0, end_ms=1_000, price_step=1.0
    )

    assert first == second


def test_insufficient_window_data_is_neutral() -> None:
    record = _trade(1, 100, 100.0, 1.0, AggressorSide.SELL)

    result = executed_flow_response((record,), (), start_ms=0, end_ms=1_000, price_step=1.0)

    assert result.absorption == 0.0
    assert result.exhaustion == 0.0


def test_duplicate_ids_and_invalid_configuration_fail_closed() -> None:
    duplicate = (
        _trade(1, 100, 100.0, 1.0, AggressorSide.SELL),
        _trade(1, 200, 100.0, 1.0, AggressorSide.SELL),
    )
    with pytest.raises(ValueError, match="unique"):
        executed_flow_response(duplicate, (), start_ms=0, end_ms=1_000, price_step=1.0)

    with pytest.raises(ValueError, match="price_step"):
        executed_flow_response((), (), start_ms=0, end_ms=1_000, price_step=0.0)
