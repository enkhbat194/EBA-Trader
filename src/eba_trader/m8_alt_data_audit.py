from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import math
import time
import zipfile
from bisect import bisect_right
from collections.abc import Callable, Iterable
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import asdict, dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from .history import parse_utc
from .holdout_guard import assert_not_first_cycle_oos_overlap
from .m8_alt_data_policy import (
    AUDIT_END_EXCLUSIVE,
    AUDIT_START,
    BINANCE_METRICS_MAX_MISSING_SLOTS,
    BINANCE_METRICS_MIN_COVERAGE,
    BINANCE_VISION_BASE,
    BOOK_DEPTH_MIN_DAILY_FILE_COVERAGE,
    BOOK_DEPTH_START,
    BYBIT_BASE,
    BYBIT_KLINE_MAX_MISSING_HOURS,
    BYBIT_KLINE_MIN_COVERAGE,
    BYBIT_POSITIONING_MAX_MISSING_HOURS,
    BYBIT_POSITIONING_MIN_COVERAGE,
    CROSS_EXCHANGE_MIN_HOURLY_ALIGNMENT,
    DAY_MS,
    FIVE_MIN_MS,
    HOUR_MS,
    LIQUIDATION_MIN_DAILY_FILE_COVERAGE,
    SYMBOL,
    sha256_bytes,
    verify_m8_audit_freeze,
)
from .provenance import collect_source_provenance

METRICS_COLUMNS = (
    "create_time",
    "symbol",
    "sum_open_interest",
    "sum_open_interest_value",
    "count_toptrader_long_short_ratio",
    "sum_toptrader_long_short_ratio",
    "count_long_short_ratio",
    "sum_taker_long_short_vol_ratio",
)


@dataclass(frozen=True, slots=True)
class BinanceMetric:
    timestamp_ms: int
    sum_open_interest: float
    sum_open_interest_value: float
    count_toptrader_long_short_ratio: float
    sum_toptrader_long_short_ratio: float
    count_long_short_ratio: float
    sum_taker_long_short_vol_ratio: float


@dataclass(frozen=True, slots=True)
class BybitKline:
    timestamp_ms: int
    open: float
    high: float
    low: float
    close: float
    volume: float
    turnover: float


@dataclass(frozen=True, slots=True)
class BybitOpenInterest:
    timestamp_ms: int
    open_interest: float


@dataclass(frozen=True, slots=True)
class BybitAccountRatio:
    timestamp_ms: int
    buy_ratio: float
    sell_ratio: float


@dataclass(frozen=True, slots=True)
class BybitFunding:
    timestamp_ms: int
    funding_rate: float


@dataclass(frozen=True, slots=True)
class DailyArchiveAudit:
    family: str
    start_date: str
    end_date_exclusive: str
    expected_files: int
    existing_files: int
    checksum_verified_files: int
    missing_files: int
    parse_error_files: int
    row_count: int
    invalid_rows: int
    exact_duplicate_rows: int
    conflicting_duplicates: int
    first_timestamp_ms: int | None
    last_timestamp_ms: int | None
    cadence_observations: int
    cadence_within_limit: int


def _guard_window(start_ms: int, end_ms: int, *, context: str) -> None:
    audit_start = parse_utc(AUDIT_START)
    audit_end = parse_utc(AUDIT_END_EXCLUSIVE)
    if start_ms < audit_start or end_ms > audit_end or start_ms >= end_ms:
        raise RuntimeError(f"{context} is outside the frozen M8 development audit window")
    assert_not_first_cycle_oos_overlap(
        symbol=SYMBOL,
        interval="M8-public-market-data",
        start_ms=start_ms,
        end_ms=end_ms,
        context=context,
    )


def _retry_sleep(attempt: int, base: float) -> None:
    time.sleep(min(base * (2**attempt), 20.0))


def _request_bytes(
    url: str,
    *,
    allow_missing: bool,
    timeout: float = 30.0,
    max_retries: int = 4,
    backoff_seconds: float = 0.5,
) -> bytes | None:
    request = Request(url, headers={"User-Agent": "EBA-Trader-M8-Audit/1.0"})
    for attempt in range(max_retries + 1):
        try:
            with urlopen(request, timeout=timeout) as response:  # noqa: S310
                return response.read()
        except HTTPError as error:
            if error.code == 404 and allow_missing:
                return None
            retryable = error.code in {403, 418, 429} or 500 <= error.code < 600
            if not retryable or attempt >= max_retries:
                raise RuntimeError(f"HTTP error {error.code}: {url}") from error
            _retry_sleep(attempt, backoff_seconds)
        except (URLError, TimeoutError) as error:
            if attempt >= max_retries:
                raise RuntimeError(f"Network request failed after retries: {url}") from error
            _retry_sleep(attempt, backoff_seconds)
    raise RuntimeError("Unreachable request retry state")


