import pytest

from eba_trader.market_chart import normalize_candles, normalize_mt5_chart


def test_normalize_binance_klines_to_chart_candles() -> None:
    result = normalize_candles(
        [
            [1_700_000_000_000, "100", "103", "99", "102", "12.5"],
            [1_700_000_060_000, "102", "104", "101", "103", "11.0"],
        ]
    )
    assert result[0] == {
        "time": 1_700_000_000,
        "open": 100.0,
        "high": 103.0,
        "low": 99.0,
        "close": 102.0,
        "volume": 12.5,
    }
    assert result[1]["time"] > result[0]["time"]


def test_normalize_mt5_chart_keeps_provider_neutral_shape() -> None:
    snapshot = {
        "charts": {
            "XAUUSD": {
                "15m": [
                    {
                        "time": 1_700_000_000,
                        "open": 2000.0,
                        "high": 2005.0,
                        "low": 1998.0,
                        "close": 2003.0,
                        "volume": 100,
                    },
                    {
                        "time": 1_700_000_900,
                        "open": 2003.0,
                        "high": 2008.0,
                        "low": 2002.0,
                        "close": 2007.0,
                        "volume": 120,
                    },
                ]
            }
        },
        "markers": [],
    }
    result = normalize_mt5_chart(snapshot, "XAUUSD", "15m")
    assert result["provider"] == "metatrader5"
    assert result["symbol"] == "XAUUSD"
    assert result["candles"][-1]["close"] == 2007.0
    assert result["liveExecutionAllowed"] is False


def test_chart_rejects_bad_geometry_and_timeframe() -> None:
    with pytest.raises(ValueError, match="OHLC"):
        normalize_candles([[1_700_000_000_000, "100", "99", "98", "101", "1"]])
    with pytest.raises(ValueError, match="unsupported timeframe"):
        normalize_mt5_chart({"charts": {}}, "XAUUSD", "2m")
