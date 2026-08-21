from __future__ import annotations

import argparse
import math
from pathlib import Path
from typing import Any

from . import m8_alt_data_audit as core

_ORIGINAL_METRICS_PARSER = core.parse_binance_metrics_rows
_ORIGINAL_BYBIT_WINDOWED = core._fetch_bybit_windowed
_METRIC_VALUE_START = 2
_METRIC_VALUE_END = 8


def _normalize_metric_row_for_audit(row: list[str]) -> list[str]:
    """Turn malformed frozen metric values into deterministic failing sentinels.

    The audit contract requires every frozen numeric metric to be finite and strictly positive.
    Official archives contain occasional blank values. Those rows must make the audit fail,
    not crash the audit before a complete evidence report can be produced. A zero sentinel
    preserves the row timestamp while guaranteeing the unchanged positivity gate fails.
    """
    normalized = list(row)
    if len(normalized) < _METRIC_VALUE_END:
        return normalized
    for index in range(_METRIC_VALUE_START, _METRIC_VALUE_END):
        try:
            value = float(normalized[index])
        except (TypeError, ValueError):
            normalized[index] = "0"
            continue
        if not math.isfinite(value) or value <= 0:
            normalized[index] = "0"
    return normalized


def parse_binance_metrics_rows_with_frozen_boundary(
    rows: list[list[str]],
    *,
    start_ms: int,
    end_ms: int,
) -> tuple[list[core.BinanceMetric], int, int]:
    """Apply frozen start-boundary handling and fail-safe malformed-value normalization."""
    filtered: list[list[str]] = []
    for row in rows:
        if not row or row[0].strip().lower() == "create_time":
            filtered.append(row)
            continue
        try:
            timestamp_ms = core._parse_timestamp(row[0])
        except (TypeError, ValueError):
            filtered.append(row)
            continue
        if timestamp_ms == start_ms:
            continue
        filtered.append(_normalize_metric_row_for_audit(row))
    return _ORIGINAL_METRICS_PARSER(
        filtered,
        start_ms=start_ms,
        end_ms=end_ms,
    )


def fetch_bybit_windowed_with_endpoint_params(
    path: str,
    *,
    start_ms: int,
    end_ms: int,
    chunk_ms: int,
    base_params: dict[str, object],
    limit: int,
) -> list[Any]:
    """Use the endpoint-specific Bybit time parameter names for the frozen audit."""
    core._guard_window(start_ms, end_ms, context=f"M8 Bybit {path}")
    collected: list[Any] = []
    cursor_start = start_ms
    start_key, end_key = (
        ("start", "end") if path == "/v5/market/kline" else ("startTime", "endTime")
    )
    while cursor_start < end_ms:
        cursor_end = min(cursor_start + chunk_ms, end_ms)
        page_cursor = ""
        seen_cursors: set[str] = set()
        while True:
            params: dict[str, object] = {
                **base_params,
                start_key: cursor_start,
                end_key: cursor_end - 1,
                "limit": limit,
            }
            if page_cursor:
                params["cursor"] = page_cursor
            payload = core._request_json(path, params)
            rows, next_cursor = core._result_list(payload)
            collected.extend(rows)
            if not next_cursor:
                break
            if next_cursor in seen_cursors:
                raise RuntimeError("Bybit pagination cursor did not advance")
            seen_cursors.add(next_cursor)
            page_cursor = next_cursor
        cursor_start = cursor_end
    return collected


def run_m8_data_audit(
    *,
    report_path: str | Path = "artifacts/m8_alt_derivatives_data_audit.json",
    workers: int = 8,
) -> dict[str, object]:
    original_parser = core.parse_binance_metrics_rows
    original_bybit_windowed = core._fetch_bybit_windowed
    core.parse_binance_metrics_rows = parse_binance_metrics_rows_with_frozen_boundary
    core._fetch_bybit_windowed = fetch_bybit_windowed_with_endpoint_params
    try:
        return core.run_m8_data_audit(report_path=report_path, workers=workers)
    finally:
        core.parse_binance_metrics_rows = original_parser
        core._fetch_bybit_windowed = original_bybit_windowed


def _source_status(section: dict[str, Any], key: str) -> object:
    value = section[key]
    if not isinstance(value, dict):
        raise RuntimeError(f"Invalid M8 report section: {key}")
    return value["status"]


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
    if not isinstance(primary, dict) or not isinstance(secondary, dict):
        raise RuntimeError("Invalid M8 report structure")
    print(f"M8 decision: {report['decision']}")
    print(f"Binance metrics: {_source_status(primary, 'binance_metrics_5m')}")
    print(f"Bybit kline: {_source_status(primary, 'bybit_kline_1h')}")
    print(f"Bybit open interest: {_source_status(primary, 'bybit_open_interest_1h')}")
    print(f"Bybit account ratio: {_source_status(primary, 'bybit_account_ratio_1h')}")
    print(f"Bybit funding: {_source_status(primary, 'bybit_funding')}")
    print(
        "Cross-exchange alignment: "
        f"{_source_status(primary, 'cross_exchange_hourly_alignment')}"
    )
    print(f"BookDepth: {_source_status(secondary, 'binance_book_depth_partial')}")
    print(f"Liquidation: {_source_status(secondary, 'binance_liquidation_snapshot')}")
    print("Forward returns: NOT_COMPUTED")
    print("2025 OOS remains LOCKED_NOT_ACCESSED")


if __name__ == "__main__":
    main()
