from __future__ import annotations

import argparse
import csv
import json
import math
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .history import parse_utc
from .m8_alt_data_audit import _csv_rows_from_zip, _download_verified_archive, _max_missing_run
from .m10_cross_asset_policy import (
    AUDIT_END_EXCLUSIVE,
    AUDIT_START,
    BINANCE_VISION_SPOT_MONTHLY,
    EXPECTED_MONTHLY_ARCHIVES,
    EXPECTED_SLOTS,
    INTERVAL,
    MAX_MISSING_RUN_BARS,
    MIN_COVERAGE,
    STEP_MS,
    SYMBOL,
    sha256_file,
    verify_m10_freeze,
)
from .provenance import collect_source_provenance


@dataclass(frozen=True, slots=True)
class CrossAssetKline:
    open_time_ms: int
    open: float
    high: float
    low: float
    close: float
    volume: float
    close_time_ms: int
    quote_volume: float
    trade_count: int
    taker_buy_base_volume: float
    taker_buy_quote_volume: float


@dataclass(frozen=True, slots=True)
class ParseResult:
    rows: tuple[CrossAssetKline, ...]
    source_rows: int
    invalid_rows: int
    alignment_violations: int
    close_time_violations: int
    numeric_integrity_violations: int


@dataclass(frozen=True, slots=True)
class MonthResult:
    month: str
    url: str
    status: str
    checksum_sha256: str | None
    source_rows: int
    invalid_rows: int
    alignment_violations: int
    close_time_violations: int
    numeric_integrity_violations: int
    rows: tuple[CrossAssetKline, ...]
    error: str | None = None


def month_range() -> tuple[tuple[int, int], ...]:
    return tuple((year, month) for year in range(2021, 2025) for month in range(1, 13))


def _archive_url(year: int, month: int) -> str:
    filename = f"{SYMBOL}-{INTERVAL}-{year:04d}-{month:02d}.zip"
    return f"{BINANCE_VISION_SPOT_MONTHLY}/{SYMBOL}/{INTERVAL}/{filename}"


def assert_m10_window(start_ms: int, end_ms: int) -> None:
    frozen_start = parse_utc(AUDIT_START)
    frozen_end = parse_utc(AUDIT_END_EXCLUSIVE)
    if start_ms != frozen_start or end_ms != frozen_end:
        raise RuntimeError("M10 may access only the exact frozen 2021-2024 audit window")
    if end_ms > parse_utc("2025-01-01T00:00:00Z"):
        raise RuntimeError("M10 must not access 2025 OOS data")


def _looks_like_header(row: list[str]) -> bool:
    if not row:
        return False
    first = row[0].strip().lower()
    if first in {"open_time", "open time", "opentime"}:
        return True
    try:
        int(first)
    except ValueError:
        return True
    return False


def _finite(values: tuple[float, ...]) -> bool:
    return all(math.isfinite(value) for value in values)


def parse_spot_kline_rows(
    rows: list[list[str]],
    *,
    start_ms: int,
    end_ms: int,
) -> ParseResult:
    if not rows:
        return ParseResult((), 0, 0, 0, 0, 0)

    data_rows = rows[1:] if _looks_like_header(rows[0]) else rows
    parsed: list[CrossAssetKline] = []
    invalid_rows = 0
    alignment_violations = 0
    close_time_violations = 0
    numeric_integrity_violations = 0

    for row in data_rows:
        if not row or _looks_like_header(row):
            continue
        if len(row) < 11:
            invalid_rows += 1
            continue
        try:
            open_time_ms = int(row[0].strip())
            open_price = float(row[1])
            high = float(row[2])
            low = float(row[3])
            close = float(row[4])
            volume = float(row[5])
            close_time_ms = int(row[6].strip())
            quote_volume = float(row[7])
            trade_count_float = float(row[8])
            taker_buy_base = float(row[9])
            taker_buy_quote = float(row[10])
        except (ValueError, OverflowError):
            invalid_rows += 1
            continue

        if not start_ms <= open_time_ms < end_ms:
            invalid_rows += 1
            continue
        if open_time_ms % STEP_MS != 0:
            alignment_violations += 1
            continue
        if close_time_ms != open_time_ms + STEP_MS - 1:
            close_time_violations += 1
            continue
        numeric_values = (
            open_price,
            high,
            low,
            close,
            volume,
            quote_volume,
            trade_count_float,
            taker_buy_base,
            taker_buy_quote,
        )
        tolerance = 1e-9
        numeric_ok = (
            _finite(numeric_values)
            and min(open_price, high, low, close) > 0
            and high >= max(open_price, close)
            and low <= min(open_price, close)
            and high >= low
            and volume >= 0
            and quote_volume >= 0
            and trade_count_float >= 0
            and trade_count_float.is_integer()
            and taker_buy_base >= 0
            and taker_buy_quote >= 0
            and taker_buy_base <= volume + tolerance * max(1.0, volume)
            and taker_buy_quote <= quote_volume + tolerance * max(1.0, quote_volume)
        )
        if not numeric_ok:
            numeric_integrity_violations += 1
            continue

        parsed.append(
            CrossAssetKline(
                open_time_ms=open_time_ms,
                open=open_price,
                high=high,
                low=low,
                close=close,
                volume=volume,
                close_time_ms=close_time_ms,
                quote_volume=quote_volume,
                trade_count=int(trade_count_float),
                taker_buy_base_volume=taker_buy_base,
                taker_buy_quote_volume=taker_buy_quote,
            )
        )

    return ParseResult(
        rows=tuple(parsed),
        source_rows=len(data_rows),
        invalid_rows=invalid_rows,
        alignment_violations=alignment_violations,
        close_time_violations=close_time_violations,
        numeric_integrity_violations=numeric_integrity_violations,
    )


