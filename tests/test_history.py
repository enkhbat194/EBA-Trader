from __future__ import annotations

import json
from urllib.error import HTTPError
from urllib.request import Request

import pytest

import eba_trader.history as history
from eba_trader.history import (
    Candle,
    candle_from_binance_row,
    find_interval_gaps,
    validate_candles,
    validate_interval_window,
)

STEP = 900_000


class FakeResponse:
    def __init__(self, payload: object):
        self.payload = payload

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def read(self) -> bytes:
        return json.dumps(self.payload).encode("utf-8")


def candle(ts: int, price: float, step: int = STEP) -> Candle:
    return Candle(
        open_time_ms=ts,
        open=price,
        high=price + 2,
        low=price - 2,
        close=price + 1,
        volume=10.0,
        close_time_ms=ts + step - 1,
        quote_volume=1000.0,
        trade_count=10,
    )


def test_public_historical_endpoint_is_market_data_only_host() -> None:
    assert history.BINANCE_KLINES_URL == "https://data-api.binance.vision/api/v3/klines"


def test_parse_binance_row() -> None:
    parsed = candle_from_binance_row(
        [1000, "100", "110", "90", "105", "12", 1999, "1234", 77, "0", "0", "0"]
    )
    assert parsed.open_time_ms == 1000
    assert parsed.close == 105.0
    assert parsed.trade_count == 77


def test_validate_rejects_duplicate_timestamp() -> None:
    with pytest.raises(ValueError, match="Duplicate"):
        validate_candles([candle(1000, 100), candle(1000, 101)])


def test_validate_rejects_negative_volume() -> None:
    row = candle(0, 100)
    invalid = Candle(
        open_time_ms=row.open_time_ms,
        open=row.open,
        high=row.high,
        low=row.low,
        close=row.close,
        volume=-1.0,
        close_time_ms=row.close_time_ms,
        quote_volume=row.quote_volume,
        trade_count=row.trade_count,
    )
    with pytest.raises(ValueError, match="volume"):
        validate_candles([invalid])


def test_validate_rejects_negative_trade_count() -> None:
    row = candle(0, 100)
    invalid = Candle(
        open_time_ms=row.open_time_ms,
        open=row.open,
        high=row.high,
        low=row.low,
        close=row.close,
        volume=row.volume,
        close_time_ms=row.close_time_ms,
        quote_volume=row.quote_volume,
        trade_count=-1,
    )
    with pytest.raises(ValueError, match="trade_count"):
        validate_candles([invalid])


def test_validate_rejects_close_before_open() -> None:
    row = candle(STEP, 100)
    invalid = Candle(
        open_time_ms=row.open_time_ms,
        open=row.open,
        high=row.high,
        low=row.low,
        close=row.close,
        volume=row.volume,
        close_time_ms=row.open_time_ms,
        quote_volume=row.quote_volume,
        trade_count=row.trade_count,
    )
    with pytest.raises(ValueError, match="after open"):
        validate_candles([invalid])


def test_gap_detector_accepts_contiguous_data() -> None:
    rows = [candle(0, 100), candle(STEP, 101), candle(2 * STEP, 102)]
    assert find_interval_gaps(rows, "15m") == []


def test_gap_detector_reports_missing_bar() -> None:
    rows = [candle(0, 100), candle(2 * STEP, 102)]
    assert find_interval_gaps(rows, "15m") == [(0, 2 * STEP)]


def test_exact_window_accepts_complete_coverage() -> None:
    rows = [candle(index * STEP, 100 + index) for index in range(4)]
    validated = validate_interval_window(rows, "15m", 0, 4 * STEP)
    assert len(validated) == 4


def test_exact_window_rejects_missing_leading_bar_without_internal_gap() -> None:
    rows = [candle(index * STEP, 100 + index) for index in range(1, 4)]
    with pytest.raises(RuntimeError, match="starts at"):
        validate_interval_window(rows, "15m", 0, 4 * STEP)


def test_exact_window_rejects_missing_trailing_bar_without_internal_gap() -> None:
    rows = [candle(index * STEP, 100 + index) for index in range(3)]
    with pytest.raises(RuntimeError, match="ends at"):
        validate_interval_window(rows, "15m", 0, 4 * STEP)


def test_exact_window_rejects_wrong_close_timestamp() -> None:
    rows = [candle(index * STEP, 100 + index) for index in range(4)]
    bad = rows[2]
    rows[2] = Candle(
        open_time_ms=bad.open_time_ms,
        open=bad.open,
        high=bad.high,
        low=bad.low,
        close=bad.close,
        volume=bad.volume,
        close_time_ms=bad.close_time_ms - 1,
        quote_volume=bad.quote_volume,
        trade_count=bad.trade_count,
    )
    with pytest.raises(RuntimeError, match="expected"):
        validate_interval_window(rows, "15m", 0, 4 * STEP)


def test_exact_window_rejects_misaligned_boundaries() -> None:
    rows = [candle(0, 100), candle(STEP, 101)]
    with pytest.raises(ValueError, match="align"):
        validate_interval_window(rows, "15m", 1, 2 * STEP)


def test_request_json_retries_rate_limit_then_succeeds(monkeypatch) -> None:
    calls = iter(
        [
            HTTPError("https://example", 429, "rate limited", {"Retry-After": "0"}, None),
            FakeResponse([[1, "ok"]]),
        ]
    )

    def fake_urlopen(request, timeout):
        value = next(calls)
        if isinstance(value, Exception):
            raise value
        return value

    monkeypatch.setattr(history, "urlopen", fake_urlopen)
    monkeypatch.setattr(history.time, "sleep", lambda seconds: None)
    payload = history._request_json(
        Request("https://example"),
        request_timeout=1.0,
        max_retries=1,
        backoff_seconds=0.0,
    )
    assert payload == [[1, "ok"]]


def test_request_json_does_not_retry_nonretryable_400(monkeypatch) -> None:
    def fake_urlopen(request, timeout):
        raise HTTPError("https://example", 400, "bad request", {}, None)

    monkeypatch.setattr(history, "urlopen", fake_urlopen)
    with pytest.raises(RuntimeError, match="400"):
        history._request_json(
            Request("https://example"),
            request_timeout=1.0,
            max_retries=5,
            backoff_seconds=0.0,
        )
