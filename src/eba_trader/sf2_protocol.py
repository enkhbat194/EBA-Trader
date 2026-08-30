from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .history import parse_utc
from .m5_study_policy import (
    DEFAULT_M5_DEVELOPMENT_CORPUS,
    DEFAULT_M5_STUDY_POLICY,
    M5DevelopmentCorpusSpec,
    M5StudyWindow,
)
from .research_evidence import canonical_json, sha256_text

PROTOCOL_SCHEMA = "sf2_research_protocol_v1"
PHASE_ID = "sf2_fresh_development_v1"
SOURCE_PHASE = "sf1_independent_families_v1"
PLANNED_MULTIPLE_TESTING_BUDGET = 48
ACTIVE_CANDIDATE_COUNT = 24
WARMUP_BARS = 64
EXPECTED_WINDOW_COUNT = 12
EXPECTED_WINDOW_DURATION_MS = 4 * 60 * 60 * 1000
FEE_BPS = 4.0
SLIPPAGE_BPS = 1.5
SIGNAL_TO_EXECUTION_DELAY_BARS = 1
MINIMUM_HOLD_BARS = 2
MAX_HOLD_BARS = 12
MINIMUM_TOTAL_TRADES = 30
MINIMUM_BASELINE_BEATING_WINDOWS = 9
ADJUSTED_ALPHA_MAX = 0.05
PERMUTATION_COUNT = 4096
ORIGINAL_SMOKE_DAY_START_MS = parse_utc("2026-08-01T00:00:00Z")
ORIGINAL_SMOKE_DAY_END_MS = parse_utc("2026-08-02T00:00:00Z")


@dataclass(frozen=True, slots=True)
class SF2Candidate:
    candidate_id: str
    family: str
    parameters: dict[str, float | int]

    def as_dict(self) -> dict[str, Any]:
        return {
            "candidate_id": self.candidate_id,
            "family": self.family,
            "parameters": dict(self.parameters),
        }


@dataclass(frozen=True, slots=True)
class SF2ResearchProtocol:
    phase_id: str
    source_phase: str
    planned_candidate_budget: int
    warmup_bars: int
    corpus: M5DevelopmentCorpusSpec
    candidates: tuple[SF2Candidate, ...]

    @property
    def protocol_id(self) -> str:
        identity = {
            "schema": PROTOCOL_SCHEMA,
            "phase_id": self.phase_id,
            "source_phase": self.source_phase,
            "planned_candidate_budget": self.planned_candidate_budget,
            "warmup_bars": self.warmup_bars,
            "corpus": self.corpus.as_dict(),
            "candidates": [candidate.as_dict() for candidate in self.candidates],
        }
        return f"sf2protocol_{sha256_text(canonical_json(identity))[:24]}"


def _ranges_overlap(start_a: int, end_a: int, start_b: int, end_b: int) -> bool:
    return start_a < end_b and end_a > start_b


