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

from .derivatives_archive_seed import _csv_rows_from_zip, _download_verified_archive
from .derivatives_audit import DerivativeKline, _kline_from_row
from .history import parse_utc
from .m10_cross_asset_audit import _write_report_once
from .m11_eth_perpetual_policy import (
    ARCHIVE_BASE,
    AUDIT_END_EXCLUSIVE,
    AUDIT_START,
    EXPECTED_MONTHLY_ARCHIVES,
    EXPECTED_SLOTS,
    INTERVAL,
    MAX_MISSING_RUN_BARS,
    MIN_COVERAGE,
    STEP_MS,
    SYMBOL,
    sha256_file,
    verify_m11_freeze,
)
from .provenance import collect_source_provenance


@dataclass(frozen=True, slots=True)
class ParseResult:
    rows: tuple[DerivativeKline, ...]
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
    rows: tuple[DerivativeKline, ...]
    error: str | None = None


def month_range() -> tuple[tuple[int, int], ...]:
    return tuple((year, month) for year in range(2021, 2025) for month in range(1, 13))


def archive_url(year: int, month: int) -> str:
    stamp = f"{year:04d}-{month:02d}"
    filename = f"{SYMBOL}-{INTERVAL}-{stamp}.zip"
    return f"{ARCHIVE_BASE}/{SYMBOL}/{INTERVAL}/{filename}"


def assert_m11_window(start_ms: int, end_ms: int) -> None:
    frozen_start = parse_utc(AUDIT_START)
    frozen_end = parse_utc(AUDIT_END_EXCLUSIVE)
    if start_ms != frozen_start or end_ms != frozen_end:
        raise RuntimeError("M11 may access only the exact frozen 2021-2024 audit window")
    if end_ms > parse_utc("2025-01-01T00:00:00Z"):
        raise RuntimeError("M11 must not access 2025 OOS data")


def _is_integer(text: str) -> bool:
    try:
        int(text)
    except ValueError:
        return False
    return True


def _finite(values: tuple[float, ...]) -> bool:
    return all(math.isfinite(value) for value in values)


def _numeric_integrity(row: DerivativeKline) -> bool:
    if (
        row.volume is None
        or row.quote_volume is None
        or row.trade_count is None
        or row.taker_buy_base_volume is None
        or row.taker_buy_quote_volume is None
    ):
        return False
    numeric = (
        row.open,
        row.high,
        row.low,
        row.close,
        row.volume,
        row.quote_volume,
        float(row.trade_count),
        row.taker_buy_base_volume,
        row.taker_buy_quote_volume,
    )
    tolerance = 1e-9
    return (
        _finite(numeric)
        and min(row.open, row.high, row.low, row.close) > 0
        and row.high >= max(row.open, row.close)
        and row.low <= min(row.open, row.close)
        and row.high >= row.low
        and row.volume >= 0
        and row.quote_volume >= 0
        and row.trade_count >= 0
        and row.taker_buy_base_volume >= 0
        and row.taker_buy_quote_volume >= 0
        and row.taker_buy_base_volume <= row.volume + tolerance * max(1.0, row.volume)
        and row.taker_buy_quote_volume
        <= row.quote_volume + tolerance * max(1.0, row.quote_volume)
    )


def parse_kline_rows(
    rows: list[list[str]],
    *,
    start_ms: int,
    end_ms: int,
) -> ParseResult:
    parsed: list[DerivativeKline] = []
    source_rows = 0
    invalid_rows = 0
    alignment_violations = 0
    close_time_violations = 0
    numeric_integrity_violations = 0

    for raw in rows:
        if not raw or not _is_integer(raw[0].strip()):
            continue
        source_rows += 1
        try:
            row = _kline_from_row(raw, futures_activity=True)
        except (ValueError, TypeError, IndexError, OverflowError):
            invalid_rows += 1
            continue
        if not start_ms <= row.open_time_ms < end_ms:
            invalid_rows += 1
            continue
        if row.open_time_ms % STEP_MS != 0:
            alignment_violations += 1
            continue
        if row.close_time_ms != row.open_time_ms + STEP_MS - 1:
            close_time_violations += 1
            continue
        if not _numeric_integrity(row):
            numeric_integrity_violations += 1
            continue
        parsed.append(row)

    return ParseResult(
        rows=tuple(parsed),
        source_rows=source_rows,
        invalid_rows=invalid_rows,
        alignment_violations=alignment_violations,
        close_time_violations=close_time_violations,
        numeric_integrity_violations=numeric_integrity_violations,
    )


