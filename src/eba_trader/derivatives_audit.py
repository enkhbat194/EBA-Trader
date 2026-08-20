from __future__ import annotations

import argparse
import csv
import json
import math
import statistics
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from .derivatives_audit_policy import (
    AUDIT_END_EXCLUSIVE,
    AUDIT_START,
    EXPECTED_15M_SLOTS,
    FAPI_BASE_URL,
    FUNDING_ENDPOINT,
    FUTURES_KLINE_ENDPOINT,
    INDEX_KLINE_ENDPOINT,
    INTERVAL,
    INTERVAL_MS,
    MAX_FUNDING_ABS_RATE,
    MAX_FUNDING_EDGE_HOURS,
    MAX_FUNDING_GAP_HOURS,
    MAX_FUNDING_MEDIAN_CADENCE_HOURS,
    MAX_KLINE_MISSING_RUN,
    MIN_CROSS_SOURCE_COVERAGE,
    MIN_FUNDING_RECORDS,
    MIN_KLINE_COVERAGE,
    PREMIUM_ENDPOINT,
    RETENTION_BLOCKED,
    SYMBOL,
    sha256_file,
    verify_m6_audit_freeze,
)
from .history import parse_utc
from .holdout_guard import assert_not_first_cycle_oos_overlap
from .provenance import collect_source_provenance

HOUR_MS = 60 * 60 * 1000


@dataclass(frozen=True, slots=True)
class FundingRecord:
    symbol: str
    funding_time_ms: int
    funding_rate: float
    mark_price: float | None = None
    rate_type: str | None = None


@dataclass(frozen=True, slots=True)
class DerivativeKline:
    open_time_ms: int
    open: float
    high: float
    low: float
    close: float
    close_time_ms: int
    volume: float | None = None
    quote_volume: float | None = None
    trade_count: int | None = None
    taker_buy_base_volume: float | None = None
    taker_buy_quote_volume: float | None = None


def _assert_development_range(start_ms: int, end_ms: int, *, context: str) -> None:
    audit_start = parse_utc(AUDIT_START)
    audit_end = parse_utc(AUDIT_END_EXCLUSIVE)
    if start_ms < audit_start or end_ms > audit_end or start_ms >= end_ms:
        raise RuntimeError(f"{context} is outside the frozen M6 development audit window")
    assert_not_first_cycle_oos_overlap(
        symbol=SYMBOL,
        interval=INTERVAL,
        start_ms=start_ms,
        end_ms=end_ms,
        context=context,
    )


def _request_json(
    path: str,
    params: dict[str, object],
    *,
    timeout: float = 20.0,
    max_retries: int = 4,
    backoff_seconds: float = 0.5,
) -> object:
    query = urlencode(params)
    request = Request(
        f"{FAPI_BASE_URL}{path}?{query}",
        headers={"User-Agent": "EBA-Trader-M6-Data-Audit/1.0"},
    )
    for attempt in range(max_retries + 1):
        try:
            with urlopen(request, timeout=timeout) as response:  # noqa: S310
                return json.loads(response.read().decode("utf-8"))
        except HTTPError as error:
            retryable = error.code in {418, 429} or 500 <= error.code < 600
            if not retryable or attempt >= max_retries:
                raise RuntimeError(f"Binance derivatives HTTP error {error.code}") from error
            retry_after = error.headers.get("Retry-After") if error.headers else None
            try:
                delay = (
                    float(retry_after)
                    if retry_after is not None
                    else backoff_seconds * (2**attempt)
                )
            except ValueError:
                delay = backoff_seconds * (2**attempt)
            time.sleep(min(max(delay, 0.0), 30.0))
        except (URLError, TimeoutError) as error:
            if attempt >= max_retries:
                raise RuntimeError("Binance derivatives request failed after retries") from error
            time.sleep(min(backoff_seconds * (2**attempt), 30.0))
    raise RuntimeError("Unreachable request retry state")


def _funding_from_object(item: object) -> FundingRecord:
    if not isinstance(item, dict):
        raise ValueError("Funding row must be an object")
    mark_raw = item.get("markPrice")
    rate_type_raw = item.get("rateType")
    return FundingRecord(
        symbol=str(item["symbol"]),
        funding_time_ms=int(item["fundingTime"]),
        funding_rate=float(item["fundingRate"]),
        mark_price=float(mark_raw) if mark_raw not in (None, "") else None,
        rate_type=str(rate_type_raw) if rate_type_raw not in (None, "") else None,
    )