def _request_json(
    path: str,
    params: dict[str, object],
    *,
    timeout: float = 30.0,
    max_retries: int = 4,
    backoff_seconds: float = 0.5,
) -> dict[str, Any]:
    url = f"{BYBIT_BASE}{path}?{urlencode(params)}"
    payload = _request_bytes(
        url,
        allow_missing=False,
        timeout=timeout,
        max_retries=max_retries,
        backoff_seconds=backoff_seconds,
    )
    if payload is None:
        raise RuntimeError(f"Unexpected missing Bybit response: {url}")
    try:
        decoded = json.loads(payload.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise RuntimeError("Invalid Bybit JSON response") from error
    if not isinstance(decoded, dict):
        raise RuntimeError("Unexpected Bybit response type")
    if decoded.get("retCode") != 0:
        raise RuntimeError(
            f"Bybit API rejected request: retCode={decoded.get('retCode')} "
            f"retMsg={decoded.get('retMsg')!r}"
        )
    return decoded


def _checksum_value(payload: bytes) -> str:
    text = payload.decode("utf-8-sig").strip()
    if not text:
        raise RuntimeError("Empty Binance Vision CHECKSUM file")
    token = text.split()[0].lower()
    if len(token) != 64 or any(char not in "0123456789abcdef" for char in token):
        raise RuntimeError("Invalid Binance Vision CHECKSUM format")
    return token


def _download_verified_archive(url: str) -> tuple[bytes, str] | None:
    payload = _request_bytes(url, allow_missing=True)
    if payload is None:
        return None
    checksum_payload = _request_bytes(url + ".CHECKSUM", allow_missing=False)
    if checksum_payload is None:
        raise RuntimeError(f"Missing checksum for existing archive: {url}")
    expected = _checksum_value(checksum_payload)
    actual = sha256_bytes(payload)
    if actual != expected:
        raise RuntimeError(f"Binance Vision checksum mismatch: {url}")
    return payload, actual


def _csv_rows_from_zip(payload: bytes) -> list[list[str]]:
    try:
        with zipfile.ZipFile(io.BytesIO(payload)) as bundle:
            members = [name for name in bundle.namelist() if name.lower().endswith(".csv")]
            if len(members) != 1:
                raise RuntimeError("Expected exactly one CSV inside Binance Vision ZIP")
            with bundle.open(members[0]) as raw:
                text = io.TextIOWrapper(raw, encoding="utf-8-sig", newline="")
                return [row for row in csv.reader(text) if row]
    except zipfile.BadZipFile as error:
        raise RuntimeError("Invalid Binance Vision ZIP payload") from error


def _parse_timestamp(value: str) -> int:
    text = value.strip()
    if not text:
        raise ValueError("empty timestamp")
    try:
        numeric = float(text)
    except ValueError:
        normalized = text.replace("Z", "+00:00")
        dt = datetime.fromisoformat(normalized)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=UTC)
        return int(dt.astimezone(UTC).timestamp() * 1000)

    magnitude = abs(numeric)
    if magnitude >= 1e17:
        return int(numeric / 1_000_000)
    if magnitude >= 1e14:
        return int(numeric / 1_000)
    if magnitude >= 1e11:
        return int(numeric)
    return int(numeric * 1000)


def _date_range(start_text: str, end_text: str) -> tuple[str, ...]:
    start = datetime.fromtimestamp(parse_utc(start_text) / 1000.0, tz=UTC).date()
    end = datetime.fromtimestamp(parse_utc(end_text) / 1000.0, tz=UTC).date()
    result: list[str] = []
    current = start
    while current < end:
        result.append(current.isoformat())
        current += timedelta(days=1)
    return tuple(result)


def _max_missing_run(timestamps: Iterable[int], start_ms: int, end_ms: int, step_ms: int) -> int:
    observed = set(timestamps)
    current_run = 0
    maximum = 0
    cursor = start_ms
    while cursor < end_ms:
        if cursor in observed:
            current_run = 0
        else:
            current_run += 1
            maximum = max(maximum, current_run)
        cursor += step_ms
    return maximum


def _expected_slots(start_ms: int, end_ms: int, step_ms: int) -> int:
    if start_ms >= end_ms:
        return 0
    return (end_ms - start_ms + step_ms - 1) // step_ms


def _normalized_hash(rows: Iterable[object]) -> str:
    digest = hashlib.sha256()
    for row in rows:
        payload = asdict(row) if hasattr(row, "__dataclass_fields__") else row
        digest.update(
            json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False).encode(
                "utf-8"
            )
        )
        digest.update(b"\n")
    return digest.hexdigest()


def parse_binance_metrics_rows(
    rows: list[list[str]],
    *,
    start_ms: int,
    end_ms: int,
) -> tuple[list[BinanceMetric], int, int]:
    if not rows:
        return [], 0, 0
    header_map: dict[str, int] | None = None
    first = [item.strip() for item in rows[0]]
    if first and first[0].lower() == "create_time":
        header_map = {name.strip(): index for index, name in enumerate(first)}
        missing = [name for name in METRICS_COLUMNS if name not in header_map]
        if missing:
            raise RuntimeError(f"Binance metrics archive missing columns: {missing}")
        data_rows = rows[1:]
    else:
        data_rows = rows

    seen: dict[int, BinanceMetric] = {}
    exact_duplicates = 0
    conflicting_duplicates = 0
    for row in data_rows:
        if row and row[0].strip().lower() == "create_time":
            continue
        try:
            if header_map is None:
                if len(row) < len(METRICS_COLUMNS):
                    raise ValueError("short metrics row")
                values = {name: row[index] for index, name in enumerate(METRICS_COLUMNS)}
            else:
                values = {name: row[index] for name, index in header_map.items()}
            if values["symbol"].strip().upper() != SYMBOL:
                raise ValueError("unexpected symbol")
            timestamp_ms = _parse_timestamp(values["create_time"])
            if not start_ms < timestamp_ms < end_ms:
                raise ValueError("metrics timestamp outside frozen window")
            metric = BinanceMetric(
                timestamp_ms=timestamp_ms,
                sum_open_interest=float(values["sum_open_interest"]),
                sum_open_interest_value=float(values["sum_open_interest_value"]),
                count_toptrader_long_short_ratio=float(values["count_toptrader_long_short_ratio"]),
                sum_toptrader_long_short_ratio=float(values["sum_toptrader_long_short_ratio"]),
                count_long_short_ratio=float(values["count_long_short_ratio"]),
                sum_taker_long_short_vol_ratio=float(values["sum_taker_long_short_vol_ratio"]),
            )
        except (KeyError, IndexError, TypeError, ValueError) as error:
            raise RuntimeError(f"Invalid Binance metrics row: {row!r}") from error

        previous = seen.get(timestamp_ms)
        if previous is None:
            seen[timestamp_ms] = metric
        elif previous == metric:
            exact_duplicates += 1
        else:
            conflicting_duplicates += 1
    return [seen[key] for key in sorted(seen)], exact_duplicates, conflicting_duplicates


