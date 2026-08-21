from __future__ import annotations

import hashlib
import json
from pathlib import Path

M13_POLICY_NAME = "m13_ml_edge_engine_v1"
M13_PROTOCOL = Path("docs/M13_ML_EDGE_ENGINE_PROTOCOL.md")
M13_FREEZE = Path("docs/M13_ML_EDGE_ENGINE_FREEZE.json")
M13_PROTOCOL_SHA256 = "a5cddd7375801426c6ac92050eca49431d7eeaa14b2f63f8cb089d0ddce7f2e8"

BTC_SPOT_RESEARCH_SHA256 = "253c6ae35856e58e35df17eaa71caeea5caaa3681c38dd7214a2872afccd8d63"
BTC_SPOT_CHALLENGE_SHA256 = "3a96b6b668cfacb0fefabb8665675d4ca589cc712b0681fb57e7a13356eda0f2"
BTC_FUTURES_SHA256 = "3c97c9b59ded32595f129a480a23e920823c0edbbf2e4f32c5d66e5020e35947"
BTC_FUNDING_SHA256 = "73b9decde0d54a0609d55ccfd49131a6e825416b595d728457bb01a968b55fd6"
ETH_FUTURES_SHA256 = "69855dcaf2f34c2a529ddb7f83964fa61b39ed0a27ae8796a6c0eaafd5b744f5"

HORIZONS_BARS = (4, 16, 48)
MODEL_FAMILIES = ("logistic", "hist_gb")
PROBABILITY_GATES = (0.60, 0.65)
FEATURE_COUNT = 19
TEST_COUNT = 12
SAMPLE_STRIDE_BARS = 4
BASE_ROUND_TRIP_COST_BPS = 30.0
SEVERE_ROUND_TRIP_COST_BPS = 70.0
FDR_Q_THRESHOLD = 0.10
RANDOM_STATE = 13
DISCOVERY_PREDICTION_YEARS = (2022, 2023)
CHALLENGE_YEAR = 2024

MIN_DISCOVERY_EVENTS = 80
MIN_DISCOVERY_DAYS = 30
MIN_DISCOVERY_EVENTS_PER_YEAR = 25
MIN_DISCOVERY_PROFIT_FACTOR = 1.10
MIN_CHALLENGE_EVENTS = 40
MIN_CHALLENGE_PROFIT_FACTOR = 1.10
MIN_POSITIVE_CHALLENGE_MONTHS = 6

FEATURE_NAMES = (
    "btc_spot_ret_1h",
    "btc_spot_ret_4h",
    "btc_spot_ret_12h",
    "btc_spot_abs_ret_mean_4h",
    "btc_spot_volume_ratio_96",
    "btc_spot_vwap_disp_96",
    "btc_perp_ret_1h",
    "btc_perp_taker_buy_share_1h",
    "btc_perp_quote_intensity_1h",
    "btc_perp_spot_premium",
    "btc_funding_latest",
    "btc_funding_minus_mean_90",
    "eth_perp_ret_1h",
    "eth_perp_ret_4h",
    "eth_perp_ret_12h",
    "eth_perp_taker_buy_share_1h",
    "eth_perp_quote_intensity_1h",
    "eth_minus_btc_ret_1h",
    "eth_minus_btc_ret_4h",
)


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


def verify_m13_freeze(root: str | Path = ".") -> dict[str, object]:
    base = Path(root)
    protocol = base / M13_PROTOCOL
    freeze_path = base / M13_FREEZE
    if not protocol.is_file() or not freeze_path.is_file():
        raise FileNotFoundError("M13 protocol or freeze manifest is missing")

    actual_hash = canonical_text_sha256(protocol)
    if actual_hash != M13_PROTOCOL_SHA256:
        raise RuntimeError("M13 protocol changed after freeze")

    manifest = json.loads(freeze_path.read_text(encoding="utf-8"))
    expected_hashes = {
        "btc_spot_research_2021_2023": BTC_SPOT_RESEARCH_SHA256,
        "btc_spot_challenge_2024": BTC_SPOT_CHALLENGE_SHA256,
        "btc_usdm_15m_2021_2024": BTC_FUTURES_SHA256,
        "btc_funding_2021_2024": BTC_FUNDING_SHA256,
        "eth_usdm_15m_2021_2024": ETH_FUTURES_SHA256,
    }
    checks = {
        "cycle": manifest.get("cycle") == M13_POLICY_NAME,
        "status": manifest.get("status") == "FROZEN_PREDECLARED_NOT_RUN",
        "protocol": manifest.get("protocol_sha256") == actual_hash,
        "hashes": manifest.get("input_sha256") == expected_hashes,
        "feature_count": manifest.get("feature_count") == FEATURE_COUNT == len(FEATURE_NAMES),
        "models": manifest.get("model_families") == list(MODEL_FAMILIES),
        "gates": manifest.get("probability_gates") == list(PROBABILITY_GATES),
        "horizons": manifest.get("horizons_bars") == list(HORIZONS_BARS),
        "tests": manifest.get("hypothesis_test_count") == TEST_COUNT,
        "stride": manifest.get("sample_stride_bars") == SAMPLE_STRIDE_BARS,
        "base_cost": manifest.get("base_round_trip_cost_bps") == BASE_ROUND_TRIP_COST_BPS,
        "severe_cost": manifest.get("severe_round_trip_cost_bps")
        == SEVERE_ROUND_TRIP_COST_BPS,
        "fdr": manifest.get("fdr_q_threshold") == FDR_Q_THRESHOLD,
        "years": manifest.get("discovery_prediction_years")
        == list(DISCOVERY_PREDICTION_YEARS),
        "challenge": manifest.get("challenge_year") == CHALLENGE_YEAR,
        "seed": manifest.get("random_state") == RANDOM_STATE,
        "oos": manifest.get("oos_2025") == "LOCKED_NOT_ACCESSED",
        "retune": manifest.get("parameter_changes_after_first_run") == "forbidden",
        "risk": manifest.get("risk_sizing") == "blocked",
        "live": manifest.get("live_execution") == "blocked",
        "risk_override": manifest.get("ai_override_of_risk") == "forbidden",
    }
    failed = [name for name, passed in checks.items() if not passed]
    if failed:
        raise RuntimeError(f"M13 freeze manifest mismatch: {', '.join(failed)}")
    if len(MODEL_FAMILIES) * len(PROBABILITY_GATES) * len(HORIZONS_BARS) != TEST_COUNT:
        raise RuntimeError("M13 frozen test count is inconsistent")
    return manifest