def _row_key(row: CrossAssetKline) -> tuple[object, ...]:
    return (
        row.open,
        row.high,
        row.low,
        row.close,
        row.volume,
        row.close_time_ms,
        row.quote_volume,
        row.trade_count,
        row.taker_buy_base_volume,
        row.taker_buy_quote_volume,
    )


def deduplicate_klines(
    rows: list[CrossAssetKline] | tuple[CrossAssetKline, ...],
) -> tuple[tuple[CrossAssetKline, ...], int, int]:
    grouped: dict[int, list[CrossAssetKline]] = defaultdict(list)
    for row in rows:
        grouped[row.open_time_ms].append(row)

    normalized: list[CrossAssetKline] = []
    exact_duplicates = 0
    conflicting_timestamps = 0
    for timestamp in sorted(grouped):
        group = grouped[timestamp]
        unique = sorted(set(group), key=_row_key)
        exact_duplicates += len(group) - len(unique)
        if len(unique) > 1:
            conflicting_timestamps += 1
        normalized.append(unique[0])
    return tuple(normalized), exact_duplicates, conflicting_timestamps


def _month_worker(year: int, month: int, *, start_ms: int, end_ms: int) -> MonthResult:
    month_text = f"{year:04d}-{month:02d}"
    url = _archive_url(year, month)
    try:
        downloaded = _download_verified_archive(url)
        if downloaded is None:
            return MonthResult(month_text, url, "MISSING", None, 0, 0, 0, 0, 0, ())
        payload, checksum = downloaded
        parsed = parse_spot_kline_rows(
            _csv_rows_from_zip(payload),
            start_ms=start_ms,
            end_ms=end_ms,
        )
        return MonthResult(
            month=month_text,
            url=url,
            status="PASS",
            checksum_sha256=checksum,
            source_rows=parsed.source_rows,
            invalid_rows=parsed.invalid_rows,
            alignment_violations=parsed.alignment_violations,
            close_time_violations=parsed.close_time_violations,
            numeric_integrity_violations=parsed.numeric_integrity_violations,
            rows=parsed.rows,
        )
    except (RuntimeError, ValueError, IndexError, KeyError) as error:
        return MonthResult(
            month=month_text,
            url=url,
            status="ERROR",
            checksum_sha256=None,
            source_rows=0,
            invalid_rows=0,
            alignment_violations=0,
            close_time_violations=0,
            numeric_integrity_violations=0,
            rows=(),
            error=str(error),
        )


def acquire_monthly_archives(*, workers: int = 8) -> tuple[MonthResult, ...]:
    if workers < 1 or workers > 12:
        raise ValueError("workers must be between 1 and 12")
    start_ms = parse_utc(AUDIT_START)
    end_ms = parse_utc(AUDIT_END_EXCLUSIVE)
    assert_m10_window(start_ms, end_ms)

    results: list[MonthResult] = []
    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = {
            executor.submit(_month_worker, year, month, start_ms=start_ms, end_ms=end_ms): (
                year,
                month,
            )
            for year, month in month_range()
        }
        for future in as_completed(futures):
            results.append(future.result())
    results.sort(key=lambda item: item.month)
    return tuple(results)


