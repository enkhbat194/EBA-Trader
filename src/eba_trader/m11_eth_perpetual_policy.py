from __future__ import annotations

import hashlib
import json
from pathlib import Path

M11_POLICY_NAME = "m11_eth_perpetual_data_audit_v1"
M11_PROTOCOL = Path("docs/M11_ETH_PERPETUAL_DATA_AUDIT_PROTOCOL.md")
M11_FREEZE = Path("docs/M11_ETH_PERPETUAL_DATA_AUDIT_FREEZE.json")
M11_PROTOCOL_SHA256 = "ee432e01ec11cb52f8cafbaa0e93c29278b740403ab9ca5f987525f037adb6ac"

AUDIT_START = "2021-01-01T00:00:00Z"
AUDIT_END_EXCLUSIVE = "2025-01-01T00:00:00Z"
SYMBOL = "ETHUSDT"
INTERVAL = "15m"
STEP_MS = 15 * 60 * 1000
EXPECTED_MONTHLY_ARCHIVES = 48
EXPECTED_SLOTS = 140_256
MIN_COVERAGE = 0.9995
MAX_MISSING_RUN_BARS = 12
ARCHIVE_BASE = "https://data.binance.vision/data/futures/um/monthly/klines"


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


def verify_m11_freeze(root: str | Path = ".") -> dict[str, object]:
    base = Path(root)
    protocol = base / M11_PROTOCOL
    manifest_path = base / M11_FREEZE
    if not protocol.is_file() or not manifest_path.is_file():
        raise FileNotFoundError("M11 protocol or freeze manifest is missing")

    actual_hash = canonical_text_sha256(protocol)
    if actual_hash != M11_PROTOCOL_SHA256:
        raise RuntimeError("M11 audit protocol changed after freeze")

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    checks = {
        "cycle": manifest.get("cycle") == M11_POLICY_NAME,
        "status": manifest.get("status") == "FROZEN_PRE_AUDIT",
        "protocol": manifest.get("protocol_sha256") == actual_hash,
        "start": manifest.get("audit_start") == AUDIT_START,
        "end": manifest.get("audit_end_exclusive") == AUDIT_END_EXCLUSIVE,
        "symbol": manifest.get("symbol") == SYMBOL,
        "instrument": manifest.get("instrument") == "ETHUSDT_USDM_PERPETUAL",
        "interval": manifest.get("interval") == INTERVAL,
        "archives": manifest.get("expected_monthly_archives") == EXPECTED_MONTHLY_ARCHIVES,
        "slots": manifest.get("expected_slots") == EXPECTED_SLOTS,
        "coverage": manifest.get("min_coverage") == MIN_COVERAGE,
        "gap": manifest.get("max_missing_run_bars") == MAX_MISSING_RUN_BARS,
        "source": manifest.get("source")
        == "binance_vision_usdm_monthly_perpetual_klines_with_checksum",
        "forward": manifest.get("forward_returns") == "forbidden",
        "strategy": manifest.get("strategy_generation") == "forbidden",
        "risk": manifest.get("risk_sizing") == "forbidden",
        "ai": manifest.get("ai_module") == "excluded",
        "live": manifest.get("live_execution") == "forbidden",
        "oos": manifest.get("oos_2025") == "LOCKED_NOT_ACCESSED",
    }
    failed = [name for name, passed in checks.items() if not passed]
    if failed:
        raise RuntimeError(f"M11 freeze manifest mismatch: {', '.join(failed)}")
    return manifest
