from __future__ import annotations

from dataclasses import replace

import pytest

import eba_trader.derivatives_audit as audit
from eba_trader.derivatives_audit import (
    DerivativeKline,
    FundingRecord,
    _kline_from_row,
    audit_cross_source,
    audit_funding,
    audit_klines,
    fetch_funding_history,
)
from eba_trader.derivatives_audit_policy import (
    AUDIT_END_EXCLUSIVE,
    AUDIT_START,
    RETENTION_BLOCKED,
    canonical_text_sha256,
    verify_m6_audit_freeze,
)
from eba_trader.history import parse_utc


def _kline(index: int, *, start_ms: int = 0) -> DerivativeKline:
    open_time = start_ms + index * audit.INTERVAL_MS
    return DerivativeKline(
        open_time_ms=open_time,
        open=100.0,
        high=101.0,
        low=99.0,
        close=100.5,
        close_time_ms=open_time + audit.INTERVAL_MS - 1,
        volume=10.0,
        quote_volume=1000.0,
        trade_count=20,
        taker_buy_base_volume=5.0,
        taker_buy_quote_volume=500.0,
    )


def test_m6_freeze_matches_protocol_and_preserves_oos_lock() -> None:
    manifest = verify_m6_audit_freeze()
    assert manifest["oos_2025"] == "LOCKED_NOT_ACCESSED"
    assert manifest["strategy_generation"] == "forbidden"
    assert manifest["protocol_sha256"] == canonical_text_sha256(
        "docs/M6_DERIVATIVES_DATA_AUDIT_PROTOCOL.md"
    )


def test_retention_blocked_sources_are_explicitly_excluded() -> None:
    assert RETENTION_BLOCKED["open_interest_statistics"]["documented_retention"] == "latest_1_month"
    assert RETENTION_BLOCKED["basis"]["documented_retention"] == "latest_30_days"


def test_2025_overlap_fails_before_any_network_request(monkeypatch) -> None:
    called = False

    def fake_request(*args, **kwargs):
        nonlocal called
        called = True
        return []

    monkeypatch.setattr(audit, "_request_json", fake_request)

    with pytest.raises(RuntimeError, match="outside the frozen M6 development audit window"):
        fetch_funding_history(
            parse_utc("2025-01-01T00:00:00Z"),
            parse_utc("2025-01-02T00:00:00Z"),
        )

    assert called is False


def test_funding_audit_accepts_complete_eight_hour_history() -> None:
    start = parse_utc(AUDIT_START)
    end = parse_utc(AUDIT_END_EXCLUSIVE)
    step = 8 * audit.HOUR_MS
    rows = [
        FundingRecord(
            symbol="BTCUSDT",
            funding_time_ms=timestamp,
            funding_rate=0.0001,
            mark_price=30_000.0,
        )
        for timestamp in range(start, end, step)
    ]

    result = audit_funding(rows, start_ms=start, end_ms=end)

    assert result["status"] == "PASS"
    assert result["record_count"] >= 4000
    assert result["median_cadence_hours"] == pytest.approx(8.0)


def test_funding_audit_rejects_duplicate_and_large_gap() -> None:
    start = parse_utc(AUDIT_START)
    end = parse_utc(AUDIT_END_EXCLUSIVE)
    step = 8 * audit.HOUR_MS
    rows = [
        FundingRecord("BTCUSDT", timestamp, 0.0001)
        for timestamp in range(start, end, step)
    ]
    rows[100] = replace(rows[99])
    rows[101] = replace(rows[99])
    rows[102] = replace(rows[99])

    result = audit_funding(rows, start_ms=start, end_ms=end)

    assert result["status"] == "FAIL"
    assert result["checks"]["strict_unique_order"] is False
    assert result["checks"]["maximum_cadence"] is False


def test_kline_parser_preserves_futures_activity_fields() -> None:
    row = [
        0,
        "100",
        "110",
        "90",
        "105",
        "12.5",
        audit.INTERVAL_MS - 1,
        "1300",
        42,
        "7.0",
        "730",
        "0",
    ]

    parsed = _kline_from_row(row, futures_activity=True)

    assert parsed.volume == pytest.approx(12.5)
    assert parsed.quote_volume == pytest.approx(1300.0)
    assert parsed.trade_count == 42
    assert parsed.taker_buy_base_volume == pytest.approx(7.0)


def test_kline_and_cross_source_audits_use_frozen_coverage(monkeypatch) -> None:
    start = parse_utc(AUDIT_START)
    slots = 10
    end = start + slots * audit.INTERVAL_MS
    monkeypatch.setattr(audit, "EXPECTED_15M_SLOTS", slots)

    futures = [_kline(index, start_ms=start) for index in range(slots)]
    premium = [
        replace(
            row,
            open=0.0001,
            high=0.0002,
            low=-0.0001,
            close=0.0,
            volume=None,
            quote_volume=None,
            trade_count=None,
            taker_buy_base_volume=None,
            taker_buy_quote_volume=None,
        )
        for row in futures
    ]
    index = [
        replace(
            row,
            open=99.0,
            high=100.0,
            low=98.0,
            close=99.5,
            volume=None,
            quote_volume=None,
            trade_count=None,
            taker_buy_base_volume=None,
            taker_buy_quote_volume=None,
        )
        for row in futures
    ]

    assert audit_klines(
        futures,
        start_ms=start,
        end_ms=end,
        allow_nonpositive_prices=False,
        futures_activity=True,
    )["status"] == "PASS"
    assert audit_klines(
        premium,
        start_ms=start,
        end_ms=end,
        allow_nonpositive_prices=True,
        futures_activity=False,
    )["status"] == "PASS"
    assert audit_klines(
        index,
        start_ms=start,
        end_ms=end,
        allow_nonpositive_prices=False,
        futures_activity=False,
    )["status"] == "PASS"

    cross = audit_cross_source(premium, futures, index)
    assert cross["status"] == "PASS"
    assert cross["intersection_coverage"] == pytest.approx(1.0)


def test_kline_audit_rejects_bad_close_time_and_missing_activity(monkeypatch) -> None:
    start = parse_utc(AUDIT_START)
    slots = 4
    end = start + slots * audit.INTERVAL_MS
    monkeypatch.setattr(audit, "EXPECTED_15M_SLOTS", slots)
    rows = [_kline(index, start_ms=start) for index in range(slots)]
    rows[1] = replace(rows[1], close_time_ms=rows[1].close_time_ms - 1, trade_count=None)

    result = audit_klines(
        rows,
        start_ms=start,
        end_ms=end,
        allow_nonpositive_prices=False,
        futures_activity=True,
    )

    assert result["status"] == "FAIL"
    assert result["checks"]["close_time"] is False
    assert result["checks"]["futures_activity_fields"] is False
