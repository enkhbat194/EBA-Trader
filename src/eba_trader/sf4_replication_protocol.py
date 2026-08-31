from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .history import parse_utc
from .m5_study_policy import M5StudyWindow
from .research_evidence import canonical_json, sha256_text
from .sf3_protocol import SF3Candidate

PROTOCOL_SCHEMA = "sf4_two_hypothesis_replication_v1"
PHASE_ID = "sf4_prospective_replication_v1"
AUTHORITY = "HYPOTHESIS_REPLICATION_ONLY"
SOURCE_PHASE = "sf3_fresh_development_v1"
SOURCE_VALIDATION_STATE = "NO_VERIFIED_CANDIDATE"
SYMBOL = "BTCUSDT"
VENUE = "usd_m_futures"
INTERVAL = "1m"
WARMUP_BARS = 96
PLANNED_MULTIPLE_TESTING_BUDGET = 48
EXPECTED_WINDOW_COUNT = 12
EXPECTED_WINDOW_DURATION_MS = 24 * 60 * 60 * 1000
PROSPECTIVE_START_MS = parse_utc("2026-09-01T00:00:00Z")
EVALUATION_NOT_BEFORE_MS = parse_utc("2026-09-13T00:00:00Z")
FEE_BPS = 4.0
SLIPPAGE_BPS = 1.5
SIGNAL_TO_EXECUTION_DELAY_BARS = 1
MAX_HOLD_BARS = 30
MINIMUM_HOLD_BARS = 4
MINIMUM_TOTAL_TRADES = 30
MINIMUM_BASELINE_BEATING_WINDOWS = 9
ADJUSTED_ALPHA_MAX = 0.05
PERMUTATION_COUNT = 4096

_EXPECTED_EXECUTION = {
    "initial_cash": 10000.0,
    "fee_bps": FEE_BPS,
    "slippage_bps": SLIPPAGE_BPS,
    "signal_to_execution_delay_bars": SIGNAL_TO_EXECUTION_DELAY_BARS,
    "max_hold_bars": MAX_HOLD_BARS,
    "minimum_hold_bars": MINIMUM_HOLD_BARS,
}

_EXPECTED_QUALIFICATION = {
    "minimum_mean_return_exclusive": 0.0,
    "minimum_mean_expectancy_exclusive": 0.0,
    "minimum_total_trades": MINIMUM_TOTAL_TRADES,
    "minimum_baseline_beating_windows": MINIMUM_BASELINE_BEATING_WINDOWS,
    "require_positive_mean_return_delta_vs_baseline": True,
    "adjusted_alpha_max": ADJUSTED_ALPHA_MAX,
    "multiple_testing_method": "bonferroni",
    "permutation_count": PERMUTATION_COUNT,
}

_EXPECTED_SAFETY = {
    "development_evidence_only": True,
    "edge_claim_allowed": False,
    "promotion_authority": False,
    "frozen_oos_allowed": False,
    "demo_promotion_allowed": False,
    "live_execution_allowed": False,
    "real_execution_allowed": False,
}

_EXPECTED_SELECTION_BIAS_CONTROL = {
    "reason": "The two hypotheses were selected after inspecting SF3 development evidence.",
    "sf3_search_budget_carried_forward": 48,
    "replication_must_pass_on_new_data_alone": True,
    "sf3_trade_count_may_not_be_added_to_replication_trade_count": True,
    "sf3_p_value_may_not_be_combined_with_replication_p_value": True,
}

_EXPECTED_CANDIDATES: tuple[dict[str, Any], ...] = (
    {
        "candidate_id": "s4_vsm_s150_replication",
        "source_candidate_id": "s3_vsm_s150",
        "family": "volume_shock_momentum_v1",
        "parameters": {
            "side": -1,
            "lookback": 30,
            "volume_multiple": 1.5,
            "minimum_price_return": 0.001,
        },
    },
    {
        "candidate_id": "s4_cex_s075_replication",
        "source_candidate_id": "s3_cex_s075",
        "family": "compression_expansion_v1",
        "parameters": {
            "side": -1,
            "short_lookback": 8,
            "long_lookback": 32,
            "compression_ratio_max": 0.75,
            "minimum_price_return": 0.001,
        },
    },
)


