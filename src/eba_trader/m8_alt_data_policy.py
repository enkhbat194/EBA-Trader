from __future__ import annotations

import hashlib
import json
from pathlib import Path

M8_AUDIT_NAME = "m8_alt_derivatives_data_audit_v1"
M8_AUDIT_PROTOCOL = Path("docs/M8_ALT_DERIVATIVES_DATA_AUDIT_PROTOCOL.md")
M8_AUDIT_FREEZE = Path("docs/M8_ALT_DERIVATIVES_DATA_AUDIT_FREEZE.json")
M8_AUDIT_PROTOCOL_SHA256 = "18fda0ce27e81e64a496be4fd439b0b5c2479a2534028ca8ec0dfc676fd671c6"

AUDIT_START = "2021-01-01T00:00:00Z"
AUDIT_END_EXCLUSIVE = "2025-01-01T00:00:00Z"
BOOK_DEPTH_START = "2023-01-01T00:00:00Z"
FROZEN_OOS_START = "2025-01-01T00:00:00Z"
FROZEN_OOS_END_EXCLUSIVE = "2026-01-01T00:00:00Z"

SYMBOL = "BTCUSDT"
BINANCE_VISION_BASE = "https://data.binance.vision/data/futures/um/daily"
BYBIT_BASE = "https://api.bybit.com"

FIVE_MIN_MS = 5 * 60 * 1000
HOUR_MS = 60 * 60 * 1000
DAY_MS = 24 * HOUR_MS

BINANCE_METRICS_MIN_COVERAGE = 0.995
BINANCE_METRICS_MAX_MISSING_SLOTS = 288
BYBIT_KLINE_MIN_COVERAGE = 0.999
BYBIT_KLINE_MAX_MISSING_HOURS = 6
BYBIT_POSITIONING_MIN_COVERAGE = 0.995
BYBIT_POSITIONING_MAX_MISSING_HOURS = 24
CROSS_EXCHANGE_MIN_HOURLY_ALIGNMENT = 0.99
BOOK_DEPTH_MIN_DAILY_FILE_COVERAGE = 0.99
LIQUIDATION_MIN_DAILY_FILE_COVERAGE = 0.99


def canonical_text_sha256(path: str | Path) -> str:
    text = Path(path).read_text(encoding="utf-8")
    canonical = text.replace("\r\n", "\n").replace("\r", "\n")
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def verify_m8_audit_freeze(root: str | Path = ".") -> dict[str, object]:
    base = Path(root)
    protocol = base / M8_AUDIT_PROTOCOL
    manifest_path = base / M8_AUDIT_FREEZE
    if not protocol.is_file() or not manifest_path.is_file():
        raise FileNotFoundError("M8 audit protocol or freeze manifest is missing")

    actual_hash = canonical_text_sha256(protocol)
    if actual_hash != M8_AUDIT_PROTOCOL_SHA256:
        raise RuntimeError("M8 data-audit protocol changed after freeze")

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("cycle") != M8_AUDIT_NAME:
        raise RuntimeError("M8 audit cycle mismatch")
    if manifest.get("status") != "FROZEN_PRE_AUDIT":
        raise RuntimeError("M8 audit freeze status mismatch")
    if manifest.get("protocol_sha256") != actual_hash:
        raise RuntimeError("M8 audit protocol hash mismatch")
    if manifest.get("audit_start") != AUDIT_START:
        raise RuntimeError("M8 audit start mismatch")
    if manifest.get("audit_end_exclusive") != AUDIT_END_EXCLUSIVE:
        raise RuntimeError("M8 audit end mismatch")
    if manifest.get("oos_2025") != "LOCKED_NOT_ACCESSED":
        raise RuntimeError("M8 audit does not preserve the 2025 OOS lock")
    if manifest.get("forward_returns") != "forbidden":
        raise RuntimeError("M8 audit unexpectedly permits forward-return research")
    if manifest.get("strategy_generation") != "forbidden":
        raise RuntimeError("M8 audit unexpectedly permits strategy generation")
    if manifest.get("ai_module") != "excluded":
        raise RuntimeError("M8 audit unexpectedly includes AI")
    return manifest