def fetch_funding_history(start_ms: int, end_ms: int) -> list[FundingRecord]:
    _assert_development_range(start_ms, end_ms, context="M6 funding history download")
    cursor = start_ms
    rows: list[FundingRecord] = []
    while cursor < end_ms:
        payload = _request_json(
            FUNDING_ENDPOINT,
            {
                "symbol": SYMBOL,
                "startTime": cursor,
                "endTime": end_ms - 1,
                "limit": 1000,
            },
        )
        if not isinstance(payload, list):
            raise RuntimeError("Unexpected funding history response shape")
        page = [_funding_from_object(item) for item in payload]
        page = [item for item in page if start_ms <= item.funding_time_ms < end_ms]
        if not page:
            break
        rows.extend(page)
        next_cursor = page[-1].funding_time_ms + 1
        if next_cursor <= cursor:
            raise RuntimeError("Funding history pagination did not advance")
        cursor = next_cursor
        if len(payload) < 1000:
            break
    return rows


def _kline_from_row(row: object, *, futures_activity: bool) -> DerivativeKline:
    if not isinstance(row, list) or len(row) < 7:
        raise ValueError("Derivatives kline row is too short")
    return DerivativeKline(
        open_time_ms=int(row[0]),
        open=float(row[1]),
        high=float(row[2]),
        low=float(row[3]),
        close=float(row[4]),
        volume=float(row[5]) if futures_activity else None,
        close_time_ms=int(row[6]),
        quote_volume=float(row[7]) if futures_activity and len(row) > 7 else None,
        trade_count=int(row[8]) if futures_activity and len(row) > 8 else None,
        taker_buy_base_volume=(
            float(row[9]) if futures_activity and len(row) > 9 else None
        ),
        taker_buy_quote_volume=(
            float(row[10]) if futures_activity and len(row) > 10 else None
        ),
    )


def fetch_kline_history(
    endpoint: str,
    *,
    parameter_name: str,
    start_ms: int,
    end_ms: int,
    futures_activity: bool,
) -> list[DerivativeKline]:
    _assert_development_range(start_ms, end_ms, context=f"M6 {endpoint} download")
    cursor = start_ms
    rows: list[DerivativeKline] = []
    while cursor < end_ms:
        payload = _request_json(
            endpoint,
            {
                parameter_name: SYMBOL,
                "interval": INTERVAL,
                "startTime": cursor,
                "endTime": end_ms - 1,
                "limit": 1500,
            },
        )
        if not isinstance(payload, list):
            raise RuntimeError(f"Unexpected kline response shape for {endpoint}")
        page = [_kline_from_row(item, futures_activity=futures_activity) for item in payload]
        page = [item for item in page if start_ms <= item.open_time_ms < end_ms]
        if not page:
            break
        rows.extend(page)
        next_cursor = page[-1].open_time_ms + INTERVAL_MS
        if next_cursor <= cursor:
            raise RuntimeError(f"Kline pagination did not advance for {endpoint}")
        cursor = next_cursor
        if len(payload) < 1500:
            break
    return rows


def _save_funding_csv(rows: list[FundingRecord], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["symbol", "funding_time_ms", "funding_rate", "mark_price", "rate_type"],
        )
        writer.writeheader()
        for row in rows:
            writer.writerow(asdict(row))


def _load_funding_csv(path: Path) -> list[FundingRecord]:
    with path.open(newline="", encoding="utf-8") as handle:
        return [
            FundingRecord(
                symbol=row["symbol"],
                funding_time_ms=int(row["funding_time_ms"]),
                funding_rate=float(row["funding_rate"]),
                mark_price=(
                    float(row["mark_price"])
                    if row["mark_price"] not in ("", "None")
                    else None
                ),
                rate_type=row["rate_type"] if row["rate_type"] not in ("", "None") else None,
            )
            for row in csv.DictReader(handle)
        ]


