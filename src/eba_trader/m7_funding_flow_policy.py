from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path

M7_POLICY_NAME = "m7_funding_futures_edge_discovery_v1"
M7_PROTOCOL = Path("docs/M7_FUNDING_FUTURES_EDGE_DISCOVERY_PROTOCOL.md")
M7_FREEZE = Path("docs/M7_FUNDING_FUTURES_EDGE_DISCOVERY_FREEZE.json")
M7_PROTOCOL_SHA256 = "3423bad14ef2f1c9ee5414f735ede1e99f9ddd313b2ffb3465e0636b3653e28a"

DISCOVERY_START = "2021-01-01T00:00:00Z"
DISCOVERY_END_EXCLUSIVE = "2024-01-01T00:00:00Z"
CHALLENGE_START = "2024-01-01T00:00:00Z"
CHALLENGE_END_EXCLUSIVE = "2025-01-01T00:00:00Z"

FUNDING_SHA256 = "73b9decde0d54a0609d55ccfd49131a6e825416b595d728457bb01a968b55fd6"
FUTURES_SHA256 = "3c97c9b59ded32595f129a480a23e920823c0edbbf2e4f32c5d66e5020e35947"
SPOT_RESEARCH_SHA256 = "253c6ae35856e58e35df17eaa71caeea5caaa3681c38dd7214a2872afccd8d63"
SPOT_CHALLENGE_SHA256 = "3a96b6b668cfacb0fefabb8665675d4ca589cc712b0681fb57e7a13356eda0f2"

HORIZONS_BARS = (4, 16, 48)
EVENT_COOLDOWN_BARS = 4
FUNDING_LOOKBACK_RECORDS = 270
ACTIVITY_BASELINE_WINDOWS = 96
BASE_ROUND_TRIP_COST_BPS = 30.0
SEVERE_ROUND_TRIP_COST_BPS = 70.0
BASELINE_UPLIFT = 0.001
FDR_Q_THRESHOLD = 0.10
MIN_DISCOVERY_EVENTS = 60
MIN_DISCOVERY_DAYS = 20
MIN_DISCOVERY_EVENTS_PER_YEAR = 10
MIN_CHALLENGE_EVENTS = 15


@dataclass(frozen=True, slots=True)
class M7CandidateSpec:
    name: str
    family: str
    direction: int
    window_bars: int | None = None
    funding_side: int | None = None
    taker_share_min: float | None = None
    taker_share_max: float | None = None
    quote_intensity_min: float | None = None
    trade_intensity_min: float | None = None
    abs_return_max: float | None = None

    def __post_init__(self) -> None:
        if self.direction not in {-1, 1}:
            raise ValueError("M7 candidate direction must be -1 or +1")
        if self.family not in {"funding", "flow", "neutral_flow", "funding_flow"}:
            raise ValueError(f"Unknown M7 candidate family: {self.family}")
        if self.window_bars is not None and self.window_bars not in {4, 16}:
            raise ValueError("M7 window_bars must be 4 or 16")
        if self.funding_side is not None and self.funding_side not in {-1, 1}:
            raise ValueError("M7 funding_side must be -1 or +1")
        for value in (self.taker_share_min, self.taker_share_max):
            if value is not None and not 0 <= value <= 1:
                raise ValueError("Taker-share thresholds must be in [0, 1]")
        for value in (self.quote_intensity_min, self.trade_intensity_min):
            if value is not None and value <= 0:
                raise ValueError("Activity-intensity thresholds must be positive")
        if self.abs_return_max is not None and self.abs_return_max <= 0:
            raise ValueError("abs_return_max must be positive")