def _binance_daily_url(family: str, date_text: str) -> str:
    filename = f"{SYMBOL}-{family}-{date_text}.zip"
    return f"{BINANCE_VISION_BASE}/{family}/{SYMBOL}/{filename}"


def _download_metrics_day(date_text: str) -> tuple[str, str | None, list[list[str]]]:
    url = _binance_daily_url("metrics", date_text)
    downloaded = _download_verified_archive(url)
    if downloaded is None:
        return date_text, None, []
    payload, checksum = downloaded
    return date_text, checksum, _csv_rows_from_zip(payload)


def fetch_binance_metrics(
    *,
    workers: int = 8,
) -> tuple[list[BinanceMetric], dict[str, object]]:
    start_ms = parse_utc(AUDIT_START)
    end_ms = parse_utc(AUDIT_END_EXCLUSIVE)
    _guard_window(start_ms, end_ms, context="M8 Binance metrics archive audit")
    if workers < 1 or workers > 16:
        raise ValueError("workers must be between 1 and 16")
    dates = _date_range(AUDIT_START, AUDIT_END_EXCLUSIVE)
    downloaded: list[tuple[str, str | None, list[list[str]]]] = []
    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = {executor.submit(_download_metrics_day, date): date for date in dates}
        for future in as_completed(futures):
            downloaded.append(future.result())

    all_rows: list[list[str]] = []
    verified = 0
    missing_files: list[str] = []
    for date_text, checksum, rows in sorted(downloaded):
        if checksum is None:
            missing_files.append(date_text)
            continue
        verified += 1
        all_rows.extend(rows)

    metrics, exact_duplicates, conflicts = parse_binance_metrics_rows(
        all_rows,
        start_ms=start_ms,
        end_ms=end_ms,
    )
    metadata: dict[str, object] = {
        "expected_daily_files": len(dates),
        "existing_daily_files": verified,
        "checksum_verified_files": verified,
        "missing_daily_files": len(missing_files),
        "missing_file_dates": missing_files,
        "exact_duplicate_timestamps_collapsed": exact_duplicates,
        "conflicting_duplicate_timestamps": conflicts,
    }
    return metrics, metadata


def audit_binance_metrics(
    metrics: list[BinanceMetric] | tuple[BinanceMetric, ...],
    metadata: dict[str, object] | None = None,
) -> dict[str, object]:
    start_ms = parse_utc(AUDIT_START) + FIVE_MIN_MS
    end_ms = parse_utc(AUDIT_END_EXCLUSIVE)
    expected = _expected_slots(start_ms, end_ms, FIVE_MIN_MS)
    timestamps = [item.timestamp_ms for item in metrics]
    unique = len(timestamps) == len(set(timestamps))
    aligned = all(timestamp % FIVE_MIN_MS == 0 for timestamp in timestamps)
    ordered = all(left < right for left, right in zip(timestamps, timestamps[1:], strict=False))
    finite_positive = all(
        all(
            math.isfinite(value) and value > 0
            for value in asdict(item).values()
            if isinstance(value, float)
        )
        for item in metrics
    )
    conflicts = int((metadata or {}).get("conflicting_duplicate_timestamps", 0))
    coverage = len(timestamps) / expected if expected else 0.0
    max_missing = _max_missing_run(timestamps, start_ms, end_ms, FIVE_MIN_MS)
    passed = (
        unique
        and aligned
        and ordered
        and finite_positive
        and conflicts == 0
        and coverage >= BINANCE_METRICS_MIN_COVERAGE
        and max_missing <= BINANCE_METRICS_MAX_MISSING_SLOTS
    )
    return {
        "status": "FULL_WINDOW_PASS" if passed else "FAIL",
        "row_count": len(metrics),
        "expected_slots": expected,
        "coverage": coverage,
        "max_missing_five_minute_slots": max_missing,
        "timestamps_unique": unique,
        "timestamps_aligned": aligned,
        "timestamps_strictly_increasing": ordered,
        "all_metric_fields_finite_and_positive": finite_positive,
        "conflicting_duplicate_timestamps": conflicts,
        "first_timestamp_ms": timestamps[0] if timestamps else None,
        "last_timestamp_ms": timestamps[-1] if timestamps else None,
        "normalized_sha256": _normalized_hash(metrics),
        "archive": metadata or {},
    }


def _result_list(payload: dict[str, Any]) -> tuple[list[Any], str]:
    result = payload.get("result")
    if not isinstance(result, dict):
        raise RuntimeError("Bybit response is missing result object")
    rows = result.get("list", [])
    if not isinstance(rows, list):
        raise RuntimeError("Bybit result list is invalid")
    cursor = result.get("nextPageCursor") or ""
    return rows, str(cursor)


def _fetch_bybit_windowed(
    path: str,
    *,
    start_ms: int,
    end_ms: int,
    chunk_ms: int,
    base_params: dict[str, object],
    limit: int,
) -> list[Any]:
    _guard_window(start_ms, end_ms, context=f"M8 Bybit {path}")
    collected: list[Any] = []
    cursor_start = start_ms
    while cursor_start < end_ms:
        cursor_end = min(cursor_start + chunk_ms, end_ms)
        page_cursor = ""
        seen_cursors: set[str] = set()
        while True:
            params = {
                **base_params,
                "startTime": cursor_start,
                "endTime": cursor_end - 1,
                "limit": limit,
            }
            if page_cursor:
                params["cursor"] = page_cursor
            payload = _request_json(path, params)
            rows, next_cursor = _result_list(payload)
            collected.extend(rows)
            if not next_cursor:
                break
            if next_cursor in seen_cursors:
                raise RuntimeError("Bybit pagination cursor did not advance")
            seen_cursors.add(next_cursor)
            page_cursor = next_cursor
        cursor_start = cursor_end
    return collected


