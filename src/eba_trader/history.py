from __future__ import annotations

import argparse
import csv
import json
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Iterable
from urllib.parse import urlencode
from urllib.request import Request, urlopen

BINANCE_KLINES_URL = "https://api.binance.com/api/v3/klines"
INTERVAL_MS = {
    "1m": 60_000,
    "3m": 180_000,
    "5m": 300_000,
    "15m": 900_000,
    "30m": 1_800_000,
    "1h": 3_600_000,
    "2h": 7_200_000,
    "4h": 14_400_000,
    "6h": 21_600_000,
    "8h": 28_800_000,
    "12h": 43_200_000,
    "1d": 86_400_000,
}
SUPPORTED_INTERVALS = set(INTERVAL_MS)


@dataclass(frozen=True, slots=True)
class Candle:
    open_time_ms: int
    open: float
    high: float
    low: float
    close: float
    volume: float
    close_time_ms: int
    quote_volume: float
    trade_count: int


def parse_utc(value: str) -> int:
    text = value.strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    dt = datetime.fromisoformat(text)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    return int(dt.astimezone(UTC).timestamp() * 1000)


def candle_from_binance_row(row: list[object]) -> Candle:
    if len(row) < 9:
        raise ValueError("Binance kline row is too short")
    return Candle(
        open_time_ms=int(row[0]),
        open=float(row[1]),
        high=float(row[2]),
        low=float(row[3]),
        close=float(row[4]),
        volume=float(row[5]),
        close_time_ms=int(row[6]),
        quote_volume=float(row[7]),
        trade_count=int(row[8]),
    )


def validate_candles(candles: Iterable[Candle]) -> list[Candle]:
    result = list(candles)
    if not result:
        raise ValueError("No candles supplied")

    previous = -1
    seen: set[int] = set()
    for candle in result:
        if candle.open_time_ms in seen:
            raise ValueError(f"Duplicate candle timestamp: {candle.open_time_ms}")
        if candle.open_time_ms <= previous:
            raise ValueError("Candles must be strictly increasing by open_time_ms")
        if min(candle.open, candle.high, candle.low, candle.close) <= 0:
            raise ValueError("OHLC prices must be positive")
        if candle.high < max(candle.open, candle.close):
            raise ValueError("Invalid OHLC relationship")
        if candle.low > min(candle.open, candle.close):
            raise ValueError("Invalid OHLC relationship")
        seen.add(candle.open_time_ms)
        previous = candle.open_time_ms
    return result


def find_interval_gaps(candles: Iterable[Candle], interval: str) -> list[tuple[int, int]]:
    if interval not in INTERVAL_MS:
        raise ValueError(f"Unsupported interval: {interval}")

    rows = validate_candles(candles)
    expected = INTERVAL_MS[interval]
    gaps: list[tuple[int, int]] = []
    for previous, current in zip(rows, rows[1:]):
        delta = current.open_time_ms - previous.open_time_ms
        if delta != expected:
            gaps.append((previous.open_time_ms, current.open_time_ms))
    return gaps


def fetch_binance_klines(
    symbol: str,
    interval: str,
    start_ms: int,
    end_ms: int,
    *,
    request_timeout: float = 20.0,
    pause_seconds: float = 0.08,
) -> list[Candle]:
    if interval not in SUPPORTED_INTERVALS:
        raise ValueError(f"Unsupported interval: {interval}")
    if start_ms >= end_ms:
        raise ValueError("start_ms must be earlier than end_ms")

    symbol = symbol.upper()
    cursor = start_ms
    candles: list[Candle] = []

    while cursor < end_ms:
        query = urlencode(
            {
                "symbol": symbol,
                "interval": interval,
                "startTime": cursor,
                "endTime": end_ms - 1,
                "limit": 1000,
            }
        )
        request = Request(
            f"{BINANCE_KLINES_URL}?{query}",
            headers={"User-Agent": "EBA-Trader/0.1 historical-research"},
        )
        with urlopen(request, timeout=request_timeout) as response:  # noqa: S310
            payload = json.loads(response.read().decode("utf-8"))

        if not isinstance(payload, list):
            raise RuntimeError(f"Unexpected Binance response: {payload!r}")
        if not payload:
            break

        batch = [
            candle_from_binance_row(row)
            for row in payload
            if start_ms <= int(row[0]) < end_ms
        ]
        if not batch:
            break

        candles.extend(batch)
        next_cursor = batch[-1].open_time_ms + 1
        if next_cursor <= cursor:
            raise RuntimeError("Historical pagination did not advance")
        cursor = next_cursor

        if len(payload) < 1000:
            break
        time.sleep(pause_seconds)

    return validate_candles(candles)


def save_csv(candles: Iterable[Candle], path: str | Path) -> Path:
    validated = validate_candles(candles)
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(
            [
                "open_time_ms",
                "open",
                "high",
                "low",
                "close",
                "volume",
                "close_time_ms",
                "quote_volume",
                "trade_count",
            ]
        )
        for candle in validated:
            writer.writerow(
                [
                    candle.open_time_ms,
                    candle.open,
                    candle.high,
                    candle.low,
                    candle.close,
                    candle.volume,
                    candle.close_time_ms,
                    candle.quote_volume,
                    candle.trade_count,
                ]
            )
    return output


def load_csv(path: str | Path) -> list[Candle]:
    rows: list[Candle] = []
    with Path(path).open("r", newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            rows.append(
                Candle(
                    open_time_ms=int(row["open_time_ms"]),
                    open=float(row["open"]),
                    high=float(row["high"]),
                    low=float(row["low"]),
                    close=float(row["close"]),
                    volume=float(row["volume"]),
                    close_time_ms=int(row["close_time_ms"]),
                    quote_volume=float(row["quote_volume"]),
                    trade_count=int(row["trade_count"]),
                )
            )
    return validate_candles(rows)


def download_history_cli() -> None:
    parser = argparse.ArgumentParser(description="Download Binance Spot candles for research only")
    parser.add_argument("--symbol", default="BTCUSDT")
    parser.add_argument("--interval", default="15m", choices=sorted(SUPPORTED_INTERVALS))
    parser.add_argument("--start", required=True, help="UTC ISO date/time, e.g. 2024-01-01")
    parser.add_argument("--end", required=True, help="Exclusive UTC end, e.g. 2025-01-01")
    parser.add_argument("--out", default="data/cache/btcusdt_15m.csv")
    args = parser.parse_args()

    candles = fetch_binance_klines(
        args.symbol,
        args.interval,
        parse_utc(args.start),
        parse_utc(args.end),
    )
    gaps = find_interval_gaps(candles, args.interval)
    output = save_csv(candles, args.out)
    print(
        f"saved={output} candles={len(candles)} gaps={len(gaps)} "
        f"first={candles[0].open_time_ms} last={candles[-1].open_time_ms}"
    )