M7_CANDIDATES = (
    M7CandidateSpec("funding_extreme_negative", "funding", 1, funding_side=-1),
    M7CandidateSpec("funding_extreme_positive", "funding", -1, funding_side=1),
    M7CandidateSpec(
        "flow_1h_buy_vol_1_5",
        "flow",
        1,
        window_bars=4,
        taker_share_min=0.55,
        quote_intensity_min=1.50,
    ),
    M7CandidateSpec(
        "flow_1h_sell_vol_1_5",
        "flow",
        -1,
        window_bars=4,
        taker_share_max=0.45,
        quote_intensity_min=1.50,
    ),
    M7CandidateSpec(
        "flow_4h_buy_vol_1_25",
        "flow",
        1,
        window_bars=16,
        taker_share_min=0.53,
        quote_intensity_min=1.25,
    ),
    M7CandidateSpec(
        "flow_4h_sell_vol_1_25",
        "flow",
        -1,
        window_bars=16,
        taker_share_max=0.47,
        quote_intensity_min=1.25,
    ),
    M7CandidateSpec(
        "neutral_flow_1h_buy",
        "neutral_flow",
        1,
        window_bars=4,
        taker_share_min=0.55,
        quote_intensity_min=1.25,
        trade_intensity_min=1.25,
        abs_return_max=0.005,
    ),
    M7CandidateSpec(
        "neutral_flow_1h_sell",
        "neutral_flow",
        -1,
        window_bars=4,
        taker_share_max=0.45,
        quote_intensity_min=1.25,
        trade_intensity_min=1.25,
        abs_return_max=0.005,
    ),
    M7CandidateSpec(
        "funding_negative_post_buy",
        "funding_flow",
        1,
        window_bars=4,
        funding_side=-1,
        taker_share_min=0.55,
    ),
    M7CandidateSpec(
        "funding_negative_post_sell",
        "funding_flow",
        -1,
        window_bars=4,
        funding_side=-1,
        taker_share_max=0.45,
    ),
    M7CandidateSpec(
        "funding_positive_post_buy",
        "funding_flow",
        1,
        window_bars=4,
        funding_side=1,
        taker_share_min=0.55,
    ),
    M7CandidateSpec(
        "funding_positive_post_sell",
        "funding_flow",
        -1,
        window_bars=4,
        funding_side=1,
        taker_share_max=0.45,
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


def verify_m7_freeze(root: str | Path = ".") -> dict[str, object]:
    base = Path(root)
    protocol = base / M7_PROTOCOL
    freeze_path = base / M7_FREEZE
    if not protocol.is_file() or not freeze_path.is_file():
        raise FileNotFoundError("M7 protocol or freeze manifest is missing")

    actual_hash = canonical_text_sha256(protocol)
    if actual_hash != M7_PROTOCOL_SHA256:
        raise RuntimeError("M7 protocol changed after freeze")

    manifest = json.loads(freeze_path.read_text(encoding="utf-8"))
    expected_hashes = {
        "funding_2021_2024": FUNDING_SHA256,
        "futures_15m_2021_2024": FUTURES_SHA256,
        "spot_research_2021_2023": SPOT_RESEARCH_SHA256,
        "spot_challenge_2024": SPOT_CHALLENGE_SHA256,
    }
    checks = {
        "cycle": manifest.get("cycle") == M7_POLICY_NAME,
        "status": manifest.get("status") == "FROZEN_PREDECLARED_NOT_RUN",
        "protocol": manifest.get("protocol_sha256") == actual_hash,
        "candidate_count": manifest.get("candidate_count") == len(M7_CANDIDATES) == 12,
        "horizons": manifest.get("horizons_bars") == list(HORIZONS_BARS),
        "test_count": manifest.get("hypothesis_test_count") == 36,
        "hashes": manifest.get("input_sha256") == expected_hashes,
        "cost_base": manifest.get("base_round_trip_cost_bps") == BASE_ROUND_TRIP_COST_BPS,
        "cost_severe": manifest.get("severe_round_trip_cost_bps") == SEVERE_ROUND_TRIP_COST_BPS,
        "uplift": manifest.get("baseline_uplift") == BASELINE_UPLIFT,
        "fdr": manifest.get("fdr_q_threshold") == FDR_Q_THRESHOLD,
        "cooldown": manifest.get("event_cooldown_bars") == EVENT_COOLDOWN_BARS,
        "funding_lookback": manifest.get("funding_lookback_records") == FUNDING_LOOKBACK_RECORDS,
        "oos": manifest.get("oos_2025") == "LOCKED_NOT_ACCESSED",
        "retune": manifest.get("parameter_changes_after_first_run") == "forbidden",
        "strategy": manifest.get("strategy_generation") == "forbidden",
        "premium": manifest.get("premium_index") == "excluded_failed_m6_data_audit",
        "index": manifest.get("index_price") == "excluded_failed_m6_data_audit",
        "ai": manifest.get("ai_module") == "excluded",
    }
    failed = [name for name, passed in checks.items() if not passed]
    if failed:
        raise RuntimeError(f"M7 freeze manifest mismatch: {', '.join(failed)}")
    if len({candidate.name for candidate in M7_CANDIDATES}) != 12:
        raise RuntimeError("M7 candidate names must be unique")
    return manifest