def fetch_bybit_klines() -> list[BybitKline]:
    start_ms = parse_utc(AUDIT_START)
    end_ms = parse_utc(AUDIT_END_EXCLUSIVE)
    raw = _fetch_bybit_windowed(
        "/v5/market/kline",
        start_ms=start_ms,
        end_ms=end_ms,
        chunk_ms=999 * HOUR_MS,
        base_params={"category": "linear", "symbol": SYMBOL, "interval": "60"},
        limit=1000,
    )
    seen: dict[int, BybitKline] = {}
    for row in raw:
        if not isinstance(row, list) or len(row) < 7:
            raise RuntimeError(f"Short Bybit kline row: {row!r}")
        timestamp = int(row[0])
        if not start_ms <= timestamp < end_ms:
            continue
        item = BybitKline(
            timestamp_ms=timestamp,
            open=float(row[1]),
            high=float(row[2]),
            low=float(row[3]),
            close=float(row[4]),
            volume=float(row[5]),
            turnover=float(row[6]),
        )
        previous = seen.get(timestamp)
        if previous is not None and previous != item:
            raise RuntimeError("Conflicting Bybit kline duplicate")
        seen[timestamp] = item
    return [seen[key] for key in sorted(seen)]


def fetch_bybit_open_interest() -> list[BybitOpenInterest]:
    start_ms = parse_utc(AUDIT_START)
    end_ms = parse_utc(AUDIT_END_EXCLUSIVE)
    raw = _fetch_bybit_windowed(
        "/v5/market/open-interest",
        start_ms=start_ms,
        end_ms=end_ms,
        chunk_ms=6 * DAY_MS,
        base_params={
            "category": "linear",
            "symbol": SYMBOL,
            "intervalTime": "1h",
        },
        limit=200,
    )
    seen: dict[int, BybitOpenInterest] = {}
    for row in raw:
        if isinstance(row, dict):
            timestamp = int(row["timestamp"])
            value = float(row["openInterest"])
        elif isinstance(row, list) and len(row) >= 2:
            timestamp = int(row[0])
            value = float(row[1])
        else:
            raise RuntimeError(f"Invalid Bybit open-interest row: {row!r}")
        if not start_ms <= timestamp < end_ms:
            continue
        item = BybitOpenInterest(timestamp_ms=timestamp, open_interest=value)
        previous = seen.get(timestamp)
        if previous is not None and previous != item:
            raise RuntimeError("Conflicting Bybit open-interest duplicate")
        seen[timestamp] = item
    return [seen[key] for key in sorted(seen)]


def fetch_bybit_account_ratio() -> list[BybitAccountRatio]:
    start_ms = parse_utc(AUDIT_START)
    end_ms = parse_utc(AUDIT_END_EXCLUSIVE)
    raw = _fetch_bybit_windowed(
        "/v5/market/account-ratio",
        start_ms=start_ms,
        end_ms=end_ms,
        chunk_ms=18 * DAY_MS,
        base_params={
            "category": "linear",
            "symbol": SYMBOL,
            "period": "1h",
        },
        limit=500,
    )
    seen: dict[int, BybitAccountRatio] = {}
    for row in raw:
        if isinstance(row, dict):
            timestamp = int(row["timestamp"])
            buy_ratio = float(row["buyRatio"])
            sell_ratio = float(row["sellRatio"])
        elif isinstance(row, list) and len(row) >= 3:
            timestamp = int(row[0])
            buy_ratio = float(row[1])
            sell_ratio = float(row[2])
        else:
            raise RuntimeError(f"Invalid Bybit account-ratio row: {row!r}")
        if not start_ms <= timestamp < end_ms:
            continue
        item = BybitAccountRatio(
            timestamp_ms=timestamp,
            buy_ratio=buy_ratio,
            sell_ratio=sell_ratio,
        )
        previous = seen.get(timestamp)
        if previous is not None and previous != item:
            raise RuntimeError("Conflicting Bybit account-ratio duplicate")
        seen[timestamp] = item
    return [seen[key] for key in sorted(seen)]


def fetch_bybit_funding() -> list[BybitFunding]:
    start_ms = parse_utc(AUDIT_START)
    audit_end = parse_utc(AUDIT_END_EXCLUSIVE)
    _guard_window(start_ms, audit_end, context="M8 Bybit funding history")
    collected: dict[int, BybitFunding] = {}
    cursor_end = audit_end - 1
    previous_oldest: int | None = None
    while cursor_end >= start_ms:
        payload = _request_json(
            "/v5/market/funding/history",
            {
                "category": "linear",
                "symbol": SYMBOL,
                "endTime": cursor_end,
                "limit": 200,
            },
        )
        rows, _ = _result_list(payload)
        if not rows:
            break
        timestamps: list[int] = []
        for raw in rows:
            if not isinstance(raw, dict):
                raise RuntimeError(f"Unexpected Bybit funding row: {raw!r}")
            timestamp = int(raw["fundingRateTimestamp"])
            timestamps.append(timestamp)
            if start_ms <= timestamp < audit_end:
                item = BybitFunding(
                    timestamp_ms=timestamp,
                    funding_rate=float(raw["fundingRate"]),
                )
                previous = collected.get(timestamp)
                if previous is not None and previous != item:
                    raise RuntimeError("Conflicting Bybit funding duplicate")
                collected[timestamp] = item
        oldest = min(timestamps)
        if oldest < start_ms:
            break
        if previous_oldest is not None and oldest >= previous_oldest:
            raise RuntimeError("Bybit funding pagination did not advance")
        previous_oldest = oldest
        cursor_end = oldest - 1
    return [collected[key] for key in sorted(collected)]


def _hourly_common(
    timestamps: list[int],
    *,
    min_coverage: float,
    max_missing: int,
) -> tuple[int, float, int, bool, bool, bool]:
    start_ms = parse_utc(AUDIT_START)
    end_ms = parse_utc(AUDIT_END_EXCLUSIVE)
    expected = _expected_slots(start_ms, end_ms, HOUR_MS)
    coverage = len(timestamps) / expected if expected else 0.0
    missing = _max_missing_run(timestamps, start_ms, end_ms, HOUR_MS)
    unique = len(timestamps) == len(set(timestamps))
    aligned = all(timestamp % HOUR_MS == 0 for timestamp in timestamps)
    ordered = all(left < right for left, right in zip(timestamps, timestamps[1:], strict=False))
    _ = min_coverage, max_missing
    return expected, coverage, missing, unique, aligned, ordered


