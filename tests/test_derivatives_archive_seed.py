from __future__ import annotations

import hashlib
import io
import zipfile

import pytest

import eba_trader.derivatives_archive_seed as seed
from eba_trader.derivatives_archive_seed import (
    ARCHIVE_DATASETS,
    _download_verified_archive,
    archive_url,
    month_range,
    parse_funding_archive,
    parse_kline_archive,
)


def _zip_csv(text: str) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED) as bundle:
        bundle.writestr("sample.csv", text)
    return buffer.getvalue()


def test_archive_urls_are_frozen_to_official_monthly_layout() -> None:
    funding = next(item for item in ARCHIVE_DATASETS if item.name == "funding")
    premium = next(item for item in ARCHIVE_DATASETS if item.name == "premium")
    futures = next(item for item in ARCHIVE_DATASETS if item.name == "futures")
    index = next(item for item in ARCHIVE_DATASETS if item.name == "index")

    assert archive_url(funding, 2021, 1).endswith(
        "/monthly/fundingRate/BTCUSDT/BTCUSDT-fundingRate-2021-01.zip"
    )
    assert archive_url(premium, 2024, 12).endswith(
        "/monthly/premiumIndexKlines/BTCUSDT/15m/BTCUSDT-15m-2024-12.zip"
    )
    assert archive_url(futures, 2024, 12).endswith(
        "/monthly/klines/BTCUSDT/15m/BTCUSDT-15m-2024-12.zip"
    )
    assert archive_url(index, 2024, 12).endswith(
        "/monthly/indexPriceKlines/BTCUSDT/15m/BTCUSDT-15m-2024-12.zip"
    )


def test_month_range_is_exactly_2021_through_2024() -> None:
    periods = month_range()
    assert len(periods) == 48
    assert periods[0] == (2021, 1)
    assert periods[-1] == (2024, 12)
    assert (2025, 1) not in periods


def test_archive_checksum_is_required_and_verified(monkeypatch) -> None:
    payload = b"verified archive bytes"
    expected = hashlib.sha256(payload).hexdigest()

    def fake_request(url: str, *, allow_missing: bool, **kwargs):
        if url.endswith(".CHECKSUM"):
            return f"{expected}  sample.zip\n".encode()
        return payload

    monkeypatch.setattr(seed, "_request_bytes", fake_request)
    result = _download_verified_archive("https://data.binance.vision/sample.zip")
    assert result == (payload, expected)

    def bad_checksum(url: str, *, allow_missing: bool, **kwargs):
        if url.endswith(".CHECKSUM"):
            return ("0" * 64 + "  sample.zip\n").encode()
        return payload

    monkeypatch.setattr(seed, "_request_bytes", bad_checksum)
    with pytest.raises(RuntimeError, match="checksum mismatch"):
        _download_verified_archive("https://data.binance.vision/sample.zip")


def test_funding_archive_parser_handles_header_and_three_column_schema() -> None:
    payload = _zip_csv(
        "calc_time,funding_interval_hours,last_funding_rate\n"
        "1609488000000,8,0.00010000\n"
        "1609516800000,8,-0.00005000\n"
    )
    rows = parse_funding_archive(payload)
    assert len(rows) == 2
    assert rows[0].funding_time_ms == 1609488000000
    assert rows[0].funding_rate == pytest.approx(0.0001)
    assert rows[0].rate_type == "archive_interval_hours=8"
    assert rows[1].funding_rate == pytest.approx(-0.00005)


def test_kline_archive_parser_handles_header_and_activity_fields() -> None:
    payload = _zip_csv(
        "open_time,open,high,low,close,volume,close_time,quote_volume,count,"
        "taker_buy_base_volume,taker_buy_quote_volume,ignore\n"
        "1609459200000,29000,29100,28900,29050,12.5,1609460099999,363125,42,7,203350,0\n"
    )
    rows = parse_kline_archive(payload, futures_activity=True)
    assert len(rows) == 1
    assert rows[0].open_time_ms == 1609459200000
    assert rows[0].close_time_ms == 1609460099999
    assert rows[0].volume == pytest.approx(12.5)
    assert rows[0].trade_count == 42
    assert rows[0].taker_buy_base_volume == pytest.approx(7.0)
