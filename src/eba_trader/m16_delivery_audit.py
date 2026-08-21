from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import math
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .derivatives_archive_seed import _download_verified_archive, parse_kline_archive
from .derivatives_audit import DerivativeKline
from .m16_delivery_policy import (
    AUDIT_WINDOW_DAYS,
    EXPECTED_SLOTS,
    FAMILIES,
    INTERVAL,
    INTERVAL_MS,
    MAX_FINAL_EDGE_MINUTES,
    MAX_MISSING_RUN,
    MIN_COVERAGE,
    DeliveryContract,
    delivery_contracts,
    verify_m16_freeze,
)
from .provenance import collect_source_provenance

ARCHIVE_ROOT = "https://data.binance.vision/data/futures"
MINUTE_MS = 60_000
OOS_2025_START_MS = int(datetime(2025, 1, 1, tzinfo=UTC).timestamp() * 1000)


@dataclass(frozen=True, slots=True)
class ArchiveFileAudit:
    period: str
    url: str
    status: str
    sha256: str | None
    zip_bytes: int
    parsed_rows: int


@dataclass(frozen=True, slots=True)
class ContractAudit:
    family: str
    symbol: str
    suffix: str
    year: int
    discovery: bool
    delivery_time_ms: int
    window_start_ms: int
    window_end_ms: int
    expected_slots: int
    accepted_rows: int
    coverage: float
    missing_slots: int
    max_missing_run: int
    first_open_time_ms: int | None
    last_open_time_ms: int | None
    final_edge_minutes: float | None
    duplicate_count: int
    conflict_count: int
    alignment_violations: int
    close_time_violations: int
    numeric_violations: int
    archive_files: tuple[ArchiveFileAudit, ...]
    normalized_sha256: str | None
    checks: dict[str, bool]
    status: str


def _window_months(start_ms: int, end_ms: int) -> tuple[tuple[int, int], ...]:
    if start_ms >= end_ms:
        raise ValueError("M16 audit window must be increasing")
    start_dt = datetime.fromtimestamp(start_ms / 1000, tz=UTC)
    last_dt = datetime.fromtimestamp((end_ms - 1) / 1000, tz=UTC)
    year, month = start_dt.year, start_dt.month
    result: list[tuple[int, int]] = []
    while (year, month) <= (last_dt.year, last_dt.month):
        result.append((year, month))
        if month == 12:
            year += 1
            month = 1
        else:
            month += 1
    return tuple(result)


def archive_url(family: str, symbol: str, year: int, month: int) -> str:
    if family not in FAMILIES:
        raise ValueError(f"Unsupported M16 family: {family}")
    if year >= 2025:
        raise RuntimeError("M16 must not construct or request 2025 archives")
    stamp = f"{year:04d}-{month:02d}"
    filename = f"{symbol}-{INTERVAL}-{stamp}.zip"
    return f"{ARCHIVE_ROOT}/{family}/monthly/klines/{symbol}/{INTERVAL}/{filename}"


def _row_signature(row: DerivativeKline) -> tuple[object, ...]:
    return (
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
    )


def _numeric_valid(row: DerivativeKline) -> bool:
    prices = (row.open, row.high, row.low, row.close)
    if not all(math.isfinite(value) and value > 0 for value in prices):
        return False
    if row.high < max(row.open, row.close) or row.low > min(row.open, row.close):
        return False
    optional_nonnegative = (
        row.volume,
        row.quote_volume,
        float(row.trade_count) if row.trade_count is not None else None,
        row.taker_buy_base_volume,
        row.taker_buy_quote_volume,
    )
    return all(
        value is None or (math.isfinite(value) and value >= 0)
        for value in optional_nonnegative
    )


def _max_missing_run(expected: tuple[int, ...], available: set[int]) -> int:
    maximum = 0
    current = 0
    for timestamp in expected:
        if timestamp in available:
            current = 0
        else:
            current += 1
            maximum = max(maximum, current)
    return maximum


