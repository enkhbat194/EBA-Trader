import json
from pathlib import Path

import pytest

import eba_trader.orderflow_acquisition as acquisition
from eba_trader.footprint_dataset import FootprintWindowRow
from eba_trader.history import Candle
from eba_trader.orderflow_acquisition import (
    AggregateTradeDownload,
    OrderFlowVenue,
    fetch_binance_agg_trades,
    find_missing_id_ranges,
    repair_missing_id_ranges,
    write_acquisition_manifest,
)
from eba_trader.orderflow_alignment import align_closed_footprints_to_candles
from eba_trader.orderflow_dataset import OrderFlowDatasetWriter


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


def test_downloader_bootstraps_by_time_then_pages_by_id(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(acquisition, "MAX_PAGE_SIZE", 3)
    calls: list[tuple[str, dict[str, object]]] = []

    def request_json(endpoint: str, params: object) -> object:
        assert isinstance(params, dict)
        calls.append((endpoint, dict(params)))
        if "startTime" in params:
            return [_trade(10, 100), _trade(11, 200), _trade(12, 300)]
        assert params["fromId"] == 13
        return [_trade(13, 400), _trade(14, 500), _trade(15, 1000)]

    result = fetch_binance_agg_trades(
        "btcusdt",
        100,
        1000,
        venue=OrderFlowVenue.USD_M_FUTURES,
        pause_seconds=0,
        request_json=request_json,
    )

    assert result.symbol == "BTCUSDT"
    assert [record.aggregate_trade_id for record in result.records] == [10, 11, 12, 13, 14]
    assert calls[0][0] == acquisition.USDM_AGG_TRADES_URL
    assert calls[0][1] == {"symbol": "BTCUSDT", "startTime": 100, "limit": 3}
    assert calls[1][1] == {"symbol": "BTCUSDT", "fromId": 13, "limit": 3}
    assert [request.mode for request in result.requests] == ["time_bootstrap", "from_id"]


def test_missing_ranges_are_detected_and_repaired() -> None:
    initial = AggregateTradeDownload(
        symbol="BTCUSDT",
        venue=OrderFlowVenue.USD_M_FUTURES,
        start_ms=100,
        end_ms=1000,
        payloads=(_trade(10, 100), _trade(12, 300)),
        requests=(),
    )
    assert find_missing_id_ranges(initial.records) == ((11, 11),)

    def request_json(endpoint: str, params: object) -> object:
        assert endpoint == acquisition.USDM_AGG_TRADES_URL
        assert params == {"symbol": "BTCUSDT", "fromId": 11, "limit": 1}
        return [_trade(11, 200)]

    repaired = repair_missing_id_ranges(initial, request_json=request_json)
    assert [record.aggregate_trade_id for record in repaired.records] == [10, 11, 12]
    assert find_missing_id_ranges(repaired.records) == ()
    assert repaired.requests[-1].mode == "repair_from_id"


def test_unresolved_gap_remains_visible() -> None:
    initial = AggregateTradeDownload(
        symbol="BTCUSDT",
        venue=OrderFlowVenue.USD_M_FUTURES,
        start_ms=100,
        end_ms=1000,
        payloads=(_trade(10, 100), _trade(12, 300)),
        requests=(),
    )

    repaired = repair_missing_id_ranges(
        initial,
        request_json=lambda _endpoint, _params: [],
    )
    assert find_missing_id_ranges(repaired.records) == ((11, 11),)


def test_acquisition_manifest_links_request_provenance_to_dataset(tmp_path: Path) -> None:
    download = AggregateTradeDownload(
        symbol="BTCUSDT",
        venue=OrderFlowVenue.SPOT,
        start_ms=100,
        end_ms=300,
        payloads=(_trade(1, 100), _trade(2, 200)),
        requests=(),
    )
    dataset = OrderFlowDatasetWriter(tmp_path).write(
        symbol="BTCUSDT",
        payloads=download.payloads,
        source="binance_spot_aggTrades",
    )

    manifest, path = write_acquisition_manifest(tmp_path, download=download, dataset=dataset)
    saved = json.loads(path.read_text(encoding="utf-8"))

    assert manifest.dataset_id == dataset.dataset_id
    assert manifest.venue == "spot"
    assert saved["requested_start_ms"] == 100
    assert saved["requested_end_ms"] == 300
    assert saved["requests"] == []


def _candle(open_ms: int) -> Candle:
    return Candle(
        open_time_ms=open_ms,
        open=100.0,
        high=101.0,
        low=99.0,
        close=100.5,
        volume=10.0,
        close_time_ms=open_ms + 59_999,
        quote_volume=1000.0,
        trade_count=5,
    )


def _footprint(start_ms: int, end_ms: int, delta: float) -> FootprintWindowRow:
    return FootprintWindowRow(
        start_ms=start_ms,
        end_ms=end_ms,
        buy_volume=max(delta, 0.0),
        sell_volume=max(-delta, 0.0),
        delta=delta,
        delta_ratio=0.0,
        total_volume=abs(delta),
        trade_count=1,
        poc_price=100.0,
        cumulative_delta=delta,
    )


def test_alignment_uses_only_footprint_closed_before_candle_open() -> None:
    candles = [_candle(60_000), _candle(120_000)]
    footprints = [
        _footprint(0, 60_000, 1.0),
        _footprint(60_000, 120_000, 2.0),
    ]

    aligned = align_closed_footprints_to_candles(
        candles,
        footprints,
        interval="1m",
    )

    assert [row.candle.open_time_ms for row in aligned] == [60_000, 120_000]
    assert [row.footprint.delta for row in aligned] == [1.0, 2.0]
    assert all(row.available_at_ms == row.candle.open_time_ms for row in aligned)


def test_alignment_fails_closed_when_prior_footprint_is_missing() -> None:
    with pytest.raises(ValueError, match="missing closed footprint"):
        align_closed_footprints_to_candles(
            [_candle(60_000)],
            [],
            interval="1m",
        )


def test_alignment_rejects_mismatched_window_width() -> None:
    with pytest.raises(ValueError, match="width"):
        align_closed_footprints_to_candles(
            [_candle(60_000)],
            [_footprint(0, 30_000, 1.0)],
            interval="1m",
        )
