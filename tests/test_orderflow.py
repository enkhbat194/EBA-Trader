import pytest

from eba_trader.orderflow import (
    AggressorSide,
    TradeEvent,
    TradeFlowAggregator,
    cumulative_delta,
)


def test_trade_flow_aggregation_delta_levels_and_poc() -> None:
    aggregator = TradeFlowAggregator(price_bucket=1.0)
    events = [
        TradeEvent(100, 100.2, 2.0, AggressorSide.BUY),
        TradeEvent(200, 100.8, 1.0, AggressorSide.SELL),
        TradeEvent(300, 101.1, 4.0, AggressorSide.BUY),
        TradeEvent(1200, 101.2, 99.0, AggressorSide.SELL),
    ]

    result = aggregator.aggregate(events, start_ms=0, end_ms=1000)

    assert result.trade_count == 3
    assert result.buy_volume == pytest.approx(6.0)
    assert result.sell_volume == pytest.approx(1.0)
    assert result.delta == pytest.approx(5.0)
    assert result.delta_ratio == pytest.approx(5.0 / 7.0)
    assert result.poc_price == pytest.approx(101.0)
    assert [(level.price, level.buy_volume, level.sell_volume) for level in result.levels] == [
        (100.0, 2.0, 1.0),
        (101.0, 4.0, 0.0),
    ]


def test_window_is_end_exclusive_and_input_order_does_not_change_result() -> None:
    aggregator = TradeFlowAggregator(price_bucket=0.5)
    events = [
        TradeEvent(999, 10.9, 1.0, AggressorSide.SELL),
        TradeEvent(1000, 10.9, 10.0, AggressorSide.BUY),
        TradeEvent(1, 10.1, 2.0, AggressorSide.BUY),
    ]

    first = aggregator.aggregate(events, start_ms=0, end_ms=1000)
    second = aggregator.aggregate(list(reversed(events)), start_ms=0, end_ms=1000)

    assert first == second
    assert first.trade_count == 2
    assert first.total_volume == pytest.approx(3.0)


def test_empty_window_is_neutral_not_nan() -> None:
    result = TradeFlowAggregator(price_bucket=1.0).aggregate([], start_ms=0, end_ms=1000)

    assert result.total_volume == 0.0
    assert result.delta == 0.0
    assert result.delta_ratio == 0.0
    assert result.poc_price is None
    assert result.levels == ()


def test_cumulative_delta_is_ordered_and_rejects_overlap() -> None:
    aggregator = TradeFlowAggregator(price_bucket=1.0)
    first = aggregator.aggregate(
        [TradeEvent(100, 100.0, 3.0, AggressorSide.BUY)],
        start_ms=0,
        end_ms=1000,
    )
    second = aggregator.aggregate(
        [TradeEvent(1100, 100.0, 1.0, AggressorSide.SELL)],
        start_ms=1000,
        end_ms=2000,
    )

    assert cumulative_delta((first, second)) == pytest.approx((3.0, 2.0))

    overlapping = aggregator.aggregate([], start_ms=900, end_ms=1500)
    with pytest.raises(ValueError, match="ordered and non-overlapping"):
        cumulative_delta((first, overlapping))


@pytest.mark.parametrize(
    "event",
    [
        lambda: TradeEvent(-1, 100.0, 1.0, AggressorSide.BUY),
        lambda: TradeEvent(1, 0.0, 1.0, AggressorSide.BUY),
        lambda: TradeEvent(1, 100.0, 0.0, AggressorSide.BUY),
    ],
)
def test_invalid_trade_events_fail_closed(event) -> None:
    with pytest.raises(ValueError):
        event()