def _normalized_sha256(rows: tuple[DerivativeKline, ...]) -> str:
    output = io.StringIO(newline="")
    writer = csv.writer(output, lineterminator="\n")
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
        writer.writerow(_row_signature(row))
    return hashlib.sha256(output.getvalue().encode("utf-8")).hexdigest()


def audit_contract_rows(
    *,
    family: str,
    contract: DeliveryContract,
    rows: list[DerivativeKline],
    archive_files: tuple[ArchiveFileAudit, ...],
) -> ContractAudit:
    delivery = contract.delivery_time_ms
    if delivery >= OOS_2025_START_MS:
        raise RuntimeError("M16 contract audit would touch 2025 OOS")
    start = delivery - AUDIT_WINDOW_DAYS * 24 * 60 * 60 * 1000
    end = delivery
    expected = tuple(start + index * INTERVAL_MS for index in range(EXPECTED_SLOTS))
    expected_set = set(expected)

    selected = [row for row in rows if start <= row.open_time_ms < end]
    by_time: dict[int, DerivativeKline] = {}
    duplicates = 0
    conflicts = 0
    for row in selected:
        previous = by_time.get(row.open_time_ms)
        if previous is None:
            by_time[row.open_time_ms] = row
            continue
        duplicates += 1
        if _row_signature(previous) != _row_signature(row):
            conflicts += 1

    normalized = tuple(by_time[timestamp] for timestamp in sorted(by_time))
    available = set(by_time).intersection(expected_set)
    accepted = tuple(row for row in normalized if row.open_time_ms in expected_set)
    alignment_violations = sum(row.open_time_ms % INTERVAL_MS != 0 for row in normalized)
    close_time_violations = sum(
        row.close_time_ms != row.open_time_ms + INTERVAL_MS - 1 for row in accepted
    )
    numeric_violations = sum(not _numeric_valid(row) for row in accepted)
    missing = EXPECTED_SLOTS - len(available)
    coverage = len(available) / EXPECTED_SLOTS
    max_gap = _max_missing_run(expected, available)
    first_time = accepted[0].open_time_ms if accepted else None
    last_time = accepted[-1].open_time_ms if accepted else None
    final_edge = (delivery - last_time) / MINUTE_MS if last_time is not None else None
    verified_archives = [item for item in archive_files if item.status == "VERIFIED"]

    checks = {
        "archive_exists": bool(verified_archives),
        "archives_checksum_verified": all(
            item.status in {"VERIFIED", "MISSING"} and (
                item.status == "MISSING" or item.sha256 is not None
            )
            for item in archive_files
        ),
        "unique_after_normalization": conflicts == 0,
        "aligned": alignment_violations == 0,
        "close_time": close_time_violations == 0,
        "numeric": numeric_violations == 0,
        "coverage": coverage >= MIN_COVERAGE,
        "max_gap": max_gap <= MAX_MISSING_RUN,
        "final_edge": final_edge is not None and final_edge <= MAX_FINAL_EDGE_MINUTES,
        "no_conflicts": conflicts == 0,
    }
    status = "PASS" if all(checks.values()) else "FAIL"
    symbol = contract.symbol(family)
    return ContractAudit(
        family=family,
        symbol=symbol,
        suffix=contract.suffix,
        year=contract.year,
        discovery=contract.discovery,
        delivery_time_ms=delivery,
        window_start_ms=start,
        window_end_ms=end,
        expected_slots=EXPECTED_SLOTS,
        accepted_rows=len(accepted),
        coverage=coverage,
        missing_slots=missing,
        max_missing_run=max_gap,
        first_open_time_ms=first_time,
        last_open_time_ms=last_time,
        final_edge_minutes=final_edge,
        duplicate_count=duplicates,
        conflict_count=conflicts,
        alignment_violations=alignment_violations,
        close_time_violations=close_time_violations,
        numeric_violations=numeric_violations,
        archive_files=archive_files,
        normalized_sha256=_normalized_sha256(accepted) if accepted else None,
        checks=checks,
        status=status,
    )


