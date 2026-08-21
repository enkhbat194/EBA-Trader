from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path

M9_POLICY_NAME = "m9_bookdepth_microstructure_edge_v1"
M9_PROTOCOL = Path("docs/M9_BOOKDEPTH_MICROSTRUCTURE_EDGE_PROTOCOL.md")
M9_FREEZE = Path("docs/M9_BOOKDEPTH_MICROSTRUCTURE_EDGE_FREEZE.json")
M9_PROTOCOL_SHA256 = "3312cb1f79bc15bdda5aff9ba151750e1e51ebf9c395c200a20237e181bb11e8"

DISCOVERY_START = "2023-01-01T00:00:00Z"
DISCOVERY_END_EXCLUSIVE = "2024-01-01T00:00:00Z"
CHALLENGE_START = "2024-01-01T00:00:00Z"
CHALLENGE_END_EXCLUSIVE = "2025-01-01T00:00:00Z"

BOOKDEPTH_EXPECTED_DAYS = 731
M8_EVIDENCE_SHA256 = "1bcfd0f44917d608b0d0c413d22aa7ce851e55ee4d54b1b81f87f588682a887f"
SPOT_RESEARCH_SHA256 = "253c6ae35856e58e35df17eaa71caeea5caaa3681c38dd7214a2872afccd8d63"
SPOT_CHALLENGE_SHA256 = "3a96b6b668cfacb0fefabb8665675d4ca589cc712b0681fb57e7a13356eda0f2"

FEATURE_BASELINE_BARS = 96
MIN_SNAPSHOTS_PER_15M = 20
MAX_SNAPSHOT_STALENESS_MS = 120_000
CHANGE_LAG_BARS = 4
Z_THRESHOLD = 1.50
EVENT_COOLDOWN_BARS = 4
HORIZONS_BARS = (4, 16, 48)
BASE_ROUND_TRIP_COST_BPS = 30.0
SEVERE_ROUND_TRIP_COST_BPS = 70.0
BASELINE_UPLIFT = 0.001
FDR_Q_THRESHOLD = 0.10
MIN_DISCOVERY_EVENTS = 80
MIN_DISCOVERY_DAYS = 40
MIN_DISCOVERY_EVENTS_PER_PASSING_QUARTER = 12
MIN_DISCOVERY_PASSING_QUARTERS = 3
MIN_CHALLENGE_EVENTS = 50
MIN_CHALLENGE_DAYS = 30
MIN_CHALLENGE_EVENTS_PER_QUARTER = 8
MIN_CHALLENGE_POSITIVE_QUARTERS = 3


@dataclass(frozen=True, slots=True)
class M9CandidateSpec:
    name: str
    feature: str
    direction: int
    threshold_side: int

    def __post_init__(self) -> None:
        if self.feature not in {
            "notional_1_z",
            "notional_5_z",
            "depth_1_z",
            "notional_1_change_4bar_z",
        }:
            raise ValueError(f"Unknown M9 feature: {self.feature}")
        if self.direction not in {-1, 1}:
            raise ValueError("M9 candidate direction must be -1 or +1")
        if self.threshold_side not in {-1, 1}:
            raise ValueError("M9 threshold_side must be -1 or +1")


