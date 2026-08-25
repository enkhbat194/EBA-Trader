from pathlib import Path

import pytest

from eba_trader.footprint_dataset import FootprintDatasetBuilder
from eba_trader.orderflow import AggressorSide
from eba_trader.orderflow_dataset import (
    OrderFlowDatasetWriter,
    normalize_aggregate_trades,
    parse_binance_agg_trade,
    sequence_gap_count,
)
from eba_trader.research_evidence import sha256_file


def _trade(
    aggregate_id: int,
    timestamp_ms: int,
    *,
    price: str = "100.0",
    quantity: str = "1.0",
    buyer_is_maker: bool = False,
) -> dict[str, object]:
    return {
        "a": aggregate_id,
        "p": price,
        "q": quantity,
        "T": timestamp_ms,
        "m": buyer_is_maker,
    }


def test_binance_maker_flag_maps_to_aggressor_side() -> None:
    aggressive_buy = parse_binance_agg_trade(_trade(1, 100, buyer_is_maker=False))
    aggressive_sell = parse_binance_agg_trade(_trade(2, 200, buyer_is_maker=True))

    assert aggressive_buy.aggressor is AggressorSide.BUY
    assert aggressive_sell.aggressor is AggressorSide.SELL


def test_normalization_is_deterministic_and_counts_sequence_gaps() -> None:
    records = normalize_aggregate_trades(
        (
            _trade(13, 300),
            _trade(10, 100),
            _trade(11, 200),
        )
    )

    assert [record.aggregate_trade_id for record in records] == [10, 11, 13]
    assert sequence_gap_count(records) == 1


def test_duplicate_and_backward_timestamp_fail_closed() -> None:
    with pytest.raises(ValueError, match="duplicate aggregate trade id"):
        normalize_aggregate_trades((_trade(1, 100), _trade(1, 100)))

    with pytest.raises(ValueError, match="conflicting duplicate aggregate trade id"):
        normalize_aggregate_trades((_trade(1, 100), _trade(1, 101)))

    with pytest.raises(ValueError, match="timestamps move backward"):
        normalize_aggregate_trades((_trade(1, 200), _trade(2, 100)))


def test_dataset_writer_is_content_addressed_and_idempotent(tmp_path: Path) -> None:
    writer = OrderFlowDatasetWriter(tmp_path)
    payloads = (_trade(1, 100), _trade(2, 200, buyer_is_maker=True))

    first = writer.write(symbol="btcusdt", payloads=payloads)
    second = writer.write(symbol="BTCUSDT", payloads=tuple(reversed(payloads)))

    assert first == second
    assert first.symbol == "BTCUSDT"
    assert first.record_count == 2
    assert first.sequence_gap_count == 0
    assert first.first_trade_id == 1
    assert first.last_trade_id == 2
    assert sha256_file(Path(first.records_path)) == first.records_sha256


def test_footprint_windows_are_end_exclusive_and_keep_empty_windows() -> None:
    records = normalize_aggregate_trades(
        (
            _trade(1, 100, quantity="2.0", buyer_is_maker=False),
            _trade(2, 999, quantity="1.0", buyer_is_maker=True),
            _trade(3, 1000, quantity="4.0", buyer_is_maker=False),
            _trade(4, 2500, quantity="3.0", buyer_is_maker=True),
        )
    )

    rows = FootprintDatasetBuilder(window_ms=1000, price_bucket=1.0).build(
        records,
        start_ms=0,
        end_ms=3000,
    )

    assert len(rows) == 3
    assert rows[0].trade_count == 2
    assert rows[0].buy_volume == pytest.approx(2.0)
    assert rows[0].sell_volume == pytest.approx(1.0)
    assert rows[0].delta == pytest.approx(1.0)

    assert rows[1].trade_count == 1
    assert rows[1].buy_volume == pytest.approx(4.0)
    assert rows[1].delta == pytest.approx(4.0)
    assert rows[1].cumulative_delta == pytest.approx(5.0)

    assert rows[2].trade_count == 1
    assert rows[2].sell_volume == pytest.approx(3.0)
    assert rows[2].delta == pytest.approx(-3.0)
    assert rows[2].cumulative_delta == pytest.approx(2.0)


def test_empty_middle_window_is_neutral() -> None:
    records = normalize_aggregate_trades((_trade(1, 100), _trade(2, 2100)))
    rows = FootprintDatasetBuilder(window_ms=1000, price_bucket=1.0).build(
        records,
        start_ms=0,
        end_ms=3000,
    )

    assert rows[1].trade_count == 0
    assert rows[1].total_volume == 0.0
    assert rows[1].delta == 0.0
    assert rows[1].poc_price is None


def test_footprint_range_must_align_exactly_to_window() -> None:
    builder = FootprintDatasetBuilder(window_ms=1000, price_bucket=1.0)
    with pytest.raises(ValueError, match="align exactly"):
        builder.build((), start_ms=0, end_ms=2500)
