from __future__ import annotations

import hashlib
import io
import json
import zipfile
from datetime import date, datetime
from pathlib import Path

import pytest

from eba_trader.orderflow_acquisition import write_acquisition_manifest
from eba_trader.orderflow_archive import (
    USDM_DAILY_AGG_TRADES_ROOT,
    fetch_binance_usdm_agg_trades_archive,
    usdm_daily_agg_trades_url,
)
from eba_trader.orderflow_dataset import OrderFlowDatasetWriter, require_research_ready

ROOT = Path(__file__).resolve().parents[1]


def _ms(value: str) -> int:
    return int(datetime.fromisoformat(value.replace("Z", "+00:00")).timestamp() * 1000)


def _archive_blob(symbol: str, day: date, rows: list[list[object]]) -> tuple[str, bytes, bytes]:
    url = usdm_daily_agg_trades_url(symbol, day)
    filename = url.rsplit("/", 1)[-1]
    csv_name = filename.removesuffix(".zip") + ".csv"
    body = io.StringIO()
    body.write(
        "agg_trade_id,price,quantity,first_trade_id,last_trade_id,"
        "transact_time,is_buyer_maker\n"
    )
    for row in rows:
        body.write(",".join(str(item) for item in row) + "\n")
    archive = io.BytesIO()
    with zipfile.ZipFile(archive, mode="w", compression=zipfile.ZIP_DEFLATED) as handle:
        handle.writestr(csv_name, body.getvalue())
    payload = archive.getvalue()
    digest = hashlib.sha256(payload).hexdigest()
    checksum = f"{digest}  {filename}\n".encode()
    return url, payload, checksum


def test_archive_url_matches_official_usdm_daily_layout() -> None:
    assert usdm_daily_agg_trades_url("btcusdt", date(2026, 8, 1)) == (
        "https://data.binance.vision/data/futures/um/daily/aggTrades/"
        "BTCUSDT/BTCUSDT-aggTrades-2026-08-01.zip"
    )


def test_archive_reader_verifies_checksum_and_spans_midnight() -> None:
    first_url, first_zip, first_checksum = _archive_blob(
        "BTCUSDT",
        date(2026, 7, 31),
        [
            [100, "50000.0", "0.1", 200, 200, _ms("2026-07-31T23:58:30Z"), "false"],
            [101, "50001.0", "0.2", 201, 201, _ms("2026-07-31T23:59:10Z"), "false"],
            [102, "50002.0", "0.3", 202, 202, _ms("2026-07-31T23:59:50Z"), "true"],
        ],
    )
    second_url, second_zip, second_checksum = _archive_blob(
        "BTCUSDT",
        date(2026, 8, 1),
        [
            [103, "50003.0", "0.4", 203, 203, _ms("2026-08-01T00:00:10Z"), "false"],
            [104, "50004.0", "0.5", 204, 204, _ms("2026-08-01T00:01:30Z"), "true"],
            [105, "50005.0", "0.6", 205, 205, _ms("2026-08-01T00:02:00Z"), "false"],
        ],
    )
    payloads = {
        first_url: first_zip,
        first_url + ".CHECKSUM": first_checksum,
        second_url: second_zip,
        second_url + ".CHECKSUM": second_checksum,
    }
    calls: list[str] = []

    def fetch(url: str) -> bytes:
        calls.append(url)
        return payloads[url]

    result = fetch_binance_usdm_agg_trades_archive(
        "btcusdt",
        _ms("2026-07-31T23:59:00Z"),
        _ms("2026-08-01T00:02:00Z"),
        fetch_bytes=fetch,
    )

    assert [row.aggregate_trade_id for row in result.records] == [101, 102, 103, 104]
    assert result.source_endpoint == USDM_DAILY_AGG_TRADES_ROOT
    assert [request.mode for request in result.requests] == [
        "archive_daily_verified",
        "archive_daily_verified",
    ]
    assert [dict(request.params)["date"] for request in result.requests] == [
        "2026-07-31",
        "2026-08-01",
    ]
    assert calls == [
        first_url + ".CHECKSUM",
        first_url,
        second_url + ".CHECKSUM",
        second_url,
    ]


def test_archive_reader_fails_closed_on_checksum_mismatch() -> None:
    url, archive, _checksum = _archive_blob(
        "BTCUSDT",
        date(2026, 8, 1),
        [[1, "50000", "1", 1, 1, _ms("2026-08-01T00:00:01Z"), "false"]],
    )
    bad_checksum = ("0" * 64 + "  " + url.rsplit("/", 1)[-1] + "\n").encode()

    def fetch(request_url: str) -> bytes:
        return bad_checksum if request_url.endswith(".CHECKSUM") else archive

    with pytest.raises(RuntimeError, match="SHA-256 mismatch"):
        fetch_binance_usdm_agg_trades_archive(
            "BTCUSDT",
            _ms("2026-08-01T00:00:00Z"),
            _ms("2026-08-01T00:01:00Z"),
            fetch_bytes=fetch,
        )


def test_archive_provenance_is_written_as_archive_not_rest(tmp_path: Path) -> None:
    url, archive, checksum = _archive_blob(
        "BTCUSDT",
        date(2026, 8, 1),
        [
            [10, "50000", "1", 10, 10, _ms("2026-08-01T00:00:01Z"), "false"],
            [11, "50001", "1", 11, 11, _ms("2026-08-01T00:00:20Z"), "true"],
        ],
    )

    def fetch(request_url: str) -> bytes:
        if request_url == url:
            return archive
        if request_url == url + ".CHECKSUM":
            return checksum
        raise AssertionError(request_url)

    download = fetch_binance_usdm_agg_trades_archive(
        "BTCUSDT",
        _ms("2026-08-01T00:00:00Z"),
        _ms("2026-08-01T00:01:00Z"),
        fetch_bytes=fetch,
    )
    dataset = OrderFlowDatasetWriter(tmp_path).write(
        symbol="BTCUSDT",
        payloads=download.payloads,
        source="binance_usd_m_futures_aggTrades_public_archive",
    )
    require_research_ready(dataset)
    manifest, path = write_acquisition_manifest(tmp_path, download=download, dataset=dataset)
    saved = json.loads(path.read_text(encoding="utf-8"))

    assert manifest.endpoint == USDM_DAILY_AGG_TRADES_ROOT
    assert saved["endpoint"] == USDM_DAILY_AGG_TRADES_ROOT
    assert saved["requests"][0]["endpoint"] == url
    assert saved["requests"][0]["mode"] == "archive_daily_verified"
    assert len(saved["requests"][0]["params"]["sha256"]) == 64


def test_fixed_real_m5_runner_uses_archive_source() -> None:
    script = (ROOT / "scripts/run_m5_real_ablation.sh").read_text(encoding="utf-8")
    assert "--orderflow-source archive" in script
    assert "final-oos" not in script.lower()
