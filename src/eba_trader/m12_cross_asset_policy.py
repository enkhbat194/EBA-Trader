from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path

M12_POLICY_NAME = "m12_cross_asset_eth_btc_edge_v1"
M12_PROTOCOL = Path("docs/M12_CROSS_ASSET_ETH_BTC_EDGE_DISCOVERY_PROTOCOL.md")
M12_FREEZE = Path("docs/M12_CROSS_ASSET_ETH_BTC_EDGE_DISCOVERY_FREEZE.json")
M12_PROTOCOL_SHA256 = "7ed775d3ce114dfaf4b768b4d9d95c3039c1b349171686684aaa6fea04b803b1"

DISCOVERY_START = "2021-01-01T00:00:00Z"
DISCOVERY_END_EXCLUSIVE = "2024-01-01T00:00:00Z"
CHALLENGE_START = "2024-01-01T00:00:00Z"
CHALLENGE_END_EXCLUSIVE = "2025-01-01T00:00:00Z"

ETH_SHA256 = "69855dcaf2f34c2a529ddb7f83964fa61b39ed0a27ae8796a6c0eaafd5b744f5"
SPOT_RESEARCH_SHA256 = "253c6ae35856e58e35df17eaa71caeea5caaa3681c38dd7214a2872afccd8d63"
SPOT_CHALLENGE_SHA256 = "3a96b6b668cfacb0fefabb8665675d4ca589cc712b0681fb57e7a13356eda0f2"

HORIZONS_BARS = (4, 16, 48)
EVENT_COOLDOWN_BARS = 4
FLOW_BASELINE_WINDOWS = 96
BASE_ROUND_TRIP_COST_BPS = 30.0
SEVERE_ROUND_TRIP_COST_BPS = 70.0
BASELINE_UPLIFT = 0.001
FDR_Q_THRESHOLD = 0.10
MIN_DISCOVERY_EVENTS = 60
MIN_DISCOVERY_DAYS = 20
MIN_DISCOVERY_EVENTS_PER_YEAR = 10
MIN_CHALLENGE_EVENTS = 15


@dataclass(frozen=True, slots=True)
class M12CandidateSpec:
    name: str
    family: str
    direction: int
    return_window_bars: int | None = None
    return_threshold: float | None = None
    relative_threshold: float | None = None
    taker_share_min: float | None = None
    taker_share_max: float | None = None
    quote_intensity_min: float | None = None

    def __post_init__(self) -> None:
        if self.direction not in {-1, 1}:
            raise ValueError("M12 candidate direction must be -1 or +1")
        if self.family not in {"impulse", "relative", "flow_impulse"}:
            raise ValueError(f"Unknown M12 candidate family: {self.family}")
        if self.return_window_bars is not None and self.return_window_bars not in {4, 16}:
            raise ValueError("M12 return window must be 4 or 16 bars")
        if self.return_threshold is not None and self.return_threshold <= 0:
            raise ValueError("return threshold must be positive magnitude")
        if self.relative_threshold is not None and self.relative_threshold <= 0:
            raise ValueError("relative threshold must be positive magnitude")
        for value in (self.taker_share_min, self.taker_share_max):
            if value is not None and not 0 <= value <= 1:
                raise ValueError("taker-share thresholds must be in [0, 1]")
        if self.quote_intensity_min is not None and self.quote_intensity_min <= 0:
            raise ValueError("quote intensity threshold must be positive")


