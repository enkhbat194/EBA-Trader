from __future__ import annotations

from pathlib import Path

import pytest

from eba_trader.derivatives_audit import DerivativeKline
from eba_trader.history import parse_utc
from eba_trader.m11_eth_perpetual_audit import (
    MonthResult,
    assert_m11_window,
    deduplicate_klines,
    evaluate_gates,
    month_range,
    parse_kline_rows,
    write_normalized_csv,
)
from eba_trader.m11_eth_perpetual_policy import (
    AUDIT_END_EXCLUSIVE,
    AUDIT_START,
    EXPECTED_MONTHLY_ARCHIVES,
    STEP_MS,
    sha256_file,
    verify_m11_freeze,
)


def _raw_row(index: int = 0) -> list[str]:
    open_time = parse_utc(AUDIT_START) + index * STEP_MS
    return [
        str(open_time), "100.0", "102.0", "99.0", "101.0", "10.0",
        str(open_time + STEP_MS - 1), "1005.0", "25", "4.0", "402.0", "0",
    ]


def _kline(index: int = 0, *, close: float = 101.0) -> DerivativeKline:
    open_time = parse_utc(AUDIT_START) + index * STEP_MS
    return DerivativeKline(
        open_time_ms=open_time,
        open=100.0,
        high=max(102.0, close),
        low=99.0,
        close=close,
        close_time_ms=open_time + STEP_MS - 1,
        volume=10.0,
        quote_volume=1005.0,
        trade_count=25,
        taker_buy_base_volume=4.0,
        taker_buy_quote_volume=402.0,
    )


def _month(status: str = "PASS") -> MonthResult:
    return MonthResult(
        month="2021-01",
        url="fixture",
        status=status,
        checksum_sha256="a" * 64 if status == "PASS" else None,
        source_rows=1,
        invalid_rows=0,
        alignment_violations=0,
        close_time_violations=0,
        numeric_integrity_violations=0,
        rows=(_kline(),) if status == "PASS" else (),
    )


def test_m11_freeze_contract_verifies() -> None:
    manifest = verify_m11_freeze()
    assert manifest["status"] == "FROZEN_PRE_AUDIT"
    assert manifest["forward_returns"] == "forbidden"
    assert manifest["oos_2025"] == "LOCKED_NOT_ACCESSED"


def test_m11_month_range_is_exactly_48_months() -> None:
    months = month_range()
    assert len(months) == EXPECTED_MONTHLY_ARCHIVES == 48
    assert months[0] == (2021, 1)
    assert months[-1] == (2024, 12)


def test_m11_window_rejects_2025_access() -> None:
    start = parse_utc(AUDIT_START)
    end = parse_utc(AUDIT_END_EXCLUSIVE)
    assert_m11_window(start, end)
    with pytest.raises(RuntimeError):
        assert_m11_window(start, end + STEP_MS)


def test_m11_parser_accepts_valid_futures_activity_row() -> None:
    result = parse_kline_rows(
        [["open_time", "open"], _raw_row()],
        start_ms=parse_utc(AUDIT_START),
        end_ms=parse_utc(AUDIT_END_EXCLUSIVE),
    )
    assert result.source_rows == 1
    assert result.invalid_rows == 0
    assert result.alignment_violations == 0
    assert result.close_time_violations == 0
    assert result.numeric_integrity_violations == 0
    assert result.rows == (_kline(),)


def test_m11_parser_rejects_bad_close_time_without_repair() -> None:
    row = _raw_row()
    row[6] = str(int(row[6]) + 1)
    result = parse_kline_rows(
        [row],
        start_ms=parse_utc(AUDIT_START),
        end_ms=parse_utc(AUDIT_END_EXCLUSIVE),
    )
    assert result.rows == ()
    assert result.close_time_violations == 1


def test_m11_parser_rejects_taker_volume_above_total() -> None:
    row = _raw_row()
    row[9] = "11.0"
    result = parse_kline_rows(
        [row],
        start_ms=parse_utc(AUDIT_START),
        end_ms=parse_utc(AUDIT_END_EXCLUSIVE),
    )
    assert result.rows == ()
    assert result.numeric_integrity_violations == 1


def test_m11_dedup_collapses_exact_and_records_conflict() -> None:
    first = _kline()
    changed = _kline(close=101.5)
    normalized, exact, conflicts = deduplicate_klines((first, first, changed))
    assert len(normalized) == 1
    assert exact == 1
    assert conflicts == 1
    assert normalized[0] in {first, changed}


def test_m11_normalized_csv_is_deterministic(tmp_path: Path) -> None:
    rows = (_kline(0), _kline(1))
    first = write_normalized_csv(rows, tmp_path / "a.csv")
    second = write_normalized_csv(rows, tmp_path / "b.csv")
    assert first.read_bytes() == second.read_bytes()
    assert sha256_file(first) == sha256_file(second)


def test_m11_gates_fail_when_month_archives_are_missing() -> None:
    gates = evaluate_gates(months=(_month("MISSING"),), normalized=(), conflicting_timestamps=0)
    assert not gates["01_all_48_monthly_archives_exist"]
    assert not gates["02_all_48_checksums_verified"]
    assert not gates["11_coverage_at_least_99_95_percent"]


def test_m11_conflicting_timestamp_gate_is_fail_closed() -> None:
    gates = evaluate_gates(
        months=tuple(_month() for _ in range(EXPECTED_MONTHLY_ARCHIVES)),
        normalized=(_kline(),),
        conflicting_timestamps=1,
    )
    assert not gates["04_no_conflicting_duplicate_timestamps"]