def audit_bybit_kline(rows: list[BybitKline] | tuple[BybitKline, ...]) -> dict[str, object]:
    timestamps = [item.timestamp_ms for item in rows]
    expected, coverage, missing, unique, aligned, ordered = _hourly_common(
        timestamps,
        min_coverage=BYBIT_KLINE_MIN_COVERAGE,
        max_missing=BYBIT_KLINE_MAX_MISSING_HOURS,
    )
    valid = all(
        all(
            math.isfinite(value)
            for value in (item.open, item.high, item.low, item.close, item.volume, item.turnover)
        )
        and item.open > 0
        and item.high > 0
        and item.low > 0
        and item.close > 0
        and item.high >= max(item.open, item.close, item.low)
        and item.low <= min(item.open, item.close, item.high)
        and item.volume >= 0
        and item.turnover >= 0
        for item in rows
    )
    passed = (
        unique
        and aligned
        and ordered
        and valid
        and coverage >= BYBIT_KLINE_MIN_COVERAGE
        and missing <= BYBIT_KLINE_MAX_MISSING_HOURS
    )
    return {
        "status": "PASS" if passed else "FAIL",
        "row_count": len(rows),
        "expected_slots": expected,
        "coverage": coverage,
        "max_missing_hours": missing,
        "timestamps_unique": unique,
        "timestamps_aligned": aligned,
        "timestamps_strictly_increasing": ordered,
        "values_valid": valid,
        "first_timestamp_ms": timestamps[0] if timestamps else None,
        "last_timestamp_ms": timestamps[-1] if timestamps else None,
        "normalized_sha256": _normalized_hash(rows),
    }


def audit_bybit_open_interest(
    rows: list[BybitOpenInterest] | tuple[BybitOpenInterest, ...],
) -> dict[str, object]:
    timestamps = [item.timestamp_ms for item in rows]
    expected, coverage, missing, unique, aligned, ordered = _hourly_common(
        timestamps,
        min_coverage=BYBIT_POSITIONING_MIN_COVERAGE,
        max_missing=BYBIT_POSITIONING_MAX_MISSING_HOURS,
    )
    valid = all(math.isfinite(item.open_interest) and item.open_interest > 0 for item in rows)
    passed = (
        unique
        and aligned
        and ordered
        and valid
        and coverage >= BYBIT_POSITIONING_MIN_COVERAGE
        and missing <= BYBIT_POSITIONING_MAX_MISSING_HOURS
    )
    return {
        "status": "PASS" if passed else "FAIL",
        "row_count": len(rows),
        "expected_slots": expected,
        "coverage": coverage,
        "max_missing_hours": missing,
        "values_valid": valid,
        "first_timestamp_ms": timestamps[0] if timestamps else None,
        "last_timestamp_ms": timestamps[-1] if timestamps else None,
        "normalized_sha256": _normalized_hash(rows),
    }


def audit_bybit_account_ratio(
    rows: list[BybitAccountRatio] | tuple[BybitAccountRatio, ...],
) -> dict[str, object]:
    timestamps = [item.timestamp_ms for item in rows]
    expected, coverage, missing, unique, aligned, ordered = _hourly_common(
        timestamps,
        min_coverage=BYBIT_POSITIONING_MIN_COVERAGE,
        max_missing=BYBIT_POSITIONING_MAX_MISSING_HOURS,
    )
    valid = all(
        math.isfinite(item.buy_ratio)
        and math.isfinite(item.sell_ratio)
        and 0 <= item.buy_ratio <= 1
        and 0 <= item.sell_ratio <= 1
        and abs(item.buy_ratio + item.sell_ratio - 1.0) <= 0.02
        for item in rows
    )
    passed = (
        unique
        and aligned
        and ordered
        and valid
        and coverage >= BYBIT_POSITIONING_MIN_COVERAGE
        and missing <= BYBIT_POSITIONING_MAX_MISSING_HOURS
    )
    return {
        "status": "PASS" if passed else "FAIL",
        "row_count": len(rows),
        "expected_slots": expected,
        "coverage": coverage,
        "max_missing_hours": missing,
        "values_valid": valid,
        "first_timestamp_ms": timestamps[0] if timestamps else None,
        "last_timestamp_ms": timestamps[-1] if timestamps else None,
        "normalized_sha256": _normalized_hash(rows),
    }


def audit_bybit_funding(
    rows: list[BybitFunding] | tuple[BybitFunding, ...],
) -> dict[str, object]:
    start_ms = parse_utc(AUDIT_START)
    end_ms = parse_utc(AUDIT_END_EXCLUSIVE)
    timestamps = [item.timestamp_ms for item in rows]
    unique = len(timestamps) == len(set(timestamps))
    ordered = all(left < right for left, right in zip(timestamps, timestamps[1:], strict=False))
    values_valid = all(
        math.isfinite(item.funding_rate) and abs(item.funding_rate) <= 0.05 for item in rows
    )
    positive_gaps = [
        right - left
        for left, right in zip(timestamps, timestamps[1:], strict=False)
        if right > left
    ]
    max_gap_hours = max(positive_gaps, default=0) / HOUR_MS
    first_edge_hours = (timestamps[0] - start_ms) / HOUR_MS if timestamps else math.inf
    last_edge_hours = (end_ms - timestamps[-1]) / HOUR_MS if timestamps else math.inf
    passed = (
        unique
        and ordered
        and values_valid
        and len(rows) >= 4000
        and 0 <= first_edge_hours <= 24
        and 0 <= last_edge_hours <= 24
        and max_gap_hours <= 24
    )
    return {
        "status": "PASS" if passed else "FAIL",
        "row_count": len(rows),
        "timestamps_unique": unique,
        "timestamps_strictly_increasing": ordered,
        "values_valid": values_valid,
        "first_edge_hours": first_edge_hours if math.isfinite(first_edge_hours) else None,
        "last_edge_hours": last_edge_hours if math.isfinite(last_edge_hours) else None,
        "max_positive_cadence_hours": max_gap_hours,
        "first_timestamp_ms": timestamps[0] if timestamps else None,
        "last_timestamp_ms": timestamps[-1] if timestamps else None,
        "normalized_sha256": _normalized_hash(rows),
    }