@dataclass(frozen=True, slots=True)
class SF4ReplicationCandidate:
    candidate_id: str
    source_candidate_id: str
    family: str
    parameters: dict[str, float | int]

    def as_sf3_candidate(self) -> SF3Candidate:
        return SF3Candidate(
            candidate_id=self.candidate_id,
            family=self.family,
            parameters=dict(self.parameters),
        )

    def as_dict(self) -> dict[str, Any]:
        return {
            "candidate_id": self.candidate_id,
            "source_candidate_id": self.source_candidate_id,
            "family": self.family,
            "parameters": dict(self.parameters),
        }


@dataclass(frozen=True, slots=True)
class SF4ReplicationCorpusSpec:
    corpus_id: str
    symbol: str
    venue: str
    interval: str
    windows: tuple[M5StudyWindow, ...]

    def __post_init__(self) -> None:
        if self.corpus_id != "sf4_prospective_replication_v1":
            raise ValueError("SF4 prospective corpus identity changed")
        if (self.symbol, self.venue, self.interval) != (SYMBOL, VENUE, INTERVAL):
            raise ValueError("SF4 prospective corpus market identity changed")
        if len(self.windows) != EXPECTED_WINDOW_COUNT:
            raise ValueError("SF4 prospective corpus requires exactly 12 windows")

    def as_dict(self) -> dict[str, Any]:
        return {
            "corpus_id": self.corpus_id,
            "symbol": self.symbol,
            "venue": self.venue,
            "interval": self.interval,
            "windows": [window.as_dict() for window in self.windows],
        }


@dataclass(frozen=True, slots=True)
class SF4ReplicationProtocol:
    phase_id: str
    authority: str
    source_phase: str
    source_validation_state: str
    warmup_bars: int
    planned_multiple_testing_budget: int
    corpus: SF4ReplicationCorpusSpec
    candidates: tuple[SF4ReplicationCandidate, ...]
    evaluation_not_before_ms: int

    @property
    def protocol_id(self) -> str:
        identity = {
            "schema": PROTOCOL_SCHEMA,
            "phase_id": self.phase_id,
            "authority": self.authority,
            "source_phase": self.source_phase,
            "source_validation_state": self.source_validation_state,
            "warmup_bars": self.warmup_bars,
            "planned_multiple_testing_budget": self.planned_multiple_testing_budget,
            "corpus": self.corpus.as_dict(),
            "candidates": [candidate.as_dict() for candidate in self.candidates],
            "evaluation_not_before_ms": self.evaluation_not_before_ms,
        }
        return f"sf4rep_{sha256_text(canonical_json(identity))[:24]}"

    def assert_evaluation_time(self, now_ms: int) -> None:
        if isinstance(now_ms, bool) or not isinstance(now_ms, int):
            raise TypeError("now_ms must be an integer UTC epoch millisecond value")
        if now_ms < self.evaluation_not_before_ms:
            raise RuntimeError(
                "SF4 replication cannot be evaluated before all prospective windows close"
            )


def _load_candidate(row: Any, expected: dict[str, Any]) -> SF4ReplicationCandidate:
    if not isinstance(row, dict) or row != expected:
        raise ValueError("SF4 replication candidate contract changed")
    parameters = row["parameters"]
    return SF4ReplicationCandidate(
        candidate_id=str(row["candidate_id"]),
        source_candidate_id=str(row["source_candidate_id"]),
        family=str(row["family"]),
        parameters=dict(parameters),
    )


def _load_windows(rows: Any) -> SF4ReplicationCorpusSpec:
    if not isinstance(rows, list) or len(rows) != EXPECTED_WINDOW_COUNT:
        raise ValueError("SF4 replication requires exactly 12 prospective windows")
    windows: list[M5StudyWindow] = []
    previous_end: int | None = None
    for index, row in enumerate(rows, start=1):
        if not isinstance(row, dict) or set(row) != {"name", "start", "end"}:
            raise ValueError("invalid SF4 replication window")
        expected_name = f"sf4-rep-{index:02d}"
        if row["name"] != expected_name:
            raise ValueError("SF4 replication window identity changed")
        window = M5StudyWindow(
            name=expected_name,
            start_ms=parse_utc(str(row["start"])),
            end_ms=parse_utc(str(row["end"])),
        )
        if window.end_ms - window.start_ms != EXPECTED_WINDOW_DURATION_MS:
            raise ValueError("SF4 replication windows must each be exactly 24 hours")
        if window.start_ms < PROSPECTIVE_START_MS:
            raise ValueError("SF4 replication cannot reuse pre-preregistered evidence")
        if previous_end is not None and window.start_ms != previous_end:
            raise ValueError("SF4 replication windows must be contiguous and non-overlapping")
        previous_end = window.end_ms
        windows.append(window)
    if windows[0].start_ms != PROSPECTIVE_START_MS:
        raise ValueError("SF4 replication start time changed")
    if windows[-1].end_ms != EVALUATION_NOT_BEFORE_MS:
        raise ValueError("SF4 replication end time changed")
    return SF4ReplicationCorpusSpec(
        corpus_id="sf4_prospective_replication_v1",
        symbol=SYMBOL,
        venue=VENUE,
        interval=INTERVAL,
        windows=tuple(windows),
    )


