from __future__ import annotations

from datetime import UTC, datetime

import pytest

from eba_trader.derivatives_audit import DerivativeKline
from eba_trader.m16_delivery_audit import (
    ArchiveFileAudit,
    audit_contract_rows,
    archive_url,
)
from eba_trader.m16_delivery_policy import (
    EXPECTED_SLOTS,
    INTERVAL_MS,
    delivery_contracts,
    verify_m16_freeze,
)


def _row(open_time: int, price: float = 100.0) -> DerivativeKline:
    return DerivativeKline(
        open_time_ms=open_time,
        open=price,
        high=price + 1.0,
        low=price - 1.0,
        close=price + 0.25,
        close_time_ms=open_time + INTERVAL_MS - 1,
        volume=10.0,
        quote_volume=1000.0,
        trade_count=10,
        taker_buy_base_volume=5.0,
        taker_buy_quote_volume=500.0,
    )


def _verified_file() -> ArchiveFileAudit:
    return ArchiveFileAudit(
        period="2021-03",
        url="https://data.binance.vision/example.zip",
        status="VERIFIED",
        sha256="a" * 64,
        zip_bytes=123,
        parsed_rows=3000,
    )


def test_m16_freeze_manifest_and_calendar_verify() -> None:
    manifest = verify_m16_freeze()
    contracts = delivery_contracts()
    assert manifest["status"] == "FROZEN_PREDECLARED_DATA_AUDIT"
    assert len(contracts) == 16
    assert sum(item.discovery for item in contracts) == 12
    assert max(item.year for item in contracts) == 2024
    assert manifest["oos_2025"] == "LOCKED_NOT_ACCESSED"


def test_delivery_archive_url_is_family_specific_and_blocks_2025() -> None:
    assert "/futures/um/monthly/klines/BTCUSDT_210326/15m/" in archive_url(
        "um", "BTCUSDT_210326", 2021, 3
    )
    assert "/futures/cm/monthly/klines/BTCUSD_210326/15m/" in archive_url(
        "cm", "BTCUSD_210326", 2021, 3
    )
    with pytest.raises(RuntimeError, match="2025"):
        archive_url("um", "BTCUSDT_250328", 2025, 3)


def test_full_30_day_contract_window_passes_integrity() -> None:
    contract = delivery_contracts()[0]
    start = contract.delivery_time_ms - 30 * 24 * 60 * 60 * 1000
    rows = [_row(start + index * INTERVAL_MS) for index in range(EXPECTED_SLOTS)]
    result = audit_contract_rows(
        family="um",
        contract=contract,
        rows=rows,
        archive_files=(_verified_file(),),
    )
    assert result.status == "PASS"
    assert result.accepted_rows == EXPECTED_SLOTS
    assert result.coverage == 1.0
    assert result.max_missing_run == 0
    assert result.final_edge_minutes == 15.0
    assert result.conflict_count == 0
    assert result.normalized_sha256 is not None


def test_five_bar_gap_fails_frozen_gap_and_coverage_gates() -> None:
    contract = delivery_contracts()[0]
    start = contract.delivery_time_ms - 30 * 24 * 60 * 60 * 1000
    missing = set(range(100, 105))
    rows = [
        _row(start + index * INTERVAL_MS)
        for index in range(EXPECTED_SLOTS)
        if index not in missing
    ]
    result = audit_contract_rows(
        family="cm",
        contract=contract,
        rows=rows,
        archive_files=(_verified_file(),),
    )
    assert result.status == "FAIL"
    assert result.max_missing_run == 5
    assert result.checks["max_gap"] is False
    assert result.checks["coverage"] is False


def test_conflicting_duplicate_is_not_silently_deduplicated() -> None:
    contract = delivery_contracts()[0]
    start = contract.delivery_time_ms - 30 * 24 * 60 * 60 * 1000
    rows = [_row(start + index * INTERVAL_MS) for index in range(EXPECTED_SLOTS)]
    rows.append(_row(start, price=110.0))
    result = audit_contract_rows(
        family="um",
        contract=contract,
        rows=rows,
        archive_files=(_verified_file(),),
    )
    assert result.status == "FAIL"
    assert result.duplicate_count == 1
    assert result.conflict_count == 1
    assert result.checks["no_conflicts"] is False


def test_contract_delivery_time_is_0800_utc() -> None:
    contract = delivery_contracts()[0]
    dt = datetime.fromtimestamp(contract.delivery_time_ms / 1000, tz=UTC)
    assert (dt.year, dt.month, dt.day, dt.hour, dt.minute) == (2021, 3, 26, 8, 0)