def audit_cross_exchange_alignment(
    metrics: list[BinanceMetric] | tuple[BinanceMetric, ...],
    klines: list[BybitKline] | tuple[BybitKline, ...],
    open_interest: list[BybitOpenInterest] | tuple[BybitOpenInterest, ...],
    account_ratio: list[BybitAccountRatio] | tuple[BybitAccountRatio, ...],
) -> dict[str, object]:
    start_ms = parse_utc(AUDIT_START)
    end_ms = parse_utc(AUDIT_END_EXCLUSIVE)
    metric_times = [item.timestamp_ms for item in metrics]
    kline_times = {item.timestamp_ms for item in klines}
    oi_times = {item.timestamp_ms for item in open_interest}
    ratio_times = {item.timestamp_ms for item in account_ratio}
    expected = _expected_slots(start_ms, end_ms, HOUR_MS)
    aligned_count = 0
    future_violations = 0
    stale_metric_hours = 0
    positioning_missing_hours = 0
    for index in range(expected):
        hour = start_ms + index * HOUR_MS
        if hour not in kline_times:
            continue
        if hour not in oi_times and hour not in ratio_times:
            positioning_missing_hours += 1
            continue
        metric_index = bisect_right(metric_times, hour) - 1
        if metric_index < 0:
            stale_metric_hours += 1
            continue
        metric_time = metric_times[metric_index]
        if metric_time > hour:
            future_violations += 1
            continue
        if hour - metric_time > 10 * 60 * 1000:
            stale_metric_hours += 1
            continue
        aligned_count += 1
    coverage = aligned_count / expected if expected else 0.0
    passed = coverage >= CROSS_EXCHANGE_MIN_HOURLY_ALIGNMENT and future_violations == 0
    return {
        "status": "PASS" if passed else "FAIL",
        "expected_hourly_slots": expected,
        "aligned_hourly_slots": aligned_count,
        "coverage": coverage,
        "future_metric_violations": future_violations,
        "stale_or_missing_metric_hours": stale_metric_hours,
        "positioning_missing_hours_with_kline": positioning_missing_hours,
        "max_metric_staleness_minutes": 10,
    }


def _daily_archive_worker(
    family: str,
    date_text: str,
    parser: Callable[[list[list[str]], str], dict[str, object]],
) -> tuple[str, bool, bool, dict[str, object]]:
    url = _binance_daily_url(family, date_text)
    downloaded = _download_verified_archive(url)
    if downloaded is None:
        return date_text, False, False, {}
    payload, _ = downloaded
    try:
        parsed = parser(_csv_rows_from_zip(payload), date_text)
    except (RuntimeError, ValueError, IndexError, KeyError):
        return date_text, True, True, {}
    return date_text, True, False, parsed


def _parse_book_depth_day(rows: list[list[str]], date_text: str) -> dict[str, object]:
    if not rows:
        raise RuntimeError("Empty bookDepth archive")
    header = [value.strip().lower() for value in rows[0]]
    has_header = "timestamp" in header and "percentage" in header
    data = rows[1:] if has_header else rows
    if has_header:
        indices = {
            name: header.index(name) for name in ("timestamp", "percentage", "depth", "notional")
        }
    else:
        indices = {"timestamp": 0, "percentage": 1, "depth": 2, "notional": 3}

    timestamps: list[int] = []
    invalid = 0
    exact_duplicates = 0
    seen_rows: set[tuple[str, ...]] = set()
    expected_percentages = {-5, -4, -3, -2, -1, 1, 2, 3, 4, 5}
    day_start = parse_utc(f"{date_text}T00:00:00Z")
    day_end = day_start + DAY_MS
    for row in data:
        normalized = tuple(value.strip() for value in row)
        if normalized in seen_rows:
            exact_duplicates += 1
            continue
        seen_rows.add(normalized)
        try:
            timestamp = _parse_timestamp(row[indices["timestamp"]])
            percentage = int(float(row[indices["percentage"]]))
            depth = float(row[indices["depth"]])
            notional = float(row[indices["notional"]])
            if (
                not day_start <= timestamp < day_end
                or percentage not in expected_percentages
                or not math.isfinite(depth)
                or not math.isfinite(notional)
                or depth < 0
                or notional < 0
            ):
                raise ValueError
        except (ValueError, IndexError):
            invalid += 1
            continue
        timestamps.append(timestamp)

    unique_snapshots = sorted(set(timestamps))
    within_limit = 0
    cadence = 0
    for left, right in zip(unique_snapshots, unique_snapshots[1:], strict=False):
        gap = right - left
        if gap <= 0:
            continue
        cadence += 1
        if gap <= 120_000:
            within_limit += 1
    return {
        "date": date_text,
        "row_count": len(data),
        "invalid_rows": invalid,
        "first_timestamp_ms": min(timestamps) if timestamps else None,
        "last_timestamp_ms": max(timestamps) if timestamps else None,
        "cadence_observations": cadence,
        "cadence_within_limit": within_limit,
        "exact_duplicate_rows": exact_duplicates,
        "conflicting_duplicates": 0,
    }


