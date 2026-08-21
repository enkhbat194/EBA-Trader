from __future__ import annotations

import hashlib
import json
from pathlib import Path

M15_POLICY_NAME = "m15_market_neutral_basis_convergence_v1"
M15_PROTOCOL = Path("docs/M15_MARKET_NEUTRAL_BASIS_CONVERGENCE_PROTOCOL.md")
M15_FREEZE = Path("docs/M15_MARKET_NEUTRAL_BASIS_CONVERGENCE_FREEZE.json")
M15_PROTOCOL_SHA256 = "1837e2a7e25e2b531ca0340f783b27bfa89e9752ff9cf7b296b08262b7940549"

SPOT_RESEARCH_SHA256 = "253c6ae35856e58e35df17eaa71caeea5caaa3681c38dd7214a2872afccd8d63"
SPOT_CHALLENGE_SHA256 = "3a96b6b668cfacb0fefabb8665675d4ca589cc712b0681fb57e7a13356eda0f2"
FUTURES_SHA256 = "3c97c9b59ded32595f129a480a23e920823c0edbbf2e4f32c5d66e5020e35947"
FUNDING_SHA256 = "73b9decde0d54a0609d55ccfd49131a6e825416b595d728457bb01a968b55fd6"

ENTRY_BASIS_THRESHOLDS = (0.0075, 0.0125, 0.0200)
EXIT_BASIS_THRESHOLD = 0.0010
MAX_HOLD_BARS = (96, 288, 672)
CONFIG_COUNT = 9
CAPITAL_USD = 2.0
LEG_NOTIONAL_USD = 1.0
BASE_COST_BPS_PER_SIDE = 15.0
SEVERE_COST_BPS_PER_SIDE = 35.0
FDR_Q_THRESHOLD = 0.10
DISCOVERY_END_EXCLUSIVE = "2024-01-01T00:00:00Z"
CHALLENGE_START = "2024-01-01T00:00:00Z"
CHALLENGE_END_EXCLUSIVE = "2025-01-01T00:00:00Z"

MIN_DISCOVERY_TRADES = 20
MIN_DISCOVERY_DAYS = 15
MIN_DISCOVERY_TRADES_PER_YEAR = 3
MIN_DISCOVERY_PF = 1.20
MIN_CHALLENGE_TRADES = 5
MIN_CHALLENGE_PF = 1.20


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


def verify_m15_freeze(root: str | Path = ".") -> dict[str, object]:
    base = Path(root)
    protocol = base / M15_PROTOCOL
    manifest_path = base / M15_FREEZE
    if not protocol.is_file() or not manifest_path.is_file():
        raise FileNotFoundError("M15 protocol or freeze manifest missing")

    actual_hash = canonical_text_sha256(protocol)
    if actual_hash != M15_PROTOCOL_SHA256:
        raise RuntimeError("M15 protocol changed after freeze")

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    expected_hashes = {
        "btc_spot_research_2021_2023": SPOT_RESEARCH_SHA256,
        "btc_spot_challenge_2024": SPOT_CHALLENGE_SHA256,
        "btc_usdm_15m_2021_2024": FUTURES_SHA256,
        "btc_funding_2021_2024": FUNDING_SHA256,
    }
    checks = {
        "cycle": manifest.get("cycle") == M15_POLICY_NAME,
        "status": manifest.get("status") == "FROZEN_PREDECLARED_NOT_RUN",
        "protocol": manifest.get("protocol_sha256") == actual_hash,
        "hashes": manifest.get("input_sha256") == expected_hashes,
        "entry_basis": manifest.get("entry_basis_thresholds")
        == list(ENTRY_BASIS_THRESHOLDS),
        "exit_basis": manifest.get("exit_basis_threshold") == EXIT_BASIS_THRESHOLD,
        "holds": manifest.get("max_hold_bars") == list(MAX_HOLD_BARS),
        "configs": manifest.get("configuration_count") == CONFIG_COUNT,
        "capital": manifest.get("capital_usd") == CAPITAL_USD,
        "spot_notional": manifest.get("spot_entry_notional_usd") == LEG_NOTIONAL_USD,
        "perp_notional": manifest.get("perp_entry_notional_usd") == LEG_NOTIONAL_USD,
        "base_cost": manifest.get("base_cost_bps_per_side_each_leg")
        == BASE_COST_BPS_PER_SIDE,
        "severe_cost": manifest.get("severe_cost_bps_per_side_each_leg")
        == SEVERE_COST_BPS_PER_SIDE,
        "fdr": manifest.get("fdr_q_threshold") == FDR_Q_THRESHOLD,
        "oos": manifest.get("oos_2025") == "LOCKED_NOT_ACCESSED",
        "leverage": manifest.get("leverage") == "forbidden",
        "naked_short": manifest.get("naked_short") == "forbidden",
        "overlap": manifest.get("overlapping_positions") == "forbidden",
        "retune": manifest.get("parameter_changes_after_first_run") == "forbidden",
        "risk": manifest.get("risk_sizing") == "blocked",
        "live": manifest.get("live_execution") == "blocked",
    }
    failed = [name for name, passed in checks.items() if not passed]
    if failed:
        raise RuntimeError(f"M15 freeze manifest mismatch: {', '.join(failed)}")
    if len(ENTRY_BASIS_THRESHOLDS) * len(MAX_HOLD_BARS) != CONFIG_COUNT:
        raise RuntimeError("M15 frozen config count inconsistent")
    return manifest