def write_normalized_csv(
    rows: tuple[CrossAssetKline, ...],
    path: str | Path,
) -> Path:
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle, lineterminator="\n")
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
                "taker_buy_base_volume",
                "taker_buy_quote_volume",
            ]
        )
        for row in rows:
            writer.writerow(
                [
                    row.open_time_ms,
                    row.open,
                    row.high,
                    row.low,
                    row.close,
                    row.volume,
                    row.close_time_ms,
                    row.quote_volume,
                    row.trade_count,
                    row.taker_buy_base_volume,
                    row.taker_buy_quote_volume,
                ]
            )
    return output


def evaluate_gates(
    *,
    months: tuple[MonthResult, ...],
    normalized: tuple[CrossAssetKline, ...],
    exact_duplicates: int,
    conflicting_timestamps: int,
) -> dict[str, bool]:
    start_ms = parse_utc(AUDIT_START)
    end_ms = parse_utc(AUDIT_END_EXCLUSIVE)
    observed = {row.open_time_ms for row in normalized}
    coverage = len(observed) / EXPECTED_SLOTS
    missing_run = _max_missing_run(observed, start_ms, end_ms, STEP_MS)
    all_months = len(months) == EXPECTED_MONTHLY_ARCHIVES and all(
        item.status != "MISSING" for item in months
    )
    checksums = len(months) == EXPECTED_MONTHLY_ARCHIVES and all(
        item.status == "PASS" and item.checksum_sha256 is not None for item in months
    )
    no_parse_errors = all(item.status != "ERROR" for item in months)
    alignment_ok = sum(item.alignment_violations for item in months) == 0
    close_time_ok = sum(item.close_time_violations for item in months) == 0
    numeric_ok = sum(item.invalid_rows + item.numeric_integrity_violations for item in months) == 0
    timestamps = [row.open_time_ms for row in normalized]
    unique_increasing = len(timestamps) == len(set(timestamps)) and all(
        left < right for left, right in zip(timestamps, timestamps[1:], strict=False)
    )
    return {
        "01_all_48_monthly_archives_exist": all_months,
        "02_all_48_checksums_verified": checksums,
        "03_no_monthly_parse_errors": no_parse_errors,
        "04_no_conflicting_duplicate_timestamps": conflicting_timestamps == 0,
        "05_exact_first_timestamp": bool(normalized) and normalized[0].open_time_ms == start_ms,
        "06_exact_last_timestamp": bool(normalized)
        and normalized[-1].open_time_ms == end_ms - STEP_MS,
        "07_unique_strictly_increasing_timestamps": unique_increasing,
        "08_all_open_timestamps_15m_aligned": alignment_ok,
        "09_exact_close_time_semantics": close_time_ok,
        "10_numeric_integrity": numeric_ok,
        "11_coverage_at_least_99_95_percent": coverage >= MIN_COVERAGE,
        "12_max_missing_run_at_most_12_bars": missing_run <= MAX_MISSING_RUN_BARS,
        "13_row_count_not_above_expected": len(normalized) <= EXPECTED_SLOTS,
        "14_oos_2025_locked": end_ms <= parse_utc("2025-01-01T00:00:00Z"),
        "diagnostic_exact_duplicate_rows_nonnegative": exact_duplicates >= 0,
    }