def _download_contract(family: str, contract: DeliveryContract) -> ContractAudit:
    if contract.year >= 2025:
        raise RuntimeError("M16 must not request 2025 delivery data")
    start = contract.delivery_time_ms - AUDIT_WINDOW_DAYS * 24 * 60 * 60 * 1000
    months = _window_months(start, contract.delivery_time_ms)
    symbol = contract.symbol(family)
    rows: list[DerivativeKline] = []
    files: list[ArchiveFileAudit] = []
    for year, month in months:
        url = archive_url(family, symbol, year, month)
        downloaded = _download_verified_archive(url)
        if downloaded is None:
            files.append(
                ArchiveFileAudit(
                    period=f"{year:04d}-{month:02d}",
                    url=url,
                    status="MISSING",
                    sha256=None,
                    zip_bytes=0,
                    parsed_rows=0,
                )
            )
            continue
        payload, digest = downloaded
        parsed = parse_kline_archive(payload, futures_activity=True)
        rows.extend(parsed)
        files.append(
            ArchiveFileAudit(
                period=f"{year:04d}-{month:02d}",
                url=url,
                status="VERIFIED",
                sha256=digest,
                zip_bytes=len(payload),
                parsed_rows=len(parsed),
            )
        )
    return audit_contract_rows(
        family=family,
        contract=contract,
        rows=rows,
        archive_files=tuple(files),
    )


def run_m16_delivery_audit(
    *,
    report_path: str | Path = "artifacts/m16_delivery_futures_data_audit.json",
) -> dict[str, Any]:
    output = Path(report_path)
    if output.exists():
        raise RuntimeError("M16 evidence already exists; preserve first complete audit")
    freeze = verify_m16_freeze()
    provenance = collect_source_provenance(require_clean=True)
    contracts = delivery_contracts()
    results: dict[str, list[ContractAudit]] = {}
    family_decisions: dict[str, str] = {}

    for family in FAMILIES:
        audits = [_download_contract(family, contract) for contract in contracts]
        results[family] = audits
        discovery_pass = sum(item.status == "PASS" and item.discovery for item in audits)
        challenge_pass = sum(item.status == "PASS" and not item.discovery for item in audits)
        family_decisions[family] = (
            "DELIVERY_DATA_ELIGIBLE"
            if discovery_pass == 12 and challenge_pass == 4
            else "DELIVERY_DATA_NOT_ELIGIBLE"
        )

    eligible = [
        family
        for family, decision in family_decisions.items()
        if decision == "DELIVERY_DATA_ELIGIBLE"
    ]
    decision = "M16_DELIVERY_DATA_AUDIT_PASS" if eligible else "M16_DELIVERY_DATA_AUDIT_FAIL"
    report: dict[str, Any] = {
        "phase": "m16_delivery_futures_first_complete_frozen_data_audit",
        "decision": decision,
        "policy_freeze": freeze,
        "source_provenance": provenance,
        "family_decisions": family_decisions,
        "eligible_families": eligible,
        "families": {
            family: {
                "discovery_contracts_passing": sum(
                    item.status == "PASS" and item.discovery for item in audits
                ),
                "challenge_contracts_passing": sum(
                    item.status == "PASS" and not item.discovery for item in audits
                ),
                "contracts": [asdict(item) for item in audits],
            }
            for family, audits in results.items()
        },
        "profitability_computation": "FORBIDDEN_NOT_RUN",
        "risk_sizing": "BLOCKED_DATA_AUDIT_ONLY",
        "live_execution": "BLOCKED_DATA_AUDIT_ONLY",
        "oos_2025": "LOCKED_NOT_ACCESSED",
        "parameter_changes_after_result": "FORBIDDEN",
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(report, indent=2, sort_keys=True, allow_nan=False),
        encoding="utf-8",
    )
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description="Run frozen M16 delivery futures data audit")
    parser.add_argument("--report", default="artifacts/m16_delivery_futures_data_audit.json")
    args = parser.parse_args()
    report = run_m16_delivery_audit(report_path=args.report)
    print("M16 decision:", report["decision"])
    print("family_decisions:", report["family_decisions"])
    print("eligible_families:", report["eligible_families"])
    print("2025 OOS remains", report["oos_2025"])


if __name__ == "__main__":
    main()
