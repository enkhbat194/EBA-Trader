from __future__ import annotations

import pytest

from eba_trader.history import Candle, candle_from_binance_row, validate_candles


def candle(ts: int, price: float) -> Candle:
    return Candle(
        open_time_ms=ts,
        open=price,
        high=price + 2,
        low=price - 2,
        close=price + 1,
        volume=10.0,
        close_time_ms=ts + 59_999,
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


def test_validate_accepts_strictly_increasing_candles() -> None:
    rows = validate_candles([candle(1000, 100), candle(2000, 101)])
    assert len(rows) == 2