def _save_kline_csv(rows: list[DerivativeKline], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = list(DerivativeKline.__dataclass_fields__)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(asdict(row))


def _optional_float(value: str) -> float | None:
    return None if value in ("", "None") else float(value)


def _optional_int(value: str) -> int | None:
    return None if value in ("", "None") else int(value)


def _load_kline_csv(path: Path) -> list[DerivativeKline]:
    with path.open(newline="", encoding="utf-8") as handle:
        return [
            DerivativeKline(
                open_time_ms=int(row["open_time_ms"]),
                open=float(row["open"]),
                high=float(row["high"]),
                low=float(row["low"]),
                close=float(row["close"]),
                close_time_ms=int(row["close_time_ms"]),
                volume=_optional_float(row["volume"]),
                quote_volume=_optional_float(row["quote_volume"]),
                trade_count=_optional_int(row["trade_count"]),
                taker_buy_base_volume=_optional_float(row["taker_buy_base_volume"]),
                taker_buy_quote_volume=_optional_float(row["taker_buy_quote_volume"]),
            )
            for row in csv.DictReader(handle)
        ]


def _max_missing_run(timestamps: list[int], start_ms: int, end_ms: int) -> int:
    if not timestamps:
        return (end_ms - start_ms) // INTERVAL_MS
    maximum = max((timestamps[0] - start_ms) // INTERVAL_MS, 0)
    for previous, current in zip(timestamps, timestamps[1:], strict=False):
        missing = max((current - previous) // INTERVAL_MS - 1, 0)
        maximum = max(maximum, missing)
    tail = max((end_ms - INTERVAL_MS - timestamps[-1]) // INTERVAL_MS, 0)
    return max(maximum, tail)


def audit_funding(
    rows: list[FundingRecord],
    *,
    start_ms: int,
    end_ms: int,
) -> dict[str, object]:
    times = [row.funding_time_ms for row in rows]
    unique_sorted = times == sorted(times) and len(times) == len(set(times))
    inside = all(start_ms <= item < end_ms for item in times)
    valid_symbol = all(row.symbol == SYMBOL for row in rows)
    finite_rates = all(math.isfinite(row.funding_rate) for row in rows)
    bounded_rates = all(abs(row.funding_rate) <= MAX_FUNDING_ABS_RATE for row in rows)
    cadences = [b - a for a, b in zip(times, times[1:], strict=False) if b > a]
    median_hours = statistics.median(cadences) / HOUR_MS if cadences else math.inf
    max_hours = max(cadences) / HOUR_MS if cadences else math.inf
    first_edge_hours = (times[0] - start_ms) / HOUR_MS if times else math.inf
    last_edge_hours = (end_ms - times[-1]) / HOUR_MS if times else math.inf

    checks = {
        "strict_unique_order": unique_sorted,
        "inside_window": inside,
        "symbol": valid_symbol,
        "minimum_records": len(rows) >= MIN_FUNDING_RECORDS,
        "first_edge": first_edge_hours <= MAX_FUNDING_EDGE_HOURS,
        "last_edge": last_edge_hours <= MAX_FUNDING_EDGE_HOURS,
        "finite_rates": finite_rates,
        "bounded_rates": bounded_rates,
        "median_cadence": median_hours <= MAX_FUNDING_MEDIAN_CADENCE_HOURS,
        "maximum_cadence": max_hours <= MAX_FUNDING_GAP_HOURS,
    }
    return {
        "status": "PASS" if all(checks.values()) else "FAIL",
        "record_count": len(rows),
        "first_funding_time_ms": times[0] if times else None,
        "last_funding_time_ms": times[-1] if times else None,
        "median_cadence_hours": median_hours if math.isfinite(median_hours) else None,
        "max_cadence_hours": max_hours if math.isfinite(max_hours) else None,
        "checks": checks,
    }


def audit_klines(
    rows: list[DerivativeKline],
    *,
    start_ms: int,
    end_ms: int,
    allow_nonpositive_prices: bool,
    futures_activity: bool,
) -> dict[str, object]:
    times = [row.open_time_ms for row in rows]
    unique_sorted = times == sorted(times) and len(times) == len(set(times))
    inside = all(start_ms <= item < end_ms for item in times)
    aligned = all(item % INTERVAL_MS == 0 for item in times)
    close_times = all(row.close_time_ms == row.open_time_ms + INTERVAL_MS - 1 for row in rows)
    finite_ohlc = all(
        all(math.isfinite(value) for value in (row.open, row.high, row.low, row.close))
        for row in rows
    )
    valid_price_sign = (
        True
        if allow_nonpositive_prices
        else all(min(row.open, row.high, row.low, row.close) > 0 for row in rows)
    )
    valid_ohlc = all(
        row.high >= max(row.open, row.close)
        and row.low <= min(row.open, row.close)
        and row.high >= row.low
        for row in rows
    )
    coverage = len(set(times)) / EXPECTED_15M_SLOTS
    max_missing = _max_missing_run(sorted(set(times)), start_ms, end_ms)

    activity_ok = True
    if futures_activity:
        for row in rows:
            values = (
                row.volume,
                row.quote_volume,
                row.taker_buy_base_volume,
                row.taker_buy_quote_volume,
            )
            if (
                row.trade_count is None
                or row.trade_count < 0
                or any(
                    value is None or not math.isfinite(value) or value < 0
                    for value in values
                )
            ):
                activity_ok = False
                break

    checks = {
        "strict_unique_order": unique_sorted,
        "inside_window": inside,
        "aligned_15m": aligned,
        "close_time": close_times,
        "finite_ohlc": finite_ohlc,
        "price_sign": valid_price_sign,
        "ohlc_relationship": valid_ohlc,
        "coverage": coverage >= MIN_KLINE_COVERAGE,
        "maximum_missing_run": max_missing <= MAX_KLINE_MISSING_RUN,
        "futures_activity_fields": activity_ok,
    }
    return {
        "status": "PASS" if all(checks.values()) else "FAIL",
        "record_count": len(rows),
        "coverage": coverage,
        "max_missing_run_slots": max_missing,
        "first_open_time_ms": times[0] if times else None,
        "last_open_time_ms": times[-1] if times else None,
        "checks": checks,
    }


def audit_cross_source(
    premium: list[DerivativeKline],
    futures: list[DerivativeKline],
    index: list[DerivativeKline],
) -> dict[str, object]:
    premium_times = {row.open_time_ms for row in premium}
    futures_map = {row.open_time_ms: row for row in futures}
    index_map = {row.open_time_ms: row for row in index}
    intersection = sorted(premium_times & futures_map.keys() & index_map.keys())
    coverage = len(intersection) / EXPECTED_15M_SLOTS
    basis_values: list[float] = []
    basis_finite = True
    for timestamp in intersection:
        index_close = index_map[timestamp].close
        futures_close = futures_map[timestamp].close
        if index_close <= 0:
            basis_finite = False
            break
        value = futures_close / index_close - 1.0
        if not math.isfinite(value):
            basis_finite = False
            break
        basis_values.append(value)
    checks = {
        "intersection_coverage": coverage >= MIN_CROSS_SOURCE_COVERAGE,
        "synthetic_basis_finite": basis_finite,
    }
    return {
        "status": "PASS" if all(checks.values()) else "FAIL",
        "intersection_count": len(intersection),
        "intersection_coverage": coverage,
        "synthetic_basis_mean": statistics.mean(basis_values) if basis_values else None,
        "synthetic_basis_min": min(basis_values) if basis_values else None,
        "synthetic_basis_max": max(basis_values) if basis_values else None,
        "checks": checks,
    }


def _load_or_fetch(
    cache_dir: Path,
    *,
    allow_download: bool,
) -> tuple[
    list[FundingRecord],
    list[DerivativeKline],
    list[DerivativeKline],
    list[DerivativeKline],
    dict[str, str],
]:
    start_ms = parse_utc(AUDIT_START)
    end_ms = parse_utc(AUDIT_END_EXCLUSIVE)
    _assert_development_range(start_ms, end_ms, context="M6 full data audit")

    paths = {
        "funding": cache_dir / "btcusdt_usdm_funding_2021_2024.csv",
        "premium": cache_dir / "btcusdt_usdm_premium_index_15m_2021_2024.csv",
        "futures": cache_dir / "btcusdt_usdm_perpetual_15m_2021_2024.csv",
        "index": cache_dir / "btcusdt_usdm_index_price_15m_2021_2024.csv",
    }

    if paths["funding"].exists():
        funding = _load_funding_csv(paths["funding"])
    elif allow_download:
        funding = fetch_funding_history(start_ms, end_ms)
        _save_funding_csv(funding, paths["funding"])
    else:
        raise FileNotFoundError(paths["funding"])

    kline_specs = {
        "premium": (PREMIUM_ENDPOINT, "symbol", False),
        "futures": (FUTURES_KLINE_ENDPOINT, "symbol", True),
        "index": (INDEX_KLINE_ENDPOINT, "pair", False),
    }
    loaded: dict[str, list[DerivativeKline]] = {}
    for name, (endpoint, parameter_name, futures_activity) in kline_specs.items():
        path = paths[name]
        if path.exists():
            loaded[name] = _load_kline_csv(path)
        elif allow_download:
            loaded[name] = fetch_kline_history(
                endpoint,
                parameter_name=parameter_name,
                start_ms=start_ms,
                end_ms=end_ms,
                futures_activity=futures_activity,
            )
            _save_kline_csv(loaded[name], path)
        else:
            raise FileNotFoundError(path)

    hashes = {name: sha256_file(path) for name, path in paths.items()}
    return funding, loaded["premium"], loaded["futures"], loaded["index"], hashes


def run_derivatives_data_audit(
    *,
    cache_dir: str | Path = "data/cache/m6",
    report_path: str | Path = "artifacts/m6_derivatives_data_audit.json",
    allow_download: bool = True,
) -> dict[str, object]:
    freeze = verify_m6_audit_freeze()
    provenance = collect_source_provenance(require_clean=True)
    start_ms = parse_utc(AUDIT_START)
    end_ms = parse_utc(AUDIT_END_EXCLUSIVE)

    funding, premium, futures, index, hashes = _load_or_fetch(
        Path(cache_dir),
        allow_download=allow_download,
    )
    funding_audit = audit_funding(funding, start_ms=start_ms, end_ms=end_ms)
    premium_audit = audit_klines(
        premium,
        start_ms=start_ms,
        end_ms=end_ms,
        allow_nonpositive_prices=True,
        futures_activity=False,
    )
    futures_audit = audit_klines(
        futures,
        start_ms=start_ms,
        end_ms=end_ms,
        allow_nonpositive_prices=False,
        futures_activity=True,
    )
    index_audit = audit_klines(
        index,
        start_ms=start_ms,
        end_ms=end_ms,
        allow_nonpositive_prices=False,
        futures_activity=False,
    )
    cross_audit = audit_cross_source(premium, futures, index)

    sections = {
        "funding": funding_audit,
        "premium_index_15m": premium_audit,
        "perpetual_futures_15m": futures_audit,
        "index_price_15m": index_audit,
        "cross_source": cross_audit,
    }
    decision = (
        "ELIGIBLE_FOR_M6_EDGE_DESIGN"
        if all(section["status"] == "PASS" for section in sections.values())
        else "M6_DERIVATIVES_DATA_AUDIT_FAIL"
    )
    report: dict[str, object] = {
        "phase": "m6_derivatives_data_audit",
        "decision": decision,
        "policy_freeze": freeze,
        "source_provenance": provenance,
        "data_boundary": {
            "start": AUDIT_START,
            "end_exclusive": AUDIT_END_EXCLUSIVE,
            "expected_15m_slots": EXPECTED_15M_SLOTS,
            "oos_2025": "LOCKED_NOT_ACCESSED",
        },
        "dataset_sha256": hashes,
        "audits": sections,
        "retention_blocked_sources": RETENTION_BLOCKED,
        "strategy_generation": "FORBIDDEN_REQUIRES_SEPARATE_FROZEN_EDGE_CONTRACT",
        "ai_module": "excluded",
        "live_execution": "forbidden",
        "oos_2025": "LOCKED_NOT_ACCESSED",
    }
    output = Path(report_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_suffix(output.suffix + ".tmp")
    temporary.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
    temporary.replace(output)
    return report


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Audit Binance USD-M BTCUSDT derivatives data for M6 without touching 2025 OOS"
    )
    parser.add_argument("--cache-dir", default="data/cache/m6")
    parser.add_argument("--report", default="artifacts/m6_derivatives_data_audit.json")
    parser.add_argument("--no-download", action="store_true")
    args = parser.parse_args()
    report = run_derivatives_data_audit(
        cache_dir=args.cache_dir,
        report_path=args.report,
        allow_download=not args.no_download,
    )
    print(f"M6 derivatives data audit decision: {report['decision']}")
    for name, section in report["audits"].items():
        print(f"{name}: {section['status']}")
    print("2025 OOS remains LOCKED_NOT_ACCESSED")


if __name__ == "__main__":
    main()
