from __future__ import annotations

from typing import Any

import pytest

import eba_trader.m8_alt_data_audit as audit
from eba_trader.history import parse_utc


def _metric(timestamp_ms: int) -> audit.BinanceMetric:
    return audit.BinanceMetric(
        timestamp_ms=timestamp_ms,
        sum_open_interest=100.0,
        sum_open_interest_value=1_000_000.0,
        count_toptrader_long_short_ratio=1.1,
        sum_toptrader_long_short_ratio=1.2,
        count_long_short_ratio=1.0,
        sum_taker_long_short_vol_ratio=1.05,
    )


def _metrics_csv_row(timestamp: str, *, oi: str = "100") -> list[str]:
    return [
        timestamp,
        "BTCUSDT",
        oi,
        "1000000",
        "1.1",
        "1.2",
        "1.0",
        "1.05",
    ]


def test_metrics_parser_collapses_exact_duplicate_and_flags_conflict() -> None:
    header = list(audit.METRICS_COLUMNS)
    start = parse_utc("2021-01-01T00:00:00Z")
    end = parse_utc("2021-01-01T01:00:00Z")
    first = _metrics_csv_row("2021-01-01 00:05:00")
    conflict = _metrics_csv_row("2021-01-01 00:05:00", oi="101")
    rows, exact, conflicting = audit.parse_binance_metrics_rows(
        [header, first, first, header, conflict],
        start_ms=start,
        end_ms=end,
    )
    assert len(rows) == 1
    assert exact == 1
    assert conflicting == 1
    assert rows[0].sum_open_interest == 100.0


