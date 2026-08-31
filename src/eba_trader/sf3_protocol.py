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
from .sf2_protocol import SF2ResearchProtocol, load_sf2_protocol

PROTOCOL_SCHEMA = "sf3_research_protocol_v1"
PHASE_ID = "sf3_fresh_development_v1"
SOURCE_PHASE = "sf2_fresh_development_v1"
PLANNED_MULTIPLE_TESTING_BUDGET = 48
ACTIVE_CANDIDATE_COUNT = 24
WARMUP_BARS = 96
EXPECTED_WINDOW_COUNT = 12
EXPECTED_WINDOW_DURATION_MS = 4 * 60 * 60 * 1000
FEE_BPS = 4.0
SLIPPAGE_BPS = 1.5
SIGNAL_TO_EXECUTION_DELAY_BARS = 1
MINIMUM_HOLD_BARS = 4
MAX_HOLD_BARS = 30
MINIMUM_TOTAL_TRADES = 30
MINIMUM_BASELINE_BEATING_WINDOWS = 9
ADJUSTED_ALPHA_MAX = 0.05
PERMUTATION_COUNT = 4096
ORIGINAL_SMOKE_DAY_START_MS = parse_utc("2026-08-01T00:00:00Z")
ORIGINAL_SMOKE_DAY_END_MS = parse_utc("2026-08-02T00:00:00Z")


@dataclass(frozen=True, slots=True)
class SF3Candidate:
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
class SF3ResearchProtocol:
    phase_id: str
    source_phase: str
    planned_candidate_budget: int
    warmup_bars: int
    corpus: M5DevelopmentCorpusSpec
    candidates: tuple[SF3Candidate, ...]

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
        return f"sf3protocol_{sha256_text(canonical_json(identity))[:24]}"


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


def _side(raw: dict[str, Any]) -> int:
    value = _integer(raw["side"], name="side")
    if value not in (-1, 1):
        raise ValueError("side must be -1 or 1")
    return value


