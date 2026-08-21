from __future__ import annotations

import hashlib
import json
from pathlib import Path

M17_POLICY_NAME = "m17_usdm_quarterly_cash_carry_v1"
M17_PROTOCOL = Path("docs/M17_USDM_QUARTERLY_CASH_CARRY_PROTOCOL.md")
M17_FREEZE = Path("docs/M17_USDM_QUARTERLY_CASH_CARRY_FREEZE.json")
M17_PROTOCOL_SHA256 = "4bfb9636b81764a0a40cbf3a09a3eacdbec7a7ea12bc252ee1a283bb36495604"

SPOT_RESEARCH_SHA256 = "253c6ae35856e58e35df17eaa71caeea5caaa3681c38dd7214a2872afccd8d63"
SPOT_CHALLENGE_SHA256 = "3a96b6b668cfacb0fefabb8665675d4ca589cc712b0681fb57e7a13356eda0f2"
M16_EVIDENCE_SHA256 = "b966f290ddc0652fbeeaa453bb33a86ffae15695c80fd321f9173e5c42e86745"

ENTRY_OFFSETS_DAYS = (28, 14, 7)
EXIT_MINUTES_BEFORE_DELIVERY = 15
CONFIG_COUNT = 3
SPOT_ENTRY_NOTIONAL_USD = 1.0
BASE_COST_BPS_PER_SIDE = 15.0
SEVERE_COST_BPS_PER_SIDE = 35.0
MIN_MARGIN_REMAINING_RATIO = 0.50
FDR_Q_THRESHOLD = 0.10
DISCOVERY_CONTRACT_COUNT = 12
CHALLENGE_CONTRACT_COUNT = 4
MIN_BASE_PF = 1.20
MIN_SEVERE_PF = 1.00
MIN_BASE_WIN_RATE = 0.75
MIN_CHALLENGE_SEVERE_WINS = 3

