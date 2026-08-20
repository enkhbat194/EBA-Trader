from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path

EDGE_DISCOVERY_POLICY_NAME = "m5_edge_discovery_price_volume_v1"
EDGE_DISCOVERY_PROTOCOL = Path("docs/M5_EDGE_DISCOVERY_PROTOCOL.md")
EDGE_DISCOVERY_FREEZE = Path("docs/M5_EDGE_DISCOVERY_FREEZE.json")
EDGE_DISCOVERY_PROTOCOL_SHA256 = (
    "da522bce26c8c560e36672267cca2a9a9763dfae9e03b7fbe503254f626453b8"
)

EDGE_DISCOVERY_RESEARCH_SHA256 = (
    "253c6ae35856e58e35df17eaa71caeea5caaa3681c38dd7214a2872afccd8d63"
)
EDGE_DISCOVERY_CHALLENGE_SHA256 = (
    "3a96b6b668cfacb0fefabb8665675d4ca589cc712b0681fb57e7a13356eda0f2"
)

HORIZONS_BARS = (4, 16, 48)
EVENT_COOLDOWN_BARS = 4
ATR_PERIOD = 14
ROLLING_WINDOW_BARS = 96
BREAKOUT_LOOKBACK_BARS = 20
MAX_RELATIVE_ATR = 0.80
BASE_ROUND_TRIP_COST_BPS = 30.0
SEVERE_ROUND_TRIP_COST_BPS = 70.0
FDR_Q_THRESHOLD = 0.10
MIN_DISCOVERY_EVENTS = 60
MIN_DISCOVERY_DAYS = 20
MIN_DISCOVERY_EVENTS_PER_YEAR = 10
MIN_CHALLENGE_EVENTS = 15


@dataclass(frozen=True, slots=True)
class EdgeCandidateSpec:
    name: str
    family: str
    direction: int
    return_lookback_bars: int | None = None
    return_threshold: float | None = None
    volume_ratio_min: float | None = None
    displacement_atr: float | None = None
    max_relative_atr: float | None = None

    def __post_init__(self) -> None:
        if self.direction not in {-1, 1}:
            raise ValueError("Candidate direction must be -1 or +1")
        if self.family not in {
            "return_impulse",
            "volume_impulse",
            "vwap_displacement",
            "compressed_breakout",
        }:
            raise ValueError(f"Unknown candidate family: {self.family}")
        if self.return_lookback_bars is not None and self.return_lookback_bars <= 0:
            raise ValueError("Return lookback must be positive")
        if self.return_threshold is not None and self.return_threshold <= 0:
            raise ValueError("Return threshold must be positive")
        if self.volume_ratio_min is not None and self.volume_ratio_min <= 0:
            raise ValueError("Volume ratio minimum must be positive")
        if self.displacement_atr is not None and self.displacement_atr <= 0:
            raise ValueError("Displacement threshold must be positive")
        if self.max_relative_atr is not None and self.max_relative_atr <= 0:
            raise ValueError("Relative ATR ceiling must be positive")