def _normalize_candidate(row: dict[str, Any]) -> SF3Candidate:
    if set(row) != {"candidate_id", "family", "parameters"}:
        raise ValueError("invalid SF3 candidate fields")
    candidate_id = str(row["candidate_id"]).strip()
    family = str(row["family"]).strip()
    raw = row["parameters"]
    if not candidate_id or not isinstance(raw, dict):
        raise ValueError("invalid SF3 candidate identity")

    if family == "rolling_flow_trend_v1":
        expected = {"side", "lookback", "minimum_flow_ratio", "minimum_price_return"}
        if set(raw) != expected:
            raise ValueError("invalid rolling_flow_trend_v1 parameters")
        parameters: dict[str, float | int] = {
            "side": _side(raw),
            "lookback": _integer(raw["lookback"], name="lookback"),
            "minimum_flow_ratio": _number(raw["minimum_flow_ratio"], name="minimum_flow_ratio"),
            "minimum_price_return": _number(
                raw["minimum_price_return"], name="minimum_price_return"
            ),
        }
        if parameters["lookback"] < 2 or not 0.0 < parameters["minimum_flow_ratio"] <= 1.0:
            raise ValueError("invalid rolling_flow_trend_v1 values")
        if parameters["minimum_price_return"] <= 0.0:
            raise ValueError("invalid rolling_flow_trend_v1 price return")
    elif family == "volume_shock_momentum_v1":
        expected = {"side", "lookback", "volume_multiple", "minimum_price_return"}
        if set(raw) != expected:
            raise ValueError("invalid volume_shock_momentum_v1 parameters")
        parameters = {
            "side": _side(raw),
            "lookback": _integer(raw["lookback"], name="lookback"),
            "volume_multiple": _number(raw["volume_multiple"], name="volume_multiple"),
            "minimum_price_return": _number(
                raw["minimum_price_return"], name="minimum_price_return"
            ),
        }
        if parameters["lookback"] < 2 or parameters["volume_multiple"] <= 1.0:
            raise ValueError("invalid volume_shock_momentum_v1 values")
        if parameters["minimum_price_return"] <= 0.0:
            raise ValueError("invalid volume_shock_momentum_v1 price return")
    elif family == "vwap_reversion_flow_v1":
        expected = {
            "side",
            "lookback",
            "entry_deviation_bps",
            "minimum_reversal_delta_ratio",
        }
        if set(raw) != expected:
            raise ValueError("invalid vwap_reversion_flow_v1 parameters")
        parameters = {
            "side": _side(raw),
            "lookback": _integer(raw["lookback"], name="lookback"),
            "entry_deviation_bps": _number(
                raw["entry_deviation_bps"], name="entry_deviation_bps"
            ),
            "minimum_reversal_delta_ratio": _number(
                raw["minimum_reversal_delta_ratio"],
                name="minimum_reversal_delta_ratio",
            ),
        }
        if parameters["lookback"] < 2 or parameters["entry_deviation_bps"] <= 0.0:
            raise ValueError("invalid vwap_reversion_flow_v1 values")
        if not 0.0 < parameters["minimum_reversal_delta_ratio"] <= 1.0:
            raise ValueError("invalid vwap_reversion_flow_v1 delta ratio")
    elif family == "compression_expansion_v1":
        expected = {
            "side",
            "short_lookback",
            "long_lookback",
            "compression_ratio_max",
            "minimum_price_return",
        }
        if set(raw) != expected:
            raise ValueError("invalid compression_expansion_v1 parameters")
        parameters = {
            "side": _side(raw),
            "short_lookback": _integer(raw["short_lookback"], name="short_lookback"),
            "long_lookback": _integer(raw["long_lookback"], name="long_lookback"),
            "compression_ratio_max": _number(
                raw["compression_ratio_max"], name="compression_ratio_max"
            ),
            "minimum_price_return": _number(
                raw["minimum_price_return"], name="minimum_price_return"
            ),
        }
        if not 1 <= parameters["short_lookback"] < parameters["long_lookback"]:
            raise ValueError("invalid compression_expansion_v1 lookbacks")
        if not 0.0 < parameters["compression_ratio_max"] < 1.0:
            raise ValueError("invalid compression_expansion_v1 compression ratio")
        if parameters["minimum_price_return"] <= 0.0:
            raise ValueError("invalid compression_expansion_v1 price return")
    else:
        raise ValueError(f"unsupported SF3 family: {family}")
    return SF3Candidate(candidate_id=candidate_id, family=family, parameters=parameters)


def _validate_fixed_contract(payload: dict[str, Any]) -> None:
    if payload.get("execution") != {
        "initial_cash": 10000.0,
        "fee_bps": FEE_BPS,
        "slippage_bps": SLIPPAGE_BPS,
        "signal_to_execution_delay_bars": SIGNAL_TO_EXECUTION_DELAY_BARS,
        "max_hold_bars": MAX_HOLD_BARS,
        "minimum_hold_bars": MINIMUM_HOLD_BARS,
    }:
        raise ValueError("SF3 execution contract was changed")
    if payload.get("qualification") != {
        "minimum_mean_return_exclusive": 0.0,
        "minimum_mean_expectancy_exclusive": 0.0,
        "minimum_total_trades": MINIMUM_TOTAL_TRADES,
        "minimum_baseline_beating_windows": MINIMUM_BASELINE_BEATING_WINDOWS,
        "adjusted_alpha_max": ADJUSTED_ALPHA_MAX,
        "multiple_testing_method": "bonferroni",
        "permutation_count": PERMUTATION_COUNT,
    }:
        raise ValueError("SF3 qualification gate was changed")
    if payload.get("data_reuse_policy") != {
        "sf1_development_windows_reused": False,
        "sf2_development_windows_reused": False,
        "original_2026_08_01_smoke_window_reused": False,
        "frozen_oos_allowed": False,
        "fresh_development_required": True,
    }:
        raise ValueError("SF3 fresh-data contract was changed")