def _row_key(row: DerivativeKline) -> tuple[object, ...]:
    return (
        row.open,
        row.high,
        row.low,
        row.close,
        row.close_time_ms,
        row.volume,
        row.quote_volume,
        row.trade_count,
        row.taker_buy_base_volume,
        row.taker_buy_quote_volume,
    )


def deduplicate_klines(
    rows: list[DerivativeKline] | tuple[DerivativeKline, ...],
) -> tuple[tuple[DerivativeKline, ...], int, int]:
    grouped: dict[int, list[DerivativeKline]] = defaultdict(list)
    for row in rows:
        grouped[row.open_time_ms].append(row)

    normalized: list[DerivativeKline] = []
    exact_duplicates = 0
    conflicts = 0
    for timestamp in sorted(grouped):
        group = grouped[timestamp]
        unique = sorted(set(group), key=_row_key)
        exact_duplicates += len(group) - len(unique)
        if len(unique) > 1:
            conflicts += 1
        normalized.append(unique[0])
    return tuple(normalized), exact_duplicates, conflicts


def _month_worker(year: int, month: int, *, start_ms: int, end_ms: int) -> MonthResult:
    month_text = f"{year:04d}-{month:02d}"
    url = archive_url(year, month)
    try:
        downloaded = _download_verified_archive(url)
        if downloaded is None:
            return MonthResult(month_text, url, "MISSING", None, 0, 0, 0, 0, 0, ())
        payload, checksum = downloaded
        parsed = parse_kline_rows(
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
    except (RuntimeError, ValueError, TypeError, IndexError, KeyError) as error:
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
    assert_m11_window(start_ms, end_ms)

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


def _max_missing_run(timestamps: set[int], start_ms: int, end_ms: int) -> int:
    current = 0
    maximum = 0
    cursor = start_ms
    while cursor < end_ms:
        if cursor in timestamps:
            current = 0
        else:
            current += 1
            maximum = max(maximum, current)
        cursor += STEP_MS
    return maximum


def write_normalized_csv(rows: tuple[DerivativeKline, ...], path: str | Path) -> Path:
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
                "close_time_ms",
                "volume",
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
                    row.close_time_ms,
                    row.volume,
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
    normalized: tuple[DerivativeKline, ...],
    conflicting_timestamps: int,
) -> dict[str, bool]:
    start_ms = parse_utc(AUDIT_START)
    end_ms = parse_utc(AUDIT_END_EXCLUSIVE)
    observed = {row.open_time_ms for row in normalized}
    timestamps = [row.open_time_ms for row in normalized]
    coverage = len(observed) / EXPECTED_SLOTS
    missing_run = _max_missing_run(observed, start_ms, end_ms)
    return {
        "01_all_48_monthly_archives_exist": len(months) == EXPECTED_MONTHLY_ARCHIVES
        and all(item.status != "MISSING" for item in months),
        "02_all_48_checksums_verified": len(months) == EXPECTED_MONTHLY_ARCHIVES
        and all(item.status == "PASS" and item.checksum_sha256 is not None for item in months),
        "03_no_monthly_parse_errors": all(item.status != "ERROR" for item in months),
        "04_no_conflicting_duplicate_timestamps": conflicting_timestamps == 0,
        "05_exact_first_timestamp": bool(normalized) and normalized[0].open_time_ms == start_ms,
        "06_exact_last_timestamp": bool(normalized)
        and normalized[-1].open_time_ms == end_ms - STEP_MS,
        "07_unique_strictly_increasing_timestamps": len(timestamps) == len(set(timestamps))
        and all(left < right for left, right in zip(timestamps, timestamps[1:], strict=False)),
        "08_all_open_timestamps_15m_aligned": sum(
            item.alignment_violations for item in months
        )
        == 0,
        "09_exact_close_time_semantics": sum(item.close_time_violations for item in months) == 0,
        "10_numeric_activity_integrity": sum(
            item.invalid_rows + item.numeric_integrity_violations for item in months
        )
        == 0,
        "11_coverage_at_least_99_95_percent": coverage >= MIN_COVERAGE,
        "12_max_missing_run_at_most_12_bars": missing_run <= MAX_MISSING_RUN_BARS,
        "13_row_count_not_above_expected": len(normalized) <= EXPECTED_SLOTS,
        "14_oos_2025_locked": end_ms <= parse_utc("2025-01-01T00:00:00Z"),
    }


