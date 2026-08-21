from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

M16_POLICY_NAME = "m16_delivery_futures_data_audit_v1"
M16_PROTOCOL = Path("docs/M16_DELIVERY_FUTURES_DATA_AUDIT_PROTOCOL.md")
M16_FREEZE = Path("docs/M16_DELIVERY_FUTURES_DATA_AUDIT_FREEZE.json")
M16_PROTOCOL_SHA256 = "c8f399b6072b02381b44cfefb5a15b472beabbea70e3ad19a6f0d8a7309815d2"

INTERVAL = "15m"
INTERVAL_MS = 15 * 60 * 1000
AUDIT_WINDOW_DAYS = 30
EXPECTED_SLOTS = 2880
MIN_COVERAGE = 0.999
MAX_MISSING_RUN = 4
MAX_FINAL_EDGE_MINUTES = 60
DELIVERY_HOUR_UTC = 8
FAMILIES = ("um", "cm")
CONTRACT_SUFFIXES = (
    "210326", "210625", "210924", "211231",
    "220325", "220624", "220930", "221230",
    "230331", "230630", "230929", "231229",
    "240329", "240628", "240927", "241227",
)


@dataclass(frozen=True, slots=True)
class DeliveryContract:
    suffix: str
    delivery_time_ms: int
    year: int
    discovery: bool

    def symbol(self, family: str) -> str:
        if family == "um":
            return f"BTCUSDT_{self.suffix}"
        if family == "cm":
            return f"BTCUSD_{self.suffix}"
        raise ValueError(f"Unsupported M16 family: {family}")


def canonical_text_sha256(path: str | Path) -> str:
    text = Path(path).read_text(encoding="utf-8")
    canonical = text.replace("\r\n", "\n").replace("\r", "\n")
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def delivery_contracts() -> tuple[DeliveryContract, ...]:
    result: list[DeliveryContract] = []
    for suffix in CONTRACT_SUFFIXES:
        year = 2000 + int(suffix[:2])
        month = int(suffix[2:4])
        day = int(suffix[4:6])
        dt = datetime(year, month, day, DELIVERY_HOUR_UTC, tzinfo=UTC)
        result.append(
            DeliveryContract(
                suffix=suffix,
                delivery_time_ms=int(dt.timestamp() * 1000),
                year=year,
                discovery=year <= 2023,
            )
        )
    return tuple(result)


def verify_m16_freeze(root: str | Path = ".") -> dict[str, object]:
    base = Path(root)
    protocol = base / M16_PROTOCOL
    manifest_path = base / M16_FREEZE
    if not protocol.is_file() or not manifest_path.is_file():
        raise FileNotFoundError("M16 protocol or freeze manifest missing")
    actual_hash = canonical_text_sha256(protocol)
    if actual_hash != M16_PROTOCOL_SHA256:
        raise RuntimeError("M16 protocol changed after freeze")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    checks = {
        "cycle": manifest.get("cycle") == M16_POLICY_NAME,
        "status": manifest.get("status") == "FROZEN_PREDECLARED_DATA_AUDIT",
        "protocol": manifest.get("protocol_sha256") == actual_hash,
        "families": manifest.get("candidate_families") == list(FAMILIES),
        "suffixes": manifest.get("contract_suffixes") == list(CONTRACT_SUFFIXES),
        "interval": manifest.get("interval") == INTERVAL,
        "window": manifest.get("audit_window_days") == AUDIT_WINDOW_DAYS,
        "slots": manifest.get("expected_slots_per_contract") == EXPECTED_SLOTS,
        "coverage": manifest.get("coverage_minimum") == MIN_COVERAGE,
        "gap": manifest.get("max_missing_run_bars") == MAX_MISSING_RUN,
        "edge": manifest.get("max_final_edge_minutes") == MAX_FINAL_EDGE_MINUTES,
        "delivery_hour": manifest.get("delivery_hour_utc") == DELIVERY_HOUR_UTC,
        "oos": manifest.get("oos_2025") == "LOCKED_NOT_ACCESSED",
        "profit": manifest.get("profitability_computation") == "forbidden",
    }
    failed = [name for name, passed in checks.items() if not passed]
    if failed:
        raise RuntimeError(f"M16 freeze manifest mismatch: {', '.join(failed)}")
    contracts = delivery_contracts()
    if len(contracts) != 16 or sum(item.discovery for item in contracts) != 12:
        raise RuntimeError("M16 frozen contract calendar is inconsistent")
    if max(item.year for item in contracts) >= 2025:
        raise RuntimeError("M16 frozen contract calendar touches 2025")
    return manifest