M9_CANDIDATES = (
    M9CandidateSpec("notional_1_negative_side_dominant", "notional_1_z", 1, 1),
    M9CandidateSpec("notional_1_positive_side_dominant", "notional_1_z", -1, -1),
    M9CandidateSpec("notional_5_negative_side_dominant", "notional_5_z", 1, 1),
    M9CandidateSpec("notional_5_positive_side_dominant", "notional_5_z", -1, -1),
    M9CandidateSpec("depth_1_negative_side_dominant", "depth_1_z", 1, 1),
    M9CandidateSpec("depth_1_positive_side_dominant", "depth_1_z", -1, -1),
    M9CandidateSpec("notional_1_imbalance_rising", "notional_1_change_4bar_z", 1, 1),
    M9CandidateSpec("notional_1_imbalance_falling", "notional_1_change_4bar_z", -1, -1),
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


def verify_m9_freeze(root: str | Path = ".") -> dict[str, object]:
    base = Path(root)
    protocol = base / M9_PROTOCOL
    freeze_path = base / M9_FREEZE
    if not protocol.is_file() or not freeze_path.is_file():
        raise FileNotFoundError("M9 protocol or freeze manifest is missing")

    actual_hash = canonical_text_sha256(protocol)
    if actual_hash != M9_PROTOCOL_SHA256:
        raise RuntimeError("M9 protocol changed after freeze")

    manifest = json.loads(freeze_path.read_text(encoding="utf-8"))
    checks = {
        "cycle": manifest.get("cycle") == M9_POLICY_NAME,
        "status": manifest.get("status") == "FROZEN_PREDECLARED_NOT_RUN",
        "protocol": manifest.get("protocol_sha256") == actual_hash,
        "boundary_discovery": manifest.get("discovery_start") == DISCOVERY_START
        and manifest.get("discovery_end_exclusive") == DISCOVERY_END_EXCLUSIVE,
        "boundary_challenge": manifest.get("challenge_start") == CHALLENGE_START
        and manifest.get("challenge_end_exclusive") == CHALLENGE_END_EXCLUSIVE,
        "oos": manifest.get("oos_2025") == "LOCKED_NOT_ACCESSED",
        "m8": manifest.get("m8_evidence_sha256") == M8_EVIDENCE_SHA256,
        "days": manifest.get("bookdepth_expected_days") == BOOKDEPTH_EXPECTED_DAYS,
        "candidate_count": manifest.get("candidate_count") == len(M9_CANDIDATES) == 8,
        "horizons": manifest.get("horizons_bars") == list(HORIZONS_BARS),
        "tests": manifest.get("hypothesis_test_count") == 24,
        "baseline": manifest.get("feature_baseline_bars") == FEATURE_BASELINE_BARS,
        "snapshots": manifest.get("minimum_snapshots_per_15m") == MIN_SNAPSHOTS_PER_15M,
        "staleness": manifest.get("maximum_snapshot_staleness_seconds")
        == MAX_SNAPSHOT_STALENESS_MS // 1000,
        "lag": manifest.get("change_lag_bars") == CHANGE_LAG_BARS,
        "z": manifest.get("z_threshold") == Z_THRESHOLD,
        "cooldown": manifest.get("event_cooldown_bars") == EVENT_COOLDOWN_BARS,
        "base_cost": manifest.get("base_round_trip_cost_bps") == BASE_ROUND_TRIP_COST_BPS,
        "severe_cost": manifest.get("severe_round_trip_cost_bps") == SEVERE_ROUND_TRIP_COST_BPS,
        "uplift": manifest.get("baseline_uplift") == BASELINE_UPLIFT,
        "fdr": manifest.get("fdr_q_threshold") == FDR_Q_THRESHOLD,
        "retune": manifest.get("parameter_changes_after_first_run") == "forbidden",
        "all_tests": manifest.get("record_all_tests") is True,
        "strategy": manifest.get("strategy_generation") == "forbidden",
        "risk": manifest.get("risk_sizing") == "forbidden",
        "short": manifest.get("short_execution") == "forbidden",
        "ai": manifest.get("ai_module") == "excluded",
        "live": manifest.get("live_execution") == "forbidden",
    }
    hashes = manifest.get("spot_input_sha256")
    checks["spot_hashes"] = hashes == {
        "research_2021_2023_file": SPOT_RESEARCH_SHA256,
        "challenge_2024_file": SPOT_CHALLENGE_SHA256,
    }
    failed = [name for name, passed in checks.items() if not passed]
    if failed:
        raise RuntimeError(f"M9 freeze manifest mismatch: {', '.join(failed)}")
    if len({candidate.name for candidate in M9_CANDIDATES}) != 8:
        raise RuntimeError("M9 candidate names must be unique")
    return manifest
