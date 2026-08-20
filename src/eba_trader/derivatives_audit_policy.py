from __future__ import annotations

import hashlib
import json
from pathlib import Path

M6_AUDIT_NAME = "m6_derivatives_data_audit_v1"
M6_AUDIT_PROTOCOL = Path("docs/M6_DERIVATIVES_DATA_AUDIT_PROTOCOL.md")
M6_AUDIT_FREEZE = Path("docs/M6_DERIVATIVES_DATA_AUDIT_FREEZE.json")
M6_AUDIT_PROTOCOL_SHA256 = "e5ef3f512c815138d2d25e72c25dd9f946a51039190ec6d0aacc05a8f15bb785"

AUDIT_START = "2021-01-01T00:00:00Z"
AUDIT_END_EXCLUSIVE = "2025-01-01T00:00:00Z"
FROZEN_OOS_START = "2025-01-01T00:00:00Z"
FROZEN_OOS_END_EXCLUSIVE = "2026-01-01T00:00:00Z"

SYMBOL = "BTCUSDT"
INTERVAL = "15m"
INTERVAL_MS = 15 * 60 * 1000
EXPECTED_15M_SLOTS = 140_256

MIN_FUNDING_RECORDS = 4_000
MAX_FUNDING_EDGE_HOURS = 8
MAX_FUNDING_ABS_RATE = 0.05
MAX_FUNDING_MEDIAN_CADENCE_HOURS = 8
MAX_FUNDING_GAP_HOURS = 24

MIN_KLINE_COVERAGE = 0.999
MAX_KLINE_MISSING_RUN = 48
MIN_CROSS_SOURCE_COVERAGE = 0.998

FAPI_BASE_URL = "https://fapi.binance.com"
FUNDING_ENDPOINT = "/fapi/v1/fundingRate"
PREMIUM_ENDPOINT = "/fapi/v1/premiumIndexKlines"
FUTURES_KLINE_ENDPOINT = "/fapi/v1/klines"
INDEX_KLINE_ENDPOINT = "/fapi/v1/indexPriceKlines"

RETENTION_BLOCKED = {
    "open_interest_statistics": {
        "endpoint": "/futures/data/openInterestHist",
        "documented_retention": "latest_1_month",
    },
    "basis": {
        "endpoint": "/futures/data/basis",
        "documented_retention": "latest_30_days",
    },
}


def canonical_text_sha256(path: str | Path) -> str:
    text = Path(path).read_text(encoding="utf-8")
    canonical = text.replace("\r\n", "\n").replace("\r", "\n")
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def sha256_file(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def verify_m6_audit_freeze(root: str | Path = ".") -> dict[str, object]:
    base = Path(root)
    protocol = base / M6_AUDIT_PROTOCOL
    manifest_path = base / M6_AUDIT_FREEZE
    if not protocol.is_file() or not manifest_path.is_file():
        raise FileNotFoundError("M6 audit protocol or freeze manifest is missing")

    actual_hash = canonical_text_sha256(protocol)
    if actual_hash != M6_AUDIT_PROTOCOL_SHA256:
        raise RuntimeError("M6 data-audit protocol changed after freeze")

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("cycle") != M6_AUDIT_NAME:
        raise RuntimeError("M6 audit cycle mismatch")
    if manifest.get("status") != "FROZEN_PRE_AUDIT":
        raise RuntimeError("M6 audit freeze status mismatch")
    if manifest.get("protocol_sha256") != actual_hash:
        raise RuntimeError("M6 audit protocol hash mismatch")
    if manifest.get("audit_start") != AUDIT_START:
        raise RuntimeError("M6 audit start mismatch")
    if manifest.get("audit_end_exclusive") != AUDIT_END_EXCLUSIVE:
        raise RuntimeError("M6 audit end mismatch")
    if manifest.get("oos_2025") != "LOCKED_NOT_ACCESSED":
        raise RuntimeError("M6 audit does not preserve the 2025 OOS lock")
    if manifest.get("strategy_generation") != "forbidden":
        raise RuntimeError("M6 audit unexpectedly permits strategy generation")
    if manifest.get("ai_module") != "excluded":
        raise RuntimeError("M6 audit unexpectedly includes AI")
    return manifest
