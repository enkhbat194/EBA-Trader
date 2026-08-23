from eba_trader.momentum_engine import _closed_candles_from_payload


def _row(open_ms: int, close_ms: int, close: float, volume: float) -> list[object]:
    return [
        open_ms,
        str(close - 1.0),
        str(close + 2.0),
        str(close - 2.0),
        str(close),
        str(volume),
        close_ms,
    ]


def test_forming_candle_is_excluded_from_signal_input() -> None:
    now_ms = 10_000_000
    payload = [
        _row(index * 60_000, index * 60_000 + 59_999, 100.0 + index, 10.0 + index)
        for index in range(61)
    ]
    payload.append(_row(now_ms - 10_000, now_ms + 49_999, 999.0, 0.01))

    candles = _closed_candles_from_payload(payload, now_ms=now_ms, limit=60)

    assert len(candles) == 60
    assert candles[-1]["close"] == 160.0
    assert candles[-1]["volume"] == 70.0
    assert all(item["closeTimeMs"] < now_ms for item in candles)
