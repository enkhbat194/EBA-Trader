from __future__ import annotations

import argparse
import csv
import json
import time
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from .holdout_guard import assert_not_first_cycle_oos_overlap

BINANCE_KLINES_URL = "https://data-api.binance.vision/api/v3/klines"
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
        if candle.open_time_ms < 0 or candle.close_time_ms < 0:
            raise ValueError("Candle timestamps cannot be negative")
        if candle.open_time_ms in seen:
            raise ValueError(f"Duplicate candle timestamp: {candle.open_time_ms}")
        if candle.open_time_ms <= previous:
            raise ValueError("Candles must be strictly increasing by open_time_ms")
        if candle.close_time_ms <= candle.open_time_ms:
            raise ValueError("Candle close_time_ms must be after open_time_ms")
        if min(candle.open, candle.high, candle.low, candle.close) <= 0:
            raise ValueError("OHLC prices must be positive")
        if candle.high < max(candle.open, candle.close):
            raise ValueError("Invalid OHLC relationship")
        if candle.low > min(candle.open, candle.close):
            raise ValueError("Invalid OHLC relationship")
        if candle.volume < 0 or candle.quote_volume < 0:
            raise ValueError("Candle volume cannot be negative")
        if candle.trade_count < 0:
            raise ValueError("Candle trade_count cannot be negative")
        seen.add(candle.open_time_ms)
        previous = candle.open_time_ms
    return result


def find_interval_gaps(candles: Iterable[Candle], interval: str) -> list[tuple[int, int]]:
    if interval not in INTERVAL_MS:
        raise ValueError(f"Unsupported interval: {interval}")

    rows = validate_candles(candles)
    expected = INTERVAL_MS[interval]
    gaps: list[tuple[int, int]] = []
    for previous, current in zip(rows, rows[1:], strict=False):
        delta = current.open_time_ms - previous.open_time_ms
        if delta != expected:
            gaps.append((previous.open_time_ms, current.open_time_ms))
    return gaps


def validate_interval_window(
    candles: Iterable[Candle],
    interval: str,
    start_ms: int,
    end_ms: int,
    *,
    allowed_missing_ranges: Iterable[tuple[int, int]] = (),
) -> list[Candle]:
    """Validate exact [start_ms, end_ms) coverage for a fixed-interval dataset."""
    if interval not in INTERVAL_MS:
        raise ValueError(f"Unsupported interval: {interval}")
    if start_ms >= end_ms:
        raise ValueError("start_ms must be earlier than end_ms")

    step = INTERVAL_MS[interval]
    if start_ms % step != 0 or end_ms % step != 0:
        raise ValueError("Research window boundaries must align to the requested interval")
    duration = end_ms - start_ms
    if duration % step != 0:
        raise ValueError("Research window length must be an exact interval multiple")

    rows = validate_candles(candles)
    expected_last_open = end_ms - step
    if rows[0].open_time_ms != start_ms:
        raise RuntimeError(
            f"Historical window starts at {rows[0].open_time_ms}, expected {start_ms}"
        )
    if rows[-1].open_time_ms != expected_last_open:
        raise RuntimeError(
            f"Historical window ends at {rows[-1].open_time_ms}, expected {expected_last_open}"
        )
    gaps = find_interval_gaps(rows, interval)
    allowed = set(allowed_missing_ranges)
    actual_missing_ranges = [(previous + step, current) for previous, current in gaps]
    unexpected = [gap for gap in actual_missing_ranges if gap not in allowed]
    if unexpected:
        raise RuntimeError(f"Historical window contains {len(unexpected)} unexpected interval gaps")

    missing_count = sum((end - start) // step for start, end in actual_missing_ranges)
    expected_count = duration // step - missing_count
    if len(rows) != expected_count:
        raise RuntimeError(
            f"Historical window has {len(rows)} candles, expected {expected_count} "
            "after allowed source gaps"
        )

    for candle in rows:
        expected_close = candle.open_time_ms + step - 1
        if candle.close_time_ms != expected_close:
            raise RuntimeError(
                f"Candle at {candle.open_time_ms} closes at {candle.close_time_ms}, "
                f"expected {expected_close} for {interval}"
            )
    return rows


def _retry_delay_seconds(error: HTTPError, attempt: int, backoff_seconds: float) -> float:
    retry_after = error.headers.get("Retry-After") if error.headers is not None else None
    if retry_after:
        try:
            return min(max(float(retry_after), 0.0), 120.0)
        except ValueError:
            pass
    return min(backoff_seconds * (2**attempt), 30.0)


def _request_json(
    request: Request,
    *,
    request_timeout: float,
    max_retries: int,
    backoff_seconds: float,
) -> object:
    if max_retries < 0:
        raise ValueError("max_retries cannot be negative")
    if backoff_seconds < 0:
        raise ValueError("backoff_seconds cannot be negative")

    for attempt in range(max_retries + 1):
        try:
            with urlopen(request, timeout=request_timeout) as response:  # noqa: S310
                return json.loads(response.read().decode("utf-8"))
        except HTTPError as error:
            retryable = error.code in {418, 429} or 500 <= error.code < 600
            if not retryable or attempt >= max_retries:
                raise RuntimeError(f"Binance HTTP error {error.code}") from error
            time.sleep(_retry_delay_seconds(error, attempt, backoff_seconds))
        except (URLError, TimeoutError) as error:
            if attempt >= max_retries:
                raise RuntimeError("Binance network request failed after retries") from error
            time.sleep(min(backoff_seconds * (2**attempt), 30.0))

    raise RuntimeError("Unreachable retry state")


def fetch_binance_klines(
    symbol: str,
    interval: str,
    start_ms: int,
    end_ms: int,
    *,
    request_timeout: float = 20.0,
    pause_seconds: float = 0.08,
    max_retries: int = 5,
    backoff_seconds: float = 0.5,
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
        payload = _request_json(
            request,
            request_timeout=request_timeout,
            max_retries=max_retries,
            backoff_seconds=backoff_seconds,
        )

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

    start_ms = parse_utc(args.start)
    end_ms = parse_utc(args.end)
    assert_not_first_cycle_oos_overlap(
        symbol=args.symbol,
        interval=args.interval,
        start_ms=start_ms,
        end_ms=end_ms,
        context="Generic historical downloader",
    )
    candles = fetch_binance_klines(
        args.symbol,
        args.interval,
        start_ms,
        end_ms,
    )
    candles = validate_interval_window(candles, args.interval, start_ms, end_ms)
    output = save_csv(candles, args.out)
    print(
        f"saved={output} candles={len(candles)} coverage=EXACT "
        f"first={candles[0].open_time_ms} last={candles[-1].open_time_ms}"
    )