def _number(value: Any, *, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{name} must be numeric")
    result = float(value)
    if result != result or result in (float("inf"), float("-inf")):
        raise ValueError(f"{name} must be finite")
    return result


def _integer(value: Any, *, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"{name} must be an integer")
    return value


def _normalize_candidate(row: dict[str, Any]) -> SF2Candidate:
    if set(row) != {"candidate_id", "family", "parameters"}:
        raise ValueError("invalid SF2 candidate fields")
    candidate_id = str(row["candidate_id"]).strip()
    family = str(row["family"]).strip()
    raw = row["parameters"]
    if not candidate_id or not isinstance(raw, dict):
        raise ValueError("invalid SF2 candidate identity")

    if family in {"divergence_reversal_v1", "absorption_reversal_v1"}:
        if set(raw) != {"side", "signal_threshold"}:
            raise ValueError(f"invalid {family} parameters")
        side = _integer(raw["side"], name="side")
        threshold = _number(raw["signal_threshold"], name="signal_threshold")
        if side not in (-1, 1) or not 0.0 < threshold <= 1.0:
            raise ValueError(f"invalid {family} parameter values")
        parameters: dict[str, float | int] = {
            "side": side,
            "signal_threshold": threshold,
        }
    elif family == "stacked_delta_continuation_v1":
        if set(raw) != {"side", "minimum_stacked_levels", "minimum_delta_ratio"}:
            raise ValueError("invalid stacked_delta_continuation_v1 parameters")
        side = _integer(raw["side"], name="side")
        levels = _integer(raw["minimum_stacked_levels"], name="minimum_stacked_levels")
        delta = _number(raw["minimum_delta_ratio"], name="minimum_delta_ratio")
        if side not in (-1, 1) or levels < 1 or not 0.0 < delta <= 1.0:
            raise ValueError("invalid stacked_delta_continuation_v1 parameter values")
        parameters = {
            "side": side,
            "minimum_stacked_levels": levels,
            "minimum_delta_ratio": delta,
        }
    elif family == "flow_price_continuation_v1":
        if set(raw) != {"side", "minimum_delta_ratio", "minimum_price_return"}:
            raise ValueError("invalid flow_price_continuation_v1 parameters")
        side = _integer(raw["side"], name="side")
        delta = _number(raw["minimum_delta_ratio"], name="minimum_delta_ratio")
        price_return = _number(raw["minimum_price_return"], name="minimum_price_return")
        if side not in (-1, 1) or not 0.0 < delta <= 1.0 or price_return <= 0.0:
            raise ValueError("invalid flow_price_continuation_v1 parameter values")
        parameters = {
            "side": side,
            "minimum_delta_ratio": delta,
            "minimum_price_return": price_return,
        }
    else:
        raise ValueError(f"unsupported SF2 family: {family}")
    return SF2Candidate(candidate_id=candidate_id, family=family, parameters=parameters)


def _validate_fixed_contract(payload: dict[str, Any]) -> None:
    execution = payload.get("execution")
    qualification = payload.get("qualification")
    reuse = payload.get("data_reuse_policy")
    if execution != {
        "initial_cash": 10000.0,
        "fee_bps": FEE_BPS,
        "slippage_bps": SLIPPAGE_BPS,
        "signal_to_execution_delay_bars": SIGNAL_TO_EXECUTION_DELAY_BARS,
        "max_hold_bars": MAX_HOLD_BARS,
        "minimum_hold_bars": MINIMUM_HOLD_BARS,
    }:
        raise ValueError("SF2 execution contract was changed")
    if qualification != {
        "minimum_mean_return_exclusive": 0.0,
        "minimum_mean_expectancy_exclusive": 0.0,
        "minimum_total_trades": MINIMUM_TOTAL_TRADES,
        "minimum_baseline_beating_windows": MINIMUM_BASELINE_BEATING_WINDOWS,
        "adjusted_alpha_max": ADJUSTED_ALPHA_MAX,
        "multiple_testing_method": "bonferroni",
        "permutation_count": PERMUTATION_COUNT,
    }:
        raise ValueError("SF2 qualification gate was changed")
    if reuse != {
        "sf1_development_windows_reused": False,
        "original_2026_08_01_smoke_window_reused": False,
        "frozen_oos_allowed": False,
        "fresh_development_required": True,
    }:
        raise ValueError("SF2 fresh-data contract was changed")


def _load_windows(rows: Any) -> M5DevelopmentCorpusSpec:
    if not isinstance(rows, list) or len(rows) != EXPECTED_WINDOW_COUNT:
        raise ValueError("SF2 requires exactly 12 fresh development windows")
    windows: list[M5StudyWindow] = []
    for row in rows:
        if not isinstance(row, dict) or set(row) != {"name", "start", "end"}:
            raise ValueError("invalid SF2 development window")
        window = M5StudyWindow(
            name=str(row["name"]),
            start_ms=parse_utc(str(row["start"])),
            end_ms=parse_utc(str(row["end"])),
        )
        if window.end_ms - window.start_ms != EXPECTED_WINDOW_DURATION_MS:
            raise ValueError("SF2 development windows must each be exactly four hours")
        for sf1_window in DEFAULT_M5_DEVELOPMENT_CORPUS.windows:
            if _ranges_overlap(
                window.start_ms,
                window.end_ms,
                sf1_window.start_ms,
                sf1_window.end_ms,
            ):
                raise ValueError("SF2 development window reuses SF1 evidence")
        if _ranges_overlap(
            window.start_ms,
            window.end_ms,
            ORIGINAL_SMOKE_DAY_START_MS,
            ORIGINAL_SMOKE_DAY_END_MS,
        ):
            raise ValueError("SF2 development window reuses the original smoke day")
        windows.append(window)
    return M5DevelopmentCorpusSpec(
        policy_id=DEFAULT_M5_STUDY_POLICY.policy_id,
        windows=tuple(windows),
    )


def load_sf2_protocol(path: str | Path) -> SF2ResearchProtocol:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("SF2 protocol must be a JSON object")
    required = {
        "schema",
        "phase_id",
        "source_phase",
        "symbol",
        "venue",
        "interval",
        "planned_candidate_budget",
        "active_candidate_count",
        "warmup_bars",
        "execution",
        "qualification",
        "data_reuse_policy",
        "development_windows",
        "candidates",
    }
    if set(payload) != required:
        raise ValueError("invalid SF2 protocol fields")
    if payload["schema"] != PROTOCOL_SCHEMA or payload["phase_id"] != PHASE_ID:
        raise ValueError("unsupported SF2 protocol identity")
    if payload["source_phase"] != SOURCE_PHASE:
        raise ValueError("SF2 source phase mismatch")
    policy = DEFAULT_M5_STUDY_POLICY
    if (
        payload["symbol"] != policy.symbol
        or payload["venue"] != policy.venue
        or payload["interval"] != policy.interval
    ):
        raise ValueError("SF2 market identity must match the sealed M5 policy")
    if payload["planned_candidate_budget"] != PLANNED_MULTIPLE_TESTING_BUDGET:
        raise ValueError("SF2 multiple-testing budget must remain 48")
    if payload["active_candidate_count"] != ACTIVE_CANDIDATE_COUNT:
        raise ValueError("SF2 active candidate count must remain 24")
    if payload["warmup_bars"] != WARMUP_BARS:
        raise ValueError("SF2 warmup bars must remain 64")
    _validate_fixed_contract(payload)
    corpus = _load_windows(payload["development_windows"])

    rows = payload["candidates"]
    if not isinstance(rows, list) or len(rows) != ACTIVE_CANDIDATE_COUNT:
        raise ValueError("SF2 requires exactly 24 preregistered candidates")
    candidates = tuple(_normalize_candidate(row) for row in rows if isinstance(row, dict))
    if len(candidates) != len(rows):
        raise ValueError("invalid SF2 candidate entry")
    ids = [candidate.candidate_id for candidate in candidates]
    if len(ids) != len(set(ids)):
        raise ValueError("SF2 candidate IDs must be unique")
    fingerprints = [
        canonical_json({"family": candidate.family, "parameters": candidate.parameters})
        for candidate in candidates
    ]
    if len(fingerprints) != len(set(fingerprints)):
        raise ValueError("SF2 candidate configurations must be unique")
    families: dict[str, int] = {}
    for candidate in candidates:
        families[candidate.family] = families.get(candidate.family, 0) + 1
    if families != {
        "divergence_reversal_v1": 6,
        "absorption_reversal_v1": 6,
        "stacked_delta_continuation_v1": 6,
        "flow_price_continuation_v1": 6,
    }:
        raise ValueError("SF2 family allocation must remain 6+6+6+6")

    return SF2ResearchProtocol(
        phase_id=PHASE_ID,
        source_phase=SOURCE_PHASE,
        planned_candidate_budget=PLANNED_MULTIPLE_TESTING_BUDGET,
        warmup_bars=WARMUP_BARS,
        corpus=corpus,
        candidates=candidates,
    )