def _parse_liquidation_day(rows: list[list[str]], date_text: str) -> dict[str, object]:
    if not rows:
        raise RuntimeError("Empty liquidationSnapshot archive")
    header = [value.strip().lower() for value in rows[0]]
    has_header = header[0] in {"time", "timestamp", "create_time"}
    data = rows[1:] if has_header else rows
    time_index = 0

    timestamps: list[int] = []
    invalid = 0
    exact_duplicates = 0
    seen_rows: set[tuple[str, ...]] = set()
    day_start = parse_utc(f"{date_text}T00:00:00Z")
    day_end = day_start + DAY_MS
    for row in data:
        normalized = tuple(value.strip() for value in row)
        if normalized in seen_rows:
            exact_duplicates += 1
            continue
        seen_rows.add(normalized)
        try:
            timestamp = _parse_timestamp(row[time_index])
            numeric_values = []
            for value in row:
                stripped = value.strip()
                if not stripped:
                    continue
                try:
                    numeric_values.append(float(stripped))
                except ValueError:
                    continue
            if (
                not day_start <= timestamp < day_end
                or not numeric_values
                or any(not math.isfinite(value) for value in numeric_values)
            ):
                raise ValueError
        except (ValueError, IndexError):
            invalid += 1
            continue
        timestamps.append(timestamp)

    conflicts = 0
    return {
        "date": date_text,
        "row_count": len(data),
        "invalid_rows": invalid,
        "first_timestamp_ms": min(timestamps) if timestamps else None,
        "last_timestamp_ms": max(timestamps) if timestamps else None,
        "cadence_observations": 0,
        "cadence_within_limit": 0,
        "exact_duplicate_rows": exact_duplicates,
        "conflicting_duplicates": conflicts,
    }


def _audit_daily_archive(
    family: str,
    *,
    start_text: str,
    end_text: str,
    parser: Callable[[list[list[str]], str], dict[str, object]],
    workers: int,
) -> DailyArchiveAudit:
    start_ms = parse_utc(start_text)
    end_ms = parse_utc(end_text)
    _guard_window(start_ms, end_ms, context=f"M8 Binance {family} archive audit")
    if workers < 1 or workers > 16:
        raise ValueError("workers must be between 1 and 16")
    dates = _date_range(start_text, end_text)
    results: list[tuple[str, bool, bool, dict[str, object]]] = []
    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = {
            executor.submit(_daily_archive_worker, family, date, parser): date for date in dates
        }
        for future in as_completed(futures):
            results.append(future.result())

    existing = 0
    parse_errors = 0
    row_count = 0
    invalid_rows = 0
    exact_duplicates = 0
    conflicts = 0
    first: int | None = None
    last: int | None = None
    cadence = 0
    cadence_within = 0
    for _, exists, parse_error, parsed in sorted(results):
        if not exists:
            continue
        existing += 1
        if parse_error:
            parse_errors += 1
            continue
        row_count += int(parsed.get("row_count", 0))
        invalid_rows += int(parsed.get("invalid_rows", 0))
        exact_duplicates += int(parsed.get("exact_duplicate_rows", 0))
        conflicts += int(parsed.get("conflicting_duplicates", 0))
        cadence += int(parsed.get("cadence_observations", 0))
        cadence_within += int(parsed.get("cadence_within_limit", 0))
        value = parsed.get("first_timestamp_ms")
        if isinstance(value, int):
            first = value if first is None else min(first, value)
        value = parsed.get("last_timestamp_ms")
        if isinstance(value, int):
            last = value if last is None else max(last, value)

    return DailyArchiveAudit(
        family=family,
        start_date=start_text,
        end_date_exclusive=end_text,
        expected_files=len(dates),
        existing_files=existing,
        checksum_verified_files=existing,
        missing_files=len(dates) - existing,
        parse_error_files=parse_errors,
        row_count=row_count,
        invalid_rows=invalid_rows,
        exact_duplicate_rows=exact_duplicates,
        conflicting_duplicates=conflicts,
        first_timestamp_ms=first,
        last_timestamp_ms=last,
        cadence_observations=cadence,
        cadence_within_limit=cadence_within,
    )


def audit_binance_book_depth(*, workers: int = 8) -> dict[str, object]:
    audited = _audit_daily_archive(
        "bookDepth",
        start_text=BOOK_DEPTH_START,
        end_text=AUDIT_END_EXCLUSIVE,
        parser=_parse_book_depth_day,
        workers=workers,
    )
    file_coverage = (
        audited.existing_files / audited.expected_files if audited.expected_files else 0.0
    )
    cadence_ratio = (
        audited.cadence_within_limit / audited.cadence_observations
        if audited.cadence_observations
        else 0.0
    )
    passed = (
        file_coverage >= BOOK_DEPTH_MIN_DAILY_FILE_COVERAGE
        and audited.parse_error_files == 0
        and audited.invalid_rows == 0
        and cadence_ratio >= 0.95
    )
    return {
        **asdict(audited),
        "status": "PARTIAL_WINDOW_ELIGIBLE" if passed else "PARTIAL_WINDOW_FAIL",
        "daily_file_coverage": file_coverage,
        "cadence_within_120_seconds_ratio": cadence_ratio,
        "full_window_primary": False,
    }


def audit_binance_liquidation(*, workers: int = 8) -> dict[str, object]:
    audited = _audit_daily_archive(
        "liquidationSnapshot",
        start_text=AUDIT_START,
        end_text=AUDIT_END_EXCLUSIVE,
        parser=_parse_liquidation_day,
        workers=workers,
    )
    file_coverage = (
        audited.existing_files / audited.expected_files if audited.expected_files else 0.0
    )
    end_ms = parse_utc(AUDIT_END_EXCLUSIVE)
    edge_ok = (
        audited.last_timestamp_ms is not None and 0 <= end_ms - audited.last_timestamp_ms <= DAY_MS
    )
    passed = (
        file_coverage >= LIQUIDATION_MIN_DAILY_FILE_COVERAGE
        and edge_ok
        and audited.parse_error_files == 0
        and audited.invalid_rows == 0
        and audited.conflicting_duplicates == 0
    )
    return {
        **asdict(audited),
        "status": "FULL_WINDOW_PASS" if passed else "EXCLUDED_INCOMPLETE_HISTORY",
        "daily_file_coverage": file_coverage,
        "last_edge_within_24h": edge_ok,
    }