USDM_NORMALIZED_SHA256 = {
    "BTCUSDT_210326": "f79f15d08c6cd43ed2561b1b4265df3e36d9956fefbc57b087285226fb87d304",
    "BTCUSDT_210625": "2e632cb7e4ab2ce64d861559fca46769e5af369bc9cbe4b5f2ba85eb8118c615",
    "BTCUSDT_210924": "65e2fa23380b31dedf3cc4f531903eaa5ff1df32f2849a902e0bc087637f8595",
    "BTCUSDT_211231": "a5e3ca298896c9534964ddf809e2012975c970f9fb2b6e9020dae47f71716aec",
    "BTCUSDT_220325": "3505ed15fc1e56434f7973c0dd50d3d9289be9dfeb67af4977095dea5ee2de20",
    "BTCUSDT_220624": "900cdbbdbb0e6af702017b025756f487d1e0fa027d7b607ff9d2d7830b9c26c8",
    "BTCUSDT_220930": "9681acf8a3ee8859458ecf352cbb2668ece506a24e6ea094c3e22b62e6dc6279",
    "BTCUSDT_221230": "04fef855eac5ff6eaff26885a5766fc75306f7b0e96d8c0ab2c969408e2b2cdb",
    "BTCUSDT_230331": "dc611534031ef5d731aff14a7b33d686d99d91f32db29c732f54be7960859f5d",
    "BTCUSDT_230630": "9289310ec582a44699ef5b5db5f2faa6ee7c2920d4cdff855e165ef58796d2ba",
    "BTCUSDT_230929": "4f1613bb07d6eec43bce62e1a90c0572c1a93470ee46c56db33a79126f03467d",
    "BTCUSDT_231229": "4cfd4b62b78311ff891158d51e9db49f1e74c6470b037cb54760918d90e1385b",
    "BTCUSDT_240329": "e1af7fe888eb22c7541746718c8e1b7ef1a07cfc6f832763619f5c5cd3f4bb93",
    "BTCUSDT_240628": "b3361ea90026104b79acb664274adc52e8a89d32e1bb4026b5d6a7b95dc421c0",
    "BTCUSDT_240927": "0fc50fdd057392af9e7fadc91e62608574f60519b5c6aca5e06468e4334ea617",
    "BTCUSDT_241227": "685167715b3a1dd2d9d96cf0c26fe9fc5abd106f44006ac921b2bdae54d16979",
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


def verify_m17_freeze(root: str | Path = ".") -> dict[str, object]:
    base = Path(root)
    protocol = base / M17_PROTOCOL
    manifest_path = base / M17_FREEZE
    if not protocol.is_file() or not manifest_path.is_file():
        raise FileNotFoundError("M17 protocol or freeze manifest missing")

    actual_hash = canonical_text_sha256(protocol)
    if actual_hash != M17_PROTOCOL_SHA256:
        raise RuntimeError("M17 protocol changed after freeze")

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    checks = {
        "cycle": manifest.get("cycle") == M17_POLICY_NAME,
        "status": manifest.get("status") == "FROZEN_PREDECLARED_NOT_RUN",
        "protocol": manifest.get("protocol_sha256") == actual_hash,
        "m16": manifest.get("m16_evidence_sha256") == M16_EVIDENCE_SHA256,
        "spot": manifest.get("spot_input_sha256")
        == {
            "btc_spot_research_2021_2023": SPOT_RESEARCH_SHA256,
            "btc_spot_challenge_2024": SPOT_CHALLENGE_SHA256,
        },
        "delivery": manifest.get("usdm_delivery_normalized_sha256")
        == USDM_NORMALIZED_SHA256,
        "entries": manifest.get("entry_offsets_days") == list(ENTRY_OFFSETS_DAYS),
        "exit": manifest.get("exit_minutes_before_delivery")
        == EXIT_MINUTES_BEFORE_DELIVERY,
        "configs": manifest.get("configuration_count") == CONFIG_COUNT,
        "spot_notional": manifest.get("spot_entry_notional_usd")
        == SPOT_ENTRY_NOTIONAL_USD,
        "hedge": manifest.get("hedge_quantity") == "same_btc_quantity_as_spot",
        "margin_model": manifest.get("futures_margin_model")
        == "100_percent_entry_notional_1x",
        "base_cost": manifest.get("base_cost_bps_per_side_each_leg")
        == BASE_COST_BPS_PER_SIDE,
        "severe_cost": manifest.get("severe_cost_bps_per_side_each_leg")
        == SEVERE_COST_BPS_PER_SIDE,
        "margin_gate": manifest.get("margin_remaining_ratio_min")
        == MIN_MARGIN_REMAINING_RATIO,
        "fdr": manifest.get("fdr_q_threshold") == FDR_Q_THRESHOLD,
        "discovery": manifest.get("discovery_contracts") == DISCOVERY_CONTRACT_COUNT,
        "challenge": manifest.get("challenge_contracts") == CHALLENGE_CONTRACT_COUNT,
        "oos": manifest.get("oos_2025") == "LOCKED_NOT_ACCESSED",
        "coin_m": manifest.get("coin_m") == "forbidden",
        "leverage": manifest.get("leverage") == "forbidden",
        "naked_short": manifest.get("naked_short") == "forbidden",
        "settlement": manifest.get("settlement_price_model")
        == "forbidden_exit_15m_pre_delivery",
        "retune": manifest.get("parameter_changes_after_first_run") == "forbidden",
        "risk": manifest.get("risk_sizing") == "blocked",
        "live": manifest.get("live_execution") == "blocked",
    }
    failed = [name for name, passed in checks.items() if not passed]
    if failed:
        raise RuntimeError(f"M17 freeze manifest mismatch: {', '.join(failed)}")
    if len(USDM_NORMALIZED_SHA256) != 16:
        raise RuntimeError("M17 frozen USD-M contract hash count changed")
    if len(ENTRY_OFFSETS_DAYS) != CONFIG_COUNT:
        raise RuntimeError("M17 frozen configuration count changed")
    return manifest