def load_sf4_replication_protocol(path: str | Path) -> SF4ReplicationProtocol:
    try:
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError("cannot read SF4 replication protocol") from exc
    if not isinstance(payload, dict):
        raise ValueError("SF4 replication protocol must be a JSON object")

    required = {
        "schema",
        "phase_id",
        "authority",
        "source_phase",
        "source_validation_state",
        "symbol",
        "venue",
        "interval",
        "warmup_bars",
        "prospective_only",
        "parameter_tuning_allowed",
        "combine_with_sf3_for_qualification",
        "planned_multiple_testing_budget",
        "execution",
        "qualification",
        "safety",
        "selection_bias_control",
        "candidates",
        "replication_windows",
        "evaluation_not_before",
    }
    if set(payload) != required:
        raise ValueError("SF4 replication protocol fields changed")
    if payload["schema"] != PROTOCOL_SCHEMA:
        raise ValueError("unsupported SF4 replication protocol schema")
    if payload["phase_id"] != PHASE_ID or payload["authority"] != AUTHORITY:
        raise ValueError("SF4 replication identity changed")
    if payload["source_phase"] != SOURCE_PHASE:
        raise ValueError("SF4 replication source phase changed")
    if payload["source_validation_state"] != SOURCE_VALIDATION_STATE:
        raise ValueError("SF4 must remain a follow-up to a failed SF3 verification phase")
    if (payload["symbol"], payload["venue"], payload["interval"]) != (SYMBOL, VENUE, INTERVAL):
        raise ValueError("SF4 market-data identity changed")
    if payload["warmup_bars"] != WARMUP_BARS:
        raise ValueError("SF4 warmup changed")
    if payload["prospective_only"] is not True:
        raise ValueError("SF4 replication must remain prospective-only")
    if payload["parameter_tuning_allowed"] is not False:
        raise ValueError("SF4 replication cannot retune selected hypotheses")
    if payload["combine_with_sf3_for_qualification"] is not False:
        raise ValueError("SF4 replication must pass on new evidence alone")
    if payload["planned_multiple_testing_budget"] != PLANNED_MULTIPLE_TESTING_BUDGET:
        raise ValueError("SF4 must carry forward the conservative SF3 search budget")
    if payload["execution"] != _EXPECTED_EXECUTION:
        raise ValueError("SF4 execution contract changed")
    if payload["qualification"] != _EXPECTED_QUALIFICATION:
        raise ValueError("SF4 qualification gate changed")
    if payload["safety"] != _EXPECTED_SAFETY:
        raise ValueError("SF4 safety locks changed")
    if payload["selection_bias_control"] != _EXPECTED_SELECTION_BIAS_CONTROL:
        raise ValueError("SF4 selection-bias controls changed")

    raw_candidates = payload["candidates"]
    if not isinstance(raw_candidates, list) or len(raw_candidates) != len(_EXPECTED_CANDIDATES):
        raise ValueError("SF4 must contain exactly two frozen hypotheses")
    candidates = tuple(
        _load_candidate(row, expected)
        for row, expected in zip(raw_candidates, _EXPECTED_CANDIDATES, strict=True)
    )
    corpus = _load_windows(payload["replication_windows"])
    evaluation_not_before_ms = parse_utc(str(payload["evaluation_not_before"]))
    if evaluation_not_before_ms != EVALUATION_NOT_BEFORE_MS:
        raise ValueError("SF4 evaluation-not-before time changed")

    return SF4ReplicationProtocol(
        phase_id=PHASE_ID,
        authority=AUTHORITY,
        source_phase=SOURCE_PHASE,
        source_validation_state=SOURCE_VALIDATION_STATE,
        warmup_bars=WARMUP_BARS,
        planned_multiple_testing_budget=PLANNED_MULTIPLE_TESTING_BUDGET,
        corpus=corpus,
        candidates=candidates,
        evaluation_not_before_ms=evaluation_not_before_ms,
    )