def _safe_source(
    loader: Callable[[], list[Any]],
    auditor: Callable[[list[Any]], dict[str, object]],
) -> tuple[list[Any], dict[str, object]]:
    try:
        rows = loader()
        report = auditor(rows)
        return rows, report
    except (RuntimeError, ValueError, KeyError, TypeError) as error:
        return [], {
            "status": "ERROR",
            "error_type": type(error).__name__,
            "error": str(error),
        }


def _write_report_once(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with path.open("x", encoding="utf-8") as handle:
            handle.write(json.dumps(payload, indent=2, sort_keys=True, allow_nan=False))
    except FileExistsError as error:
        raise RuntimeError(
            "M8 audit report already exists; preserve the first frozen audit"
        ) from error


def run_m8_data_audit(
    *,
    report_path: str | Path = "artifacts/m8_alt_derivatives_data_audit.json",
    workers: int = 8,
) -> dict[str, object]:
    output = Path(report_path)
    if output.exists():
        raise RuntimeError("M8 audit report already exists; preserve the first frozen audit")

    freeze = verify_m8_audit_freeze()
    provenance = collect_source_provenance(require_clean=True)
    start_ms = parse_utc(AUDIT_START)
    end_ms = parse_utc(AUDIT_END_EXCLUSIVE)
    _guard_window(start_ms, end_ms, context="M8 frozen alternative derivatives audit")

    metrics, metrics_meta = fetch_binance_metrics(workers=workers)
    metrics_report = audit_binance_metrics(metrics, metrics_meta)

    bybit_kline, bybit_kline_report = _safe_source(fetch_bybit_klines, audit_bybit_kline)
    bybit_oi, bybit_oi_report = _safe_source(
        fetch_bybit_open_interest,
        audit_bybit_open_interest,
    )
    bybit_ratio, bybit_ratio_report = _safe_source(
        fetch_bybit_account_ratio,
        audit_bybit_account_ratio,
    )
    _, bybit_funding_report = _safe_source(fetch_bybit_funding, audit_bybit_funding)

    alignment_report = audit_cross_exchange_alignment(
        metrics,
        bybit_kline,
        bybit_oi,
        bybit_ratio,
    )
    book_depth_report = audit_binance_book_depth(workers=workers)
    liquidation_report = audit_binance_liquidation(workers=workers)

    positioning_pass = (
        bybit_oi_report.get("status") == "PASS" or bybit_ratio_report.get("status") == "PASS"
    )
    eligible = (
        metrics_report.get("status") == "FULL_WINDOW_PASS"
        and bybit_kline_report.get("status") == "PASS"
        and positioning_pass
        and alignment_report.get("status") == "PASS"
    )
    decision = (
        "ELIGIBLE_FOR_M8_POSITIONING_EDGE_DESIGN"
        if eligible
        else "M8_ALT_DERIVATIVES_DATA_AUDIT_FAIL"
    )
    report: dict[str, object] = {
        "phase": "m8_alt_derivatives_historical_data_audit",
        "decision": decision,
        "policy_freeze": freeze,
        "source_provenance": provenance,
        "data_boundary": {
            "audit": f"{AUDIT_START}/{AUDIT_END_EXCLUSIVE}",
            "book_depth_partial": f"{BOOK_DEPTH_START}/{AUDIT_END_EXCLUSIVE}",
            "oos_2025": "LOCKED_NOT_ACCESSED",
        },
        "primary": {
            "binance_metrics_5m": metrics_report,
            "bybit_kline_1h": bybit_kline_report,
            "bybit_open_interest_1h": bybit_oi_report,
            "bybit_account_ratio_1h": bybit_ratio_report,
            "bybit_funding": bybit_funding_report,
            "cross_exchange_hourly_alignment": alignment_report,
        },
        "secondary": {
            "binance_book_depth_partial": book_depth_report,
            "binance_liquidation_snapshot": liquidation_report,
        },
        "forward_returns": "NOT_COMPUTED",
        "strategy_generation": "FORBIDDEN_REQUIRES_SEPARATE_FROZEN_EDGE_PROTOCOL",
        "ai_module": "excluded",
        "live_execution": "forbidden",
        "oos_2025": "LOCKED_NOT_ACCESSED",
    }
    _write_report_once(output, report)
    return report


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run frozen M8 alternative derivatives historical data audit (2021-2024 only)"
    )
    parser.add_argument(
        "--report",
        default="artifacts/m8_alt_derivatives_data_audit.json",
    )
    parser.add_argument("--workers", type=int, default=8)
    args = parser.parse_args()
    report = run_m8_data_audit(report_path=args.report, workers=args.workers)
    primary = report["primary"]
    secondary = report["secondary"]
    assert isinstance(primary, dict)
    assert isinstance(secondary, dict)
    print(f"M8 decision: {report['decision']}")
    print(f"Binance metrics: {primary['binance_metrics_5m']['status']}")
    print(f"Bybit kline: {primary['bybit_kline_1h']['status']}")
    print(f"Bybit open interest: {primary['bybit_open_interest_1h']['status']}")
    print(f"Bybit account ratio: {primary['bybit_account_ratio_1h']['status']}")
    print(f"Bybit funding: {primary['bybit_funding']['status']}")
    print(f"Cross-exchange alignment: {primary['cross_exchange_hourly_alignment']['status']}")
    print(f"BookDepth: {secondary['binance_book_depth_partial']['status']}")
    print(f"Liquidation: {secondary['binance_liquidation_snapshot']['status']}")
    print("Forward returns: NOT_COMPUTED")
    print("2025 OOS remains LOCKED_NOT_ACCESSED")


if __name__ == "__main__":
    main()