EDGE_CANDIDATES = (
    EdgeCandidateSpec("ret_1h_up_1_5", "return_impulse", 1, 4, 0.015),
    EdgeCandidateSpec("ret_1h_up_2_5", "return_impulse", 1, 4, 0.025),
    EdgeCandidateSpec("ret_4h_up_3_0", "return_impulse", 1, 16, 0.030),
    EdgeCandidateSpec("ret_4h_up_5_0", "return_impulse", 1, 16, 0.050),
    EdgeCandidateSpec("ret_1h_down_1_5", "return_impulse", -1, 4, 0.015),
    EdgeCandidateSpec("ret_1h_down_2_5", "return_impulse", -1, 4, 0.025),
    EdgeCandidateSpec("ret_4h_down_3_0", "return_impulse", -1, 16, 0.030),
    EdgeCandidateSpec("ret_4h_down_5_0", "return_impulse", -1, 16, 0.050),
    EdgeCandidateSpec(
        "volume_ret_1h_up_1_5_x1_5",
        "volume_impulse",
        1,
        4,
        0.015,
        1.5,
    ),
    EdgeCandidateSpec(
        "volume_ret_1h_up_1_5_x2_0",
        "volume_impulse",
        1,
        4,
        0.015,
        2.0,
    ),
    EdgeCandidateSpec(
        "volume_ret_4h_up_3_0_x1_5",
        "volume_impulse",
        1,
        16,
        0.030,
        1.5,
    ),
    EdgeCandidateSpec(
        "volume_ret_4h_up_3_0_x2_0",
        "volume_impulse",
        1,
        16,
        0.030,
        2.0,
    ),
    EdgeCandidateSpec(
        "volume_ret_1h_down_1_5_x1_5",
        "volume_impulse",
        -1,
        4,
        0.015,
        1.5,
    ),
    EdgeCandidateSpec(
        "volume_ret_1h_down_1_5_x2_0",
        "volume_impulse",
        -1,
        4,
        0.015,
        2.0,
    ),
    EdgeCandidateSpec(
        "volume_ret_4h_down_3_0_x1_5",
        "volume_impulse",
        -1,
        16,
        0.030,
        1.5,
    ),
    EdgeCandidateSpec(
        "volume_ret_4h_down_3_0_x2_0",
        "volume_impulse",
        -1,
        16,
        0.030,
        2.0,
    ),
    EdgeCandidateSpec("vwap_up_1_0_atr", "vwap_displacement", 1, displacement_atr=1.0),
    EdgeCandidateSpec("vwap_up_2_0_atr", "vwap_displacement", 1, displacement_atr=2.0),
    EdgeCandidateSpec("vwap_down_1_0_atr", "vwap_displacement", -1, displacement_atr=1.0),
    EdgeCandidateSpec("vwap_down_2_0_atr", "vwap_displacement", -1, displacement_atr=2.0),
    EdgeCandidateSpec(
        "compressed_breakout_up_vol_1_5",
        "compressed_breakout",
        1,
        volume_ratio_min=1.5,
        max_relative_atr=MAX_RELATIVE_ATR,
    ),
    EdgeCandidateSpec(
        "compressed_breakout_up_vol_2_0",
        "compressed_breakout",
        1,
        volume_ratio_min=2.0,
        max_relative_atr=MAX_RELATIVE_ATR,
    ),
    EdgeCandidateSpec(
        "compressed_breakout_down_vol_1_5",
        "compressed_breakout",
        -1,
        volume_ratio_min=1.5,
        max_relative_atr=MAX_RELATIVE_ATR,
    ),
    EdgeCandidateSpec(
        "compressed_breakout_down_vol_2_0",
        "compressed_breakout",
        -1,
        volume_ratio_min=2.0,
        max_relative_atr=MAX_RELATIVE_ATR,
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


def verify_edge_discovery_freeze(root: str | Path = ".") -> dict[str, object]:
    base = Path(root)
    protocol = base / EDGE_DISCOVERY_PROTOCOL
    manifest_path = base / EDGE_DISCOVERY_FREEZE
    if not protocol.is_file() or not manifest_path.is_file():
        raise FileNotFoundError("M5 protocol document or freeze manifest is missing")

    actual_protocol_hash = canonical_text_sha256(protocol)
    if actual_protocol_hash != EDGE_DISCOVERY_PROTOCOL_SHA256:
        raise RuntimeError("M5 edge discovery protocol changed after freeze")

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("cycle") != EDGE_DISCOVERY_POLICY_NAME:
        raise RuntimeError("M5 freeze manifest cycle mismatch")
    if manifest.get("protocol_sha256") != actual_protocol_hash:
        raise RuntimeError("M5 freeze manifest protocol hash mismatch")
    if manifest.get("candidate_count") != len(EDGE_CANDIDATES):
        raise RuntimeError("M5 candidate count mismatch")
    if manifest.get("hypothesis_test_count") != len(EDGE_CANDIDATES) * len(HORIZONS_BARS):
        raise RuntimeError("M5 hypothesis-test count mismatch")
    if manifest.get("horizons_bars") != list(HORIZONS_BARS):
        raise RuntimeError("M5 horizon set mismatch")
    if manifest.get("oos_2025") != "LOCKED_NOT_ACCESSED":
        raise RuntimeError("M5 does not preserve the 2025 OOS lock")
    if manifest.get("strategy_generation") != "forbidden":
        raise RuntimeError("M5 unexpectedly permits strategy generation")
    if manifest.get("ai_module") != "excluded":
        raise RuntimeError("M5 unexpectedly includes AI")
    if len(EDGE_CANDIDATES) != 24 or len({item.name for item in EDGE_CANDIDATES}) != 24:
        raise RuntimeError("M5 frozen search space must contain 24 unique candidates")
    return manifest
