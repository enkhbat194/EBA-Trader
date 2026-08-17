from __future__ import annotations

import pytest

from eba_trader.history import (
    Candle,
    candle_from_binance_row,
    find_interval_gaps,
    validate_candles,
    validate_interval_window,
)

STEP = 900_000


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


def test_exact_window_rejects_misaligned_boundaries() -> None:
    rows = [candle(0, 100), candle(STEP, 101)]
    with pytest.raises(ValueError, match="align"):
        validate_interval_window(rows, "15m", 1, 2 * STEP)
