from __future__ import annotations

import hashlib
import io
import zipfile
from datetime import UTC, date, datetime
from pathlib import Path
from urllib.parse import urlparse

from eba_trader.candle_acquisition import USDM_KLINES_URL
from eba_trader.history import parse_utc
from eba_trader.orderflow_archive import usdm_daily_agg_trades_url
from eba_trader.orderflow_feature_dataset import load_orderflow_feature_csv
from eba_trader.strategy_factory_v2_next_dataset_workflow import (
    build_next_d0_window_feature_dataset,
)

STEP = 60_000
START = parse_utc("2026-08-22T00:15:00Z")
END = parse_utc("2026-08-23T00:00:00Z")
ORDERFLOW_START = START - STEP


def _kline(open_ms: int, index: int) -> list[object]:
    price = 50_000.0 + index * 0.25
    return [
        open_ms,
        str(price),
        str(price + 5.0),
        str(price - 5.0),
        str(price + 0.5),
        "10.0",
        open_ms + STEP - 1,
        "500000.0",
        20,
    ]


def _candle_request(calls: list[tuple[str, dict[str, object]]]):
    all_rows = [
        _kline(open_ms, index)
        for index, open_ms in enumerate(range(START, END, STEP))
    ]

    def request(endpoint: str, params):
        params = dict(params)
        calls.append((endpoint, params))
        cursor = int(params["startTime"])
        limit = int(params["limit"])
        return [row for row in all_rows if int(row[0]) >= cursor][:limit]

    return request


def _archive_blob() -> tuple[str, bytes, bytes]:
    day = date(2026, 8, 22)
    url = usdm_daily_agg_trades_url("BTCUSDT", day)
    filename = url.rsplit("/", 1)[-1]
    csv_name = filename.removesuffix(".zip") + ".csv"
    body = io.StringIO()
    body.write(
        "agg_trade_id,price,quantity,first_trade_id,last_trade_id,"
        "transact_time,is_buyer_maker\n"
    )
    trade_id = 1000
    for index, minute_ms in enumerate(range(ORDERFLOW_START, END, STEP)):
        timestamp_ms = minute_ms + 30_000
        maker = "true" if index % 2 else "false"
        body.write(
            f"{trade_id},50000.0,0.25,{trade_id},{trade_id},"
            f"{timestamp_ms},{maker}\n"
        )
        trade_id += 1
    archive = io.BytesIO()
    with zipfile.ZipFile(archive, mode="w", compression=zipfile.ZIP_DEFLATED) as handle:
        handle.writestr(csv_name, body.getvalue())
    payload = archive.getvalue()
    digest = hashlib.sha256(payload).hexdigest()
    checksum = f"{digest}  {filename}\n".encode()
    return url, payload, checksum


def test_next_d0_workflow_materializes_exact_first_window_without_oos_leak(
    tmp_path: Path,
) -> None:
    candle_calls: list[tuple[str, dict[str, object]]] = []
    archive_url, archive_payload, checksum = _archive_blob()
    archive_calls: list[str] = []

    def archive_fetch(url: str) -> bytes:
        archive_calls.append(url)
        if url == archive_url:
            return archive_payload
        if url == archive_url + ".CHECKSUM":
            return checksum
        raise AssertionError(url)

    manifest, manifest_path = build_next_d0_window_feature_dataset(
        window_name="next-d0-01",
        dataset_root=tmp_path,
        candle_request_json=_candle_request(candle_calls),
        orderflow_archive_fetch_bytes=archive_fetch,
    )

    assert manifest.authority == "D0_DATA_MATERIALIZATION_ONLY"
    assert manifest.study_phase == "d0_discovery_not_confirmation"
    assert manifest.start_ms == START
    assert manifest.end_ms == END
    assert manifest.required_orderflow_start_ms == ORDERFLOW_START
    assert ORDERFLOW_START >= parse_utc("2026-08-22T00:00:00Z")
    assert manifest.orderflow_source == "archive"
    assert manifest.row_count == (END - START) // STEP
    assert manifest_path.is_file()
    assert not Path(manifest.dataset_ref).is_absolute()

    assert candle_calls[0][0] == USDM_KLINES_URL
    assert candle_calls[0][1]["startTime"] == START
    assert archive_calls == [archive_url + ".CHECKSUM", archive_url]
    assert urlparse(archive_url).netloc == "data.binance.vision"

    rows = load_orderflow_feature_csv(tmp_path / manifest.dataset_ref)
    assert len(rows) == manifest.row_count
    assert rows[0].candle.open_time_ms == START
    assert rows[0].footprint_available_at_ms == START
    assert rows[-1].candle.open_time_ms == END - STEP


def test_next_d0_workflow_is_replay_deterministic(tmp_path: Path) -> None:
    archive_url, archive_payload, checksum = _archive_blob()

    def archive_fetch(url: str) -> bytes:
        if url == archive_url:
            return archive_payload
        if url == archive_url + ".CHECKSUM":
            return checksum
        raise AssertionError(url)

    first, first_path = build_next_d0_window_feature_dataset(
        window_name="next-d0-01",
        dataset_root=tmp_path,
        candle_request_json=_candle_request([]),
        orderflow_archive_fetch_bytes=archive_fetch,
    )
    second, second_path = build_next_d0_window_feature_dataset(
        window_name="next-d0-01",
        dataset_root=tmp_path,
        candle_request_json=_candle_request([]),
        orderflow_archive_fetch_bytes=archive_fetch,
    )
    assert first == second
    assert first_path == second_path


def test_next_d0_workflow_rejects_unknown_window_before_network(tmp_path: Path) -> None:
    candle_calls: list[tuple[str, dict[str, object]]] = []

    def archive_fetch(url: str) -> bytes:
        raise AssertionError(url)

    try:
        build_next_d0_window_feature_dataset(
            window_name="next-d0-11",
            dataset_root=tmp_path,
            candle_request_json=_candle_request(candle_calls),
            orderflow_archive_fetch_bytes=archive_fetch,
        )
    except ValueError as exc:
        assert "exactly one frozen next D0 window" in str(exc)
    else:
        raise AssertionError("unknown next D0 window should fail closed")
    assert candle_calls == []