def _write_report_once(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with path.open("x", encoding="utf-8") as handle:
            handle.write(json.dumps(payload, indent=2, sort_keys=True, allow_nan=False))
    except FileExistsError as error:
        raise RuntimeError(
            "M10 audit report already exists; preserve the first complete result"
        ) from error


def run_m10_cross_asset_audit(
    *,
    workers: int = 8,
    report_path: str | Path = "artifacts/m10_cross_asset_data_audit.json",
    normalized_path: str | Path = "artifacts/m10_ethusdt_15m_normalized.csv",
) -> dict[str, Any]:
    report_output = Path(report_path)
    normalized_output = Path(normalized_path)
    if report_output.exists():
        raise RuntimeError("M10 audit report already exists; preserve the first complete result")

    freeze = verify_m10_freeze()
    provenance = collect_source_provenance(require_clean=True)
    start_ms = parse_utc(AUDIT_START)
    end_ms = parse_utc(AUDIT_END_EXCLUSIVE)
    assert_m10_window(start_ms, end_ms)
    if (end_ms - start_ms) // STEP_MS != EXPECTED_SLOTS:
        raise RuntimeError("M10 expected slot count disagrees with the frozen window")

    months = acquire_monthly_archives(workers=workers)
    all_rows = [row for month in months for row in month.rows]
    normalized, exact_duplicates, conflicting_timestamps = deduplicate_klines(all_rows)
    normalized_file = write_normalized_csv(normalized, normalized_output)
    normalized_sha256 = sha256_file(normalized_file)

    observed = {row.open_time_ms for row in normalized}
    missing_slots = EXPECTED_SLOTS - len(observed)
    max_missing_run = _max_missing_run(observed, start_ms, end_ms, STEP_MS)
    coverage = len(observed) / EXPECTED_SLOTS
    gates = evaluate_gates(
        months=months,
        normalized=normalized,
        exact_duplicates=exact_duplicates,
        conflicting_timestamps=conflicting_timestamps,
    )
    required_gates = {key: value for key, value in gates.items() if key[:2].isdigit()}
    decision = (
        "M10_CROSS_ASSET_DATA_AUDIT_PASS"
        if all(required_gates.values())
        else "M10_CROSS_ASSET_DATA_AUDIT_FAIL"
    )

    manifest = [
        {
            "month": item.month,
            "status": item.status,
            "checksum_sha256": item.checksum_sha256,
            "source_rows": item.source_rows,
            "invalid_rows": item.invalid_rows,
            "alignment_violations": item.alignment_violations,
            "close_time_violations": item.close_time_violations,
            "numeric_integrity_violations": item.numeric_integrity_violations,
            "error": item.error,
        }
        for item in months
    ]
    report: dict[str, Any] = {
        "phase": "m10_cross_asset_historical_data_audit_only",
        "decision": decision,
        "policy_freeze": freeze,
        "source_provenance": provenance,
        "data_boundary": {
            "audit": f"{AUDIT_START}/{AUDIT_END_EXCLUSIVE}",
            "oos_2025": "LOCKED_NOT_ACCESSED",
        },
        "source": {
            "provider": "Binance Vision",
            "market": "Spot",
            "symbol": SYMBOL,
            "interval": INTERVAL,
            "monthly_archives_expected": EXPECTED_MONTHLY_ARCHIVES,
            "monthly_archives_present": sum(item.status != "MISSING" for item in months),
            "checksum_verified_files": sum(item.status == "PASS" for item in months),
            "parse_error_files": sum(item.status == "ERROR" for item in months),
            "missing_months": [item.month for item in months if item.status == "MISSING"],
            "manifest": manifest,
        },
        "normalized": {
            "source_rows": sum(item.source_rows for item in months),
            "accepted_unique_rows": len(normalized),
            "expected_rows": EXPECTED_SLOTS,
            "coverage": coverage,
            "missing_slots": missing_slots,
            "max_missing_run_bars": max_missing_run,
            "exact_duplicate_rows": exact_duplicates,
            "conflicting_duplicate_timestamps": conflicting_timestamps,
            "invalid_rows": sum(item.invalid_rows for item in months),
            "alignment_violations": sum(item.alignment_violations for item in months),
            "close_time_violations": sum(item.close_time_violations for item in months),
            "numeric_integrity_violations": sum(
                item.numeric_integrity_violations for item in months
            ),
            "first_open_time_ms": normalized[0].open_time_ms if normalized else None,
            "last_open_time_ms": normalized[-1].open_time_ms if normalized else None,
            "csv_path": str(normalized_file),
            "csv_sha256": normalized_sha256,
        },
        "gates": gates,
        "forward_returns": "FORBIDDEN_NOT_COMPUTED",
        "strategy_generation": "FORBIDDEN",
        "risk_sizing": "FORBIDDEN",
        "ai_module": "EXCLUDED",
        "live_execution": "FORBIDDEN",
        "oos_2025": "LOCKED_NOT_ACCESSED",
    }
    _write_report_once(report_output, report)
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the frozen M10 ETHUSDT historical data audit")
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument("--report", default="artifacts/m10_cross_asset_data_audit.json")
    parser.add_argument("--normalized", default="artifacts/m10_ethusdt_15m_normalized.csv")
    args = parser.parse_args()
    report = run_m10_cross_asset_audit(
        workers=args.workers,
        report_path=args.report,
        normalized_path=args.normalized,
    )
    normalized = report["normalized"]
    print("M10 decision:", report["decision"])
    print("coverage:", normalized["coverage"])
    print("accepted_unique_rows:", normalized["accepted_unique_rows"])
    print("missing_slots:", normalized["missing_slots"])
    print("max_missing_run_bars:", normalized["max_missing_run_bars"])
    print("normalized_csv_sha256:", normalized["csv_sha256"])
    print("2025 OOS remains LOCKED_NOT_ACCESSED")


if __name__ == "__main__":
    main()