def run_m11_eth_perpetual_audit(
    *,
    workers: int = 8,
    report_path: str | Path = "artifacts/m11_eth_perpetual_data_audit.json",
    normalized_path: str | Path = "artifacts/m11_ethusdt_usdm_15m_normalized.csv",
) -> dict[str, Any]:
    report_output = Path(report_path)
    normalized_output = Path(normalized_path)
    if report_output.exists():
        raise RuntimeError("M11 audit report already exists; preserve the first complete result")

    freeze = verify_m11_freeze()
    provenance = collect_source_provenance(require_clean=True)
    start_ms = parse_utc(AUDIT_START)
    end_ms = parse_utc(AUDIT_END_EXCLUSIVE)
    assert_m11_window(start_ms, end_ms)
    if (end_ms - start_ms) // STEP_MS != EXPECTED_SLOTS:
        raise RuntimeError("M11 expected slot count disagrees with the frozen window")

    months = acquire_monthly_archives(workers=workers)
    all_rows = [row for month in months for row in month.rows]
    normalized, exact_duplicates, conflicts = deduplicate_klines(all_rows)
    normalized_file = write_normalized_csv(normalized, normalized_output)
    normalized_sha256 = sha256_file(normalized_file)

    observed = {row.open_time_ms for row in normalized}
    coverage = len(observed) / EXPECTED_SLOTS
    max_missing_run = _max_missing_run(observed, start_ms, end_ms)
    gates = evaluate_gates(
        months=months,
        normalized=normalized,
        conflicting_timestamps=conflicts,
    )
    decision = (
        "M11_ETH_PERPETUAL_DATA_AUDIT_PASS"
        if all(gates.values())
        else "M11_ETH_PERPETUAL_DATA_AUDIT_FAIL"
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
        "phase": "m11_eth_perpetual_historical_data_audit_only",
        "decision": decision,
        "policy_freeze": freeze,
        "source_provenance": provenance,
        "data_boundary": {
            "audit": f"{AUDIT_START}/{AUDIT_END_EXCLUSIVE}",
            "oos_2025": "LOCKED_NOT_ACCESSED",
        },
        "source": {
            "provider": "Binance Vision",
            "market": "USD-M perpetual futures",
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
            "missing_slots": EXPECTED_SLOTS - len(observed),
            "max_missing_run_bars": max_missing_run,
            "exact_duplicate_rows": exact_duplicates,
            "conflicting_duplicate_timestamps": conflicts,
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
    parser = argparse.ArgumentParser(description="Run the frozen M11 ETH perpetual data audit")
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument("--report", default="artifacts/m11_eth_perpetual_data_audit.json")
    parser.add_argument("--normalized", default="artifacts/m11_ethusdt_usdm_15m_normalized.csv")
    args = parser.parse_args()
    report = run_m11_eth_perpetual_audit(
        workers=args.workers,
        report_path=args.report,
        normalized_path=args.normalized,
    )
    normalized = report["normalized"]
    print("M11 decision:", report["decision"])
    print("coverage:", normalized["coverage"])
    print("accepted_unique_rows:", normalized["accepted_unique_rows"])
    print("missing_slots:", normalized["missing_slots"])
    print("max_missing_run_bars:", normalized["max_missing_run_bars"])
    print("normalized_csv_sha256:", normalized["csv_sha256"])
    print("2025 OOS remains LOCKED_NOT_ACCESSED")


if __name__ == "__main__":
    main()