def test_metrics_audit_can_pass_short_frozen_fixture(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(audit, "AUDIT_START", "2021-01-01T00:00:00Z")
    monkeypatch.setattr(audit, "AUDIT_END_EXCLUSIVE", "2021-01-01T01:00:00Z")
    monkeypatch.setattr(audit, "BINANCE_METRICS_MIN_COVERAGE", 1.0)
    monkeypatch.setattr(audit, "BINANCE_METRICS_MAX_MISSING_SLOTS", 0)
    start = parse_utc(audit.AUDIT_START)
    rows = [_metric(start + index * audit.FIVE_MIN_MS) for index in range(1, 12)]
    report = audit.audit_binance_metrics(
        rows,
        {"conflicting_duplicate_timestamps": 0},
    )
    assert report["status"] == "FULL_WINDOW_PASS"
    assert report["coverage"] == 1.0
    assert report["max_missing_five_minute_slots"] == 0


def test_metrics_audit_fails_on_conflicting_duplicate_metadata(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(audit, "AUDIT_START", "2021-01-01T00:00:00Z")
    monkeypatch.setattr(audit, "AUDIT_END_EXCLUSIVE", "2021-01-01T00:10:00Z")
    start = parse_utc(audit.AUDIT_START)
    report = audit.audit_binance_metrics(
        [_metric(start + audit.FIVE_MIN_MS)],
        {"conflicting_duplicate_timestamps": 1},
    )
    assert report["status"] == "FAIL"


def test_bybit_hourly_auditors_pass_complete_short_fixture(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(audit, "AUDIT_START", "2021-01-01T00:00:00Z")
    monkeypatch.setattr(audit, "AUDIT_END_EXCLUSIVE", "2021-01-01T04:00:00Z")
    monkeypatch.setattr(audit, "BYBIT_KLINE_MIN_COVERAGE", 1.0)
    monkeypatch.setattr(audit, "BYBIT_KLINE_MAX_MISSING_HOURS", 0)
    monkeypatch.setattr(audit, "BYBIT_POSITIONING_MIN_COVERAGE", 1.0)
    monkeypatch.setattr(audit, "BYBIT_POSITIONING_MAX_MISSING_HOURS", 0)
    start = parse_utc(audit.AUDIT_START)
    times = [start + index * audit.HOUR_MS for index in range(4)]
    klines = [audit.BybitKline(time, 100, 102, 99, 101, 10, 1000) for time in times]
    oi = [audit.BybitOpenInterest(time, 1000 + index) for index, time in enumerate(times)]
    ratios = [audit.BybitAccountRatio(time, 0.51, 0.49) for time in times]
    assert audit.audit_bybit_kline(klines)["status"] == "PASS"
    assert audit.audit_bybit_open_interest(oi)["status"] == "PASS"
    assert audit.audit_bybit_account_ratio(ratios)["status"] == "PASS"


def test_cross_exchange_alignment_is_causal(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(audit, "AUDIT_START", "2021-01-01T00:00:00Z")
    monkeypatch.setattr(audit, "AUDIT_END_EXCLUSIVE", "2021-01-01T03:00:00Z")
    monkeypatch.setattr(audit, "CROSS_EXCHANGE_MIN_HOURLY_ALIGNMENT", 1.0)
    start = parse_utc(audit.AUDIT_START)
    times = [start + index * audit.HOUR_MS for index in range(3)]
    klines = [audit.BybitKline(time, 100, 101, 99, 100, 1, 100) for time in times]
    oi = [audit.BybitOpenInterest(time, 1000) for time in times]
    metrics = [_metric(time) for time in times]
    report = audit.audit_cross_exchange_alignment(metrics, klines, oi, [])
    assert report["status"] == "PASS"
    assert report["future_metric_violations"] == 0

    future_only = [_metric(time + audit.FIVE_MIN_MS) for time in times]
    failed = audit.audit_cross_exchange_alignment(future_only, klines, oi, [])
    assert failed["status"] == "FAIL"
    assert failed["future_metric_violations"] == 0


def test_bybit_positioning_fetchers_accept_documented_object_rows(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    timestamp = parse_utc("2021-01-01T01:00:00Z")

    def fake_open_interest(*args: Any, **kwargs: Any) -> list[dict[str, str]]:
        _ = args, kwargs
        return [{"timestamp": str(timestamp), "openInterest": "1234.5"}]

    monkeypatch.setattr(audit, "_fetch_bybit_windowed", fake_open_interest)
    rows = audit.fetch_bybit_open_interest()
    assert rows == [audit.BybitOpenInterest(timestamp, 1234.5)]

    def fake_ratio(*args: Any, **kwargs: Any) -> list[dict[str, str]]:
        _ = args, kwargs
        return [{"timestamp": str(timestamp), "buyRatio": "0.52", "sellRatio": "0.48"}]

    monkeypatch.setattr(audit, "_fetch_bybit_windowed", fake_ratio)
    ratios = audit.fetch_bybit_account_ratio()
    assert ratios == [audit.BybitAccountRatio(timestamp, 0.52, 0.48)]


def test_book_depth_parser_checks_schema_cadence_and_exact_duplicates() -> None:
    day = "2023-01-01"
    start = parse_utc(f"{day}T00:00:00Z")
    rows = [["timestamp", "percentage", "depth", "notional"]]
    for timestamp in (start, start + 30_000):
        for percentage in (-5, -4, -3, -2, -1, 1, 2, 3, 4, 5):
            rows.append([str(timestamp), str(percentage), "1.0", "100.0"])
    rows.append(rows[-1])
    result = audit._parse_book_depth_day(rows, day)
    assert result["invalid_rows"] == 0
    assert result["cadence_observations"] == 1
    assert result["cadence_within_limit"] == 1
    assert result["exact_duplicate_rows"] == 1


def test_liquidation_parser_does_not_treat_distinct_same_time_events_as_conflicts() -> None:
    day = "2024-03-31"
    timestamp = parse_utc(f"{day}T12:00:00Z")
    header = ["time", "side", "order_type", "original_quantity", "price"]
    buy = [str(timestamp), "BUY", "LIMIT", "1.0", "50000"]
    sell = [str(timestamp), "SELL", "LIMIT", "2.0", "50001"]
    result = audit._parse_liquidation_day([header, buy, sell, buy], day)
    assert result["invalid_rows"] == 0
    assert result["exact_duplicate_rows"] == 1
    assert result["conflicting_duplicates"] == 0


def test_m8_network_guard_rejects_any_range_beyond_development_window() -> None:
    start = parse_utc("2024-12-31T23:00:00Z")
    forbidden_end = parse_utc("2025-01-01T00:00:00Z") + 1
    with pytest.raises(RuntimeError, match="outside the frozen M8 development audit window"):
        audit._guard_window(start, forbidden_end, context="test")