def _load_windows(rows: Any, sf2: SF2ResearchProtocol) -> M5DevelopmentCorpusSpec:
    if not isinstance(rows, list) or len(rows) != EXPECTED_WINDOW_COUNT:
        raise ValueError("SF3 requires exactly 12 fresh development windows")
    windows: list[M5StudyWindow] = []
    used = DEFAULT_M5_DEVELOPMENT_CORPUS.windows + sf2.corpus.windows
    for row in rows:
        if not isinstance(row, dict) or set(row) != {"name", "start", "end"}:
            raise ValueError("invalid SF3 development window")
        window = M5StudyWindow(
            name=str(row["name"]),
            start_ms=parse_utc(str(row["start"])),
            end_ms=parse_utc(str(row["end"])),
        )
        if window.end_ms - window.start_ms != EXPECTED_WINDOW_DURATION_MS:
            raise ValueError("SF3 development windows must each be exactly four hours")
        for prior_window in used:
            if _ranges_overlap(
                window.start_ms,
                window.end_ms,
                prior_window.start_ms,
                prior_window.end_ms,
            ):
                raise ValueError("SF3 development window reuses prior phase evidence")
        if _ranges_overlap(
            window.start_ms,
            window.end_ms,
            ORIGINAL_SMOKE_DAY_START_MS,
            ORIGINAL_SMOKE_DAY_END_MS,
        ):
            raise ValueError("SF3 development window reuses the original smoke day")
        windows.append(window)
    return M5DevelopmentCorpusSpec(
        policy_id=DEFAULT_M5_STUDY_POLICY.policy_id,
        windows=tuple(windows),
    )


def load_sf3_protocol(path: str | Path) -> SF3ResearchProtocol:
    protocol_path = Path(path)
    payload = json.loads(protocol_path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("SF3 protocol must be a JSON object")
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
        raise ValueError("invalid SF3 protocol fields")
    if payload["schema"] != PROTOCOL_SCHEMA or payload["phase_id"] != PHASE_ID:
        raise ValueError("unsupported SF3 protocol identity")
    if payload["source_phase"] != SOURCE_PHASE:
        raise ValueError("SF3 source phase mismatch")
    policy = DEFAULT_M5_STUDY_POLICY
    if (
        payload["symbol"] != policy.symbol
        or payload["venue"] != policy.venue
        or payload["interval"] != policy.interval
    ):
        raise ValueError("SF3 market identity must match the sealed M5 policy")
    if payload["planned_candidate_budget"] != PLANNED_MULTIPLE_TESTING_BUDGET:
        raise ValueError("SF3 multiple-testing budget must remain 48")
    if payload["active_candidate_count"] != ACTIVE_CANDIDATE_COUNT:
        raise ValueError("SF3 active candidate count must remain 24")
    if payload["warmup_bars"] != WARMUP_BARS:
        raise ValueError("SF3 warmup bars must remain 96")
    _validate_fixed_contract(payload)

    sf2_path = protocol_path.with_name("sf2_research_protocol_v1.json")
    sf2 = load_sf2_protocol(sf2_path)
    corpus = _load_windows(payload["development_windows"], sf2)

    rows = payload["candidates"]
    if not isinstance(rows, list) or len(rows) != ACTIVE_CANDIDATE_COUNT:
        raise ValueError("SF3 requires exactly 24 preregistered candidates")
    candidates = tuple(_normalize_candidate(row) for row in rows if isinstance(row, dict))
    if len(candidates) != len(rows):
        raise ValueError("invalid SF3 candidate entry")
    ids = [candidate.candidate_id for candidate in candidates]
    if len(ids) != len(set(ids)):
        raise ValueError("SF3 candidate IDs must be unique")
    fingerprints = [
        canonical_json({"family": candidate.family, "parameters": candidate.parameters})
        for candidate in candidates
    ]
    if len(fingerprints) != len(set(fingerprints)):
        raise ValueError("SF3 candidate configurations must be unique")
    families: dict[str, int] = {}
    for candidate in candidates:
        families[candidate.family] = families.get(candidate.family, 0) + 1
    if families != {
        "rolling_flow_trend_v1": 6,
        "volume_shock_momentum_v1": 6,
        "vwap_reversion_flow_v1": 6,
        "compression_expansion_v1": 6,
    }:
        raise ValueError("SF3 family allocation must remain 6+6+6+6")

    return SF3ResearchProtocol(
        phase_id=PHASE_ID,
        source_phase=SOURCE_PHASE,
        planned_candidate_budget=PLANNED_MULTIPLE_TESTING_BUDGET,
        warmup_bars=WARMUP_BARS,
        corpus=corpus,
        candidates=candidates,
    )
