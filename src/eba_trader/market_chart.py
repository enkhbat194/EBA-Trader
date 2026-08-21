from __future__ import annotations

import json
import urllib.parse
import urllib.request
from dataclasses import dataclass, asdict
from typing import Any

from .providers.base import ProviderEnvironment
from .providers.binance import BINANCE_ENDPOINTS

SUPPORTED_TIMEFRAMES = {"1m", "5m", "15m", "1h"}
BINANCE_CHART_SYMBOLS = {"BTCUSDT"}
MAX_BARS = 240


@dataclass(frozen=True, slots=True)
class Candle:
    time: int
    open: float
    high: float
    low: float
    close: float
    volume: float


def _finite_positive(value: Any, field: str) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"invalid candle {field}") from exc
    if number <= 0:
        raise ValueError(f"invalid candle {field}")
    return number


def normalize_candles(raw: list[Any]) -> list[dict[str, Any]]:
    candles: list[dict[str, Any]] = []
    previous_time = -1
    for row in raw:
        if not isinstance(row, (list, tuple)) or len(row) < 6:
            raise ValueError("invalid kline row")
        timestamp = int(row[0]) // 1000
        if timestamp <= previous_time:
            raise ValueError("candles must be strictly ordered")
        candle = Candle(
            time=timestamp,
            open=_finite_positive(row[1], "open"),
            high=_finite_positive(row[2], "high"),
            low=_finite_positive(row[3], "low"),
            close=_finite_positive(row[4], "close"),
            volume=max(0.0, float(row[5])),
        )
        if candle.high < max(candle.open, candle.close) or candle.low > min(candle.open, candle.close):
            raise ValueError("invalid OHLC geometry")
        candles.append(asdict(candle))
        previous_time = timestamp
    return candles


def fetch_binance_demo_chart(symbol: str, timeframe: str, limit: int = 120) -> dict[str, Any]:
    symbol = symbol.upper().strip()
    if symbol not in BINANCE_CHART_SYMBOLS:
        raise ValueError("unsupported Binance chart symbol")
    if timeframe not in SUPPORTED_TIMEFRAMES:
        raise ValueError("unsupported timeframe")
    if limit <= 0 or limit > MAX_BARS:
        raise ValueError("invalid chart limit")

    base_url = BINANCE_ENDPOINTS[ProviderEnvironment.DEMO].spot_rest
    query = urllib.parse.urlencode({"symbol": symbol, "interval": timeframe, "limit": limit})
    request = urllib.request.Request(
        f"{base_url}/api/v3/klines?{query}",
        headers={"Accept": "application/json"},
        method="GET",
    )
    with urllib.request.urlopen(request, timeout=10.0) as response:
        payload = json.loads(response.read().decode("utf-8"))
    if not isinstance(payload, list):
        raise RuntimeError("unexpected Binance Demo kline response")
    return {
        "provider": "binance",
        "symbol": symbol,
        "timeframe": timeframe,
        "candles": normalize_candles(payload),
        "markers": [],
        "environment": "demo",
        "liveExecutionAllowed": False,
    }


def normalize_mt5_chart(snapshot: dict[str, Any], symbol: str, timeframe: str) -> dict[str, Any]:
    if timeframe not in SUPPORTED_TIMEFRAMES:
        raise ValueError("unsupported timeframe")
    charts = snapshot.get("charts")
    if not isinstance(charts, dict):
        raise ValueError("MT5 bridge has no chart data")
    symbol_charts = charts.get(symbol)
    if not isinstance(symbol_charts, dict):
        raise ValueError("MT5 symbol is not available")
    candles = symbol_charts.get(timeframe)
    if not isinstance(candles, list):
        raise ValueError("MT5 timeframe is not available")

    normalized: list[dict[str, Any]] = []
    previous_time = -1
    for item in candles[-MAX_BARS:]:
        if not isinstance(item, dict):
            raise ValueError("invalid MT5 candle")
        timestamp = int(item.get("time", 0))
        if timestamp <= previous_time:
            raise ValueError("MT5 candles must be strictly ordered")
        normalized.append(
            {
                "time": timestamp,
                "open": _finite_positive(item.get("open"), "open"),
                "high": _finite_positive(item.get("high"), "high"),
                "low": _finite_positive(item.get("low"), "low"),
                "close": _finite_positive(item.get("close"), "close"),
                "volume": max(0.0, float(item.get("volume", 0.0))),
            }
        )
        previous_time = timestamp
    return {
        "provider": "metatrader5",
        "symbol": symbol,
        "timeframe": timeframe,
        "candles": normalized,
        "markers": list(snapshot.get("markers") or []),
        "environment": "demo",
        "liveExecutionAllowed": False,
    }