M12_CANDIDATES = (
    M12CandidateSpec("eth_1h_up_1_5", "impulse", 1, 4, return_threshold=0.015),
    M12CandidateSpec("eth_1h_down_1_5", "impulse", -1, 4, return_threshold=0.015),
    M12CandidateSpec("eth_4h_up_3", "impulse", 1, 16, return_threshold=0.03),
    M12CandidateSpec("eth_4h_down_3", "impulse", -1, 16, return_threshold=0.03),
    M12CandidateSpec(
        "eth_relative_1h_outperform_1",
        "relative",
        1,
        4,
        relative_threshold=0.01,
    ),
    M12CandidateSpec(
        "eth_relative_1h_underperform_1",
        "relative",
        -1,
        4,
        relative_threshold=0.01,
    ),
    M12CandidateSpec(
        "eth_flow_1h_up_buy_confirm",
        "flow_impulse",
        1,
        4,
        return_threshold=0.015,
        taker_share_min=0.55,
        quote_intensity_min=1.25,
    ),
    M12CandidateSpec(
        "eth_flow_1h_down_sell_confirm",
        "flow_impulse",
        -1,
        4,
        return_threshold=0.015,
        taker_share_max=0.45,
        quote_intensity_min=1.25,
    ),
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


def verify_m12_freeze(root: str | Path = ".") -> dict[str, object]:
    base = Path(root)
    protocol = base / M12_PROTOCOL
    freeze_path = base / M12_FREEZE
    if not protocol.is_file() or not freeze_path.is_file():
        raise FileNotFoundError("M12 protocol or freeze manifest is missing")

    actual_hash = canonical_text_sha256(protocol)
    if actual_hash != M12_PROTOCOL_SHA256:
        raise RuntimeError("M12 protocol changed after freeze")

    manifest = json.loads(freeze_path.read_text(encoding="utf-8"))
    expected_hashes = {
        "ethusdt_usdm_15m_2021_2024": ETH_SHA256,
        "btcusdt_spot_research_2021_2023": SPOT_RESEARCH_SHA256,
        "btcusdt_spot_challenge_2024": SPOT_CHALLENGE_SHA256,
    }
    checks = {
        "cycle": manifest.get("cycle") == M12_POLICY_NAME,
        "status": manifest.get("status") == "FROZEN_PREDECLARED_NOT_RUN",
        "protocol": manifest.get("protocol_sha256") == actual_hash,
        "candidate_count": manifest.get("candidate_count") == len(M12_CANDIDATES) == 8,
        "horizons": manifest.get("horizons_bars") == list(HORIZONS_BARS),
        "test_count": manifest.get("hypothesis_test_count") == 24,
        "hashes": manifest.get("input_sha256") == expected_hashes,
        "cooldown": manifest.get("event_cooldown_bars") == EVENT_COOLDOWN_BARS,
        "flow_baseline": manifest.get("flow_baseline_windows") == FLOW_BASELINE_WINDOWS,
        "base_cost": manifest.get("base_round_trip_cost_bps") == BASE_ROUND_TRIP_COST_BPS,
        "severe_cost": manifest.get("severe_round_trip_cost_bps")
        == SEVERE_ROUND_TRIP_COST_BPS,
        "uplift": manifest.get("baseline_uplift") == BASELINE_UPLIFT,
        "fdr": manifest.get("fdr_q_threshold") == FDR_Q_THRESHOLD,
        "min_events": manifest.get("minimum_discovery_events") == MIN_DISCOVERY_EVENTS,
        "min_days": manifest.get("minimum_discovery_days") == MIN_DISCOVERY_DAYS,
        "min_year": manifest.get("minimum_discovery_events_per_year")
        == MIN_DISCOVERY_EVENTS_PER_YEAR,
        "min_challenge": manifest.get("minimum_challenge_events") == MIN_CHALLENGE_EVENTS,
        "m10": manifest.get("m10_eth_spot") == "excluded_failed_data_audit",
        "strategy": manifest.get("strategy_generation") == "forbidden",
        "risk": manifest.get("risk_sizing") == "forbidden",
        "ai": manifest.get("ai_module") == "excluded",
        "oos": manifest.get("oos_2025") == "LOCKED_NOT_ACCESSED",
        "retune": manifest.get("parameter_changes_after_first_run") == "forbidden",
    }
    failed = [name for name, passed in checks.items() if not passed]
    if failed:
        raise RuntimeError(f"M12 freeze manifest mismatch: {', '.join(failed)}")
    if len({candidate.name for candidate in M12_CANDIDATES}) != 8:
        raise RuntimeError("M12 candidate names must be unique")
    return manifest
