from __future__ import annotations

import json
import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from enum import StrEnum
from typing import Any

from .research_evidence import canonical_json, sha256_text
from .research_store import ResearchStore

DISCOVERY_AUTHORITY = "DISCOVERY_ONLY"
MAX_RAW_CANDIDATES = 500
MAX_CANDIDATES_PER_FAMILY = 64
MAX_SURVIVORS = 30


class DiscoveryTrialStatus(StrEnum):
    DECLARED = "declared"
    EVALUATED = "evaluated"
    REJECTED = "rejected"
    SURVIVOR = "survivor"


@dataclass(frozen=True, slots=True)
class DiscoveryCampaignPolicy:
    campaign_id: str
    raw_candidate_cap: int = MAX_RAW_CANDIDATES
    candidate_cap_per_family: int = MAX_CANDIDATES_PER_FAMILY
    survivor_cap: int = MAX_SURVIVORS
    authority: str = DISCOVERY_AUTHORITY

    def __post_init__(self) -> None:
        if not self.campaign_id.strip():
            raise ValueError("campaign_id is required")
        if self.authority != DISCOVERY_AUTHORITY:
            raise ValueError("strategy discovery v2 must remain DISCOVERY_ONLY")
        if not 1 <= self.raw_candidate_cap <= MAX_RAW_CANDIDATES:
            raise ValueError(f"raw_candidate_cap must be between 1 and {MAX_RAW_CANDIDATES}")
        if not 1 <= self.candidate_cap_per_family <= MAX_CANDIDATES_PER_FAMILY:
            raise ValueError(
                "candidate_cap_per_family must be between 1 and "
                f"{MAX_CANDIDATES_PER_FAMILY}"
            )
        if not 1 <= self.survivor_cap <= MAX_SURVIVORS:
            raise ValueError(f"survivor_cap must be between 1 and {MAX_SURVIVORS}")
        if self.survivor_cap > self.raw_candidate_cap:
            raise ValueError("survivor_cap cannot exceed raw_candidate_cap")

    def as_dict(self) -> dict[str, object]:
        return {
            "authority": self.authority,
            "campaign_id": self.campaign_id,
            "candidate_cap_per_family": self.candidate_cap_per_family,
            "raw_candidate_cap": self.raw_candidate_cap,
            "survivor_cap": self.survivor_cap,
        }


@dataclass(frozen=True, slots=True)
class DiscoveryCandidate:
    family_id: str
    hypothesis_fingerprint: str
    parameters: Mapping[str, object]

    def __post_init__(self) -> None:
        if not self.family_id.strip():
            raise ValueError("family_id is required")
        if not self.hypothesis_fingerprint.strip():
            raise ValueError("hypothesis_fingerprint is required")
        canonical_json(dict(self.parameters))

    @property
    def specification(self) -> dict[str, object]:
        return {
            "family_id": self.family_id,
            "hypothesis_fingerprint": self.hypothesis_fingerprint,
            "parameters": dict(self.parameters),
        }

    @property
    def specification_sha256(self) -> str:
        return sha256_text(canonical_json(self.specification))

    @property
    def candidate_id(self) -> str:
        return f"dc_{self.specification_sha256[:24]}"


@dataclass(frozen=True, slots=True)
class BehavioralFingerprint:
    signal_keys: tuple[str, ...]
    trade_keys: tuple[str, ...]
    regime_returns: tuple[float, ...]
    exposure_fraction: float
    turnover: float

    def __post_init__(self) -> None:
        if self.signal_keys != tuple(sorted(set(self.signal_keys))):
            raise ValueError("signal_keys must be sorted and unique")
        if self.trade_keys != tuple(sorted(set(self.trade_keys))):
            raise ValueError("trade_keys must be sorted and unique")
        if not self.regime_returns:
            raise ValueError("regime_returns cannot be empty")
        if not all(math.isfinite(value) for value in self.regime_returns):
            raise ValueError("regime_returns must be finite")
        if not 0.0 <= self.exposure_fraction <= 1.0:
            raise ValueError("exposure_fraction must be between 0 and 1")
        if not math.isfinite(self.turnover) or self.turnover < 0.0:
            raise ValueError("turnover must be finite and non-negative")

    def as_dict(self) -> dict[str, object]:
        return {
            "exposure_fraction": self.exposure_fraction,
            "regime_returns": list(self.regime_returns),
            "signal_keys": list(self.signal_keys),
            "trade_keys": list(self.trade_keys),
            "turnover": self.turnover,
        }


@dataclass(frozen=True, slots=True)
class BehavioralSimilarity:
    score: float
    signal_overlap: float
    trade_overlap: float
    regime_similarity: float
    exposure_similarity: float
    turnover_similarity: float
    near_duplicate: bool


def behavioral_similarity(
    left: BehavioralFingerprint,
    right: BehavioralFingerprint,
    *,
    threshold: float = 0.90,
) -> BehavioralSimilarity:
    if not 0.0 <= threshold <= 1.0:
        raise ValueError("threshold must be between 0 and 1")
    if len(left.regime_returns) != len(right.regime_returns):
        raise ValueError("regime return vectors must have the same length")

    signal_overlap = _jaccard(left.signal_keys, right.signal_keys)
    trade_overlap = _jaccard(left.trade_keys, right.trade_keys)
    regime_similarity = _pearson_similarity(left.regime_returns, right.regime_returns)
    exposure_similarity = 1.0 - abs(left.exposure_fraction - right.exposure_fraction)
    turnover_similarity = _ratio_similarity(left.turnover, right.turnover)
    score = (
        0.35 * signal_overlap
        + 0.35 * trade_overlap
        + 0.20 * regime_similarity
        + 0.05 * exposure_similarity
        + 0.05 * turnover_similarity
    )
    score = min(1.0, max(0.0, score))
    return BehavioralSimilarity(
        score=score,
        signal_overlap=signal_overlap,
        trade_overlap=trade_overlap,
        regime_similarity=regime_similarity,
        exposure_similarity=exposure_similarity,
        turnover_similarity=turnover_similarity,
        near_duplicate=score >= threshold,
    )


def select_behavioral_representatives(
    fingerprints: Mapping[str, BehavioralFingerprint],
    *,
    threshold: float = 0.90,
) -> tuple[str, ...]:
    kept: list[str] = []
    for candidate_id in sorted(fingerprints):
        fingerprint = fingerprints[candidate_id]
        if any(
            behavioral_similarity(fingerprint, fingerprints[existing], threshold=threshold)
            .near_duplicate
            for existing in kept
        ):
            continue
        kept.append(candidate_id)
    return tuple(kept)


class DiscoveryTrialLedger:
    """Immutable-audit ledger for non-authoritative mass discovery trials.

    This ledger deliberately has no method that changes StrategyLifecycle. A survivor only
    earns the right to enter a later hidden-confirmation workflow; it is never verified here.
    """

    def __init__(self, store: ResearchStore) -> None:
        self.store = store
        self._initialize()

    def _initialize(self) -> None:
        with self.store._connection() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS discovery_campaigns_v2 (
                    campaign_id TEXT PRIMARY KEY,
                    authority TEXT NOT NULL CHECK(authority = 'DISCOVERY_ONLY'),
                    raw_candidate_cap INTEGER NOT NULL,
                    candidate_cap_per_family INTEGER NOT NULL,
                    survivor_cap INTEGER NOT NULL,
                    definition_sha256 TEXT NOT NULL,
                    definition_json TEXT NOT NULL,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                );

                CREATE TABLE IF NOT EXISTS discovery_trials_v2 (
                    trial_id TEXT PRIMARY KEY,
                    campaign_id TEXT NOT NULL,
                    candidate_id TEXT NOT NULL,
                    family_id TEXT NOT NULL,
                    candidate_spec_sha256 TEXT NOT NULL,
                    candidate_spec_json TEXT NOT NULL,
                    dataset_sha256 TEXT NOT NULL,
                    source_code_sha TEXT NOT NULL,
                    search_round INTEGER NOT NULL CHECK(search_round >= 0),
                    status TEXT NOT NULL,
                    metrics_json TEXT NOT NULL DEFAULT '{}',
                    behavior_json TEXT,
                    rejection_reason TEXT,
                    compute_ms INTEGER CHECK(compute_ms IS NULL OR compute_ms >= 0),
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY(campaign_id) REFERENCES discovery_campaigns_v2(campaign_id)
                        ON DELETE RESTRICT,
                    UNIQUE(campaign_id, candidate_id, dataset_sha256)
                );

                CREATE INDEX IF NOT EXISTS idx_discovery_trials_campaign
                    ON discovery_trials_v2(campaign_id, status, family_id, candidate_id);
                """
            )

    def register_campaign(
        self,
        policy: DiscoveryCampaignPolicy,
        *,
        definition: Mapping[str, object],
    ) -> None:
        payload = {
            "definition": dict(definition),
            "policy": policy.as_dict(),
        }
        definition_json = canonical_json(payload)
        definition_sha256 = sha256_text(definition_json)
        with self.store._connection() as connection:
            row = connection.execute(
                "SELECT * FROM discovery_campaigns_v2 WHERE campaign_id = ?",
                (policy.campaign_id,),
            ).fetchone()
            if row is not None:
                if row["definition_sha256"] != definition_sha256:
                    raise ValueError("discovery campaign definition is immutable")
                return
            connection.execute(
                """
                INSERT INTO discovery_campaigns_v2(
                    campaign_id, authority, raw_candidate_cap, candidate_cap_per_family,
                    survivor_cap, definition_sha256, definition_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    policy.campaign_id,
                    policy.authority,
                    policy.raw_candidate_cap,
                    policy.candidate_cap_per_family,
                    policy.survivor_cap,
                    definition_sha256,
                    definition_json,
                ),
            )

    def declare_trial(
        self,
        *,
        campaign_id: str,
        candidate: DiscoveryCandidate,
        dataset_sha256: str,
        source_code_sha: str,
        search_round: int,
    ) -> str:
        dataset_sha256 = _required_token(dataset_sha256, "dataset_sha256")
        source_code_sha = _required_token(source_code_sha, "source_code_sha")
        if search_round < 0:
            raise ValueError("search_round must be non-negative")
        trial_payload = {
            "campaign_id": campaign_id,
            "candidate_id": candidate.candidate_id,
            "dataset_sha256": dataset_sha256,
        }
        trial_id = f"dtrial_{sha256_text(canonical_json(trial_payload))[:24]}"
        candidate_json = canonical_json(candidate.specification)

        with self.store._connection() as connection:
            campaign = connection.execute(
                "SELECT * FROM discovery_campaigns_v2 WHERE campaign_id = ?",
                (campaign_id,),
            ).fetchone()
            if campaign is None:
                raise KeyError(f"unknown discovery campaign: {campaign_id}")
            existing = connection.execute(
                "SELECT * FROM discovery_trials_v2 WHERE trial_id = ?",
                (trial_id,),
            ).fetchone()
            if existing is not None:
                if (
                    existing["candidate_spec_sha256"] != candidate.specification_sha256
                    or existing["source_code_sha"] != source_code_sha
                ):
                    raise RuntimeError("immutable discovery trial collision")
                return trial_id

            total = connection.execute(
                "SELECT COUNT(*) AS n FROM discovery_trials_v2 WHERE campaign_id = ?",
                (campaign_id,),
            ).fetchone()["n"]
            if int(total) >= int(campaign["raw_candidate_cap"]):
                raise RuntimeError("discovery campaign raw candidate cap reached")
            family_total = connection.execute(
                """
                SELECT COUNT(*) AS n FROM discovery_trials_v2
                WHERE campaign_id = ? AND family_id = ?
                """,
                (campaign_id, candidate.family_id),
            ).fetchone()["n"]
            if int(family_total) >= int(campaign["candidate_cap_per_family"]):
                raise RuntimeError("discovery campaign per-family candidate cap reached")

            connection.execute(
                """
                INSERT INTO discovery_trials_v2(
                    trial_id, campaign_id, candidate_id, family_id,
                    candidate_spec_sha256, candidate_spec_json, dataset_sha256,
                    source_code_sha, search_round, status
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    trial_id,
                    campaign_id,
                    candidate.candidate_id,
                    candidate.family_id,
                    candidate.specification_sha256,
                    candidate_json,
                    dataset_sha256,
                    source_code_sha,
                    search_round,
                    DiscoveryTrialStatus.DECLARED.value,
                ),
            )
        return trial_id

    def record_result(
        self,
        *,
        trial_id: str,
        status: DiscoveryTrialStatus,
        metrics: Mapping[str, object],
        behavior: BehavioralFingerprint | None = None,
        rejection_reason: str | None = None,
        compute_ms: int | None = None,
    ) -> None:
        if status is DiscoveryTrialStatus.DECLARED:
            raise ValueError("record_result requires a terminal discovery evaluation status")
        if compute_ms is not None and compute_ms < 0:
            raise ValueError("compute_ms must be non-negative")
        if status is DiscoveryTrialStatus.REJECTED and not (rejection_reason or "").strip():
            raise ValueError("rejected discovery trial requires rejection_reason")
        metrics_json = canonical_json(dict(metrics))
        behavior_json = canonical_json(behavior.as_dict()) if behavior is not None else None

        with self.store._connection() as connection:
            row = connection.execute(
                "SELECT * FROM discovery_trials_v2 WHERE trial_id = ?",
                (trial_id,),
            ).fetchone()
            if row is None:
                raise KeyError(f"unknown discovery trial: {trial_id}")
            if row["status"] != DiscoveryTrialStatus.DECLARED.value:
                same = (
                    row["status"] == status.value
                    and row["metrics_json"] == metrics_json
                    and row["behavior_json"] == behavior_json
                    and (row["rejection_reason"] or None) == (rejection_reason or None)
                    and row["compute_ms"] == compute_ms
                )
                if same:
                    return
                raise RuntimeError("discovery trial result is immutable")

            if status is DiscoveryTrialStatus.SURVIVOR:
                campaign = connection.execute(
                    """
                    SELECT c.survivor_cap,
                           SUM(CASE WHEN t.status = 'survivor' THEN 1 ELSE 0 END) AS survivors
                    FROM discovery_campaigns_v2 AS c
                    LEFT JOIN discovery_trials_v2 AS t USING(campaign_id)
                    WHERE c.campaign_id = ?
                    GROUP BY c.campaign_id
                    """,
                    (row["campaign_id"],),
                ).fetchone()
                if campaign is None:
                    raise RuntimeError("discovery campaign disappeared")
                if int(campaign["survivors"] or 0) >= int(campaign["survivor_cap"]):
                    raise RuntimeError("discovery campaign survivor cap reached")

            connection.execute(
                """
                UPDATE discovery_trials_v2
                SET status = ?, metrics_json = ?, behavior_json = ?,
                    rejection_reason = ?, compute_ms = ?, updated_at = CURRENT_TIMESTAMP
                WHERE trial_id = ?
                """,
                (
                    status.value,
                    metrics_json,
                    behavior_json,
                    rejection_reason,
                    compute_ms,
                    trial_id,
                ),
            )

    def list_trials(self, campaign_id: str) -> list[dict[str, Any]]:
        with self.store._connection() as connection:
            rows = connection.execute(
                """
                SELECT * FROM discovery_trials_v2
                WHERE campaign_id = ?
                ORDER BY search_round, family_id, candidate_id
                """,
                (campaign_id,),
            ).fetchall()
        output: list[dict[str, Any]] = []
        for row in rows:
            item = dict(row)
            item["candidate_spec"] = json.loads(item.pop("candidate_spec_json"))
            item["metrics"] = json.loads(item.pop("metrics_json"))
            behavior_json = item.pop("behavior_json")
            item["behavior"] = json.loads(behavior_json) if behavior_json else None
            output.append(item)
        return output


def _required_token(value: str, name: str) -> str:
    value = value.strip()
    if not value:
        raise ValueError(f"{name} is required")
    return value


def _jaccard(left: Sequence[str], right: Sequence[str]) -> float:
    left_set = set(left)
    right_set = set(right)
    union = left_set | right_set
    if not union:
        return 1.0
    return len(left_set & right_set) / len(union)


def _pearson_similarity(left: Sequence[float], right: Sequence[float]) -> float:
    if tuple(left) == tuple(right):
        return 1.0
    left_mean = sum(left) / len(left)
    right_mean = sum(right) / len(right)
    left_centered = [value - left_mean for value in left]
    right_centered = [value - right_mean for value in right]
    left_norm = math.sqrt(sum(value * value for value in left_centered))
    right_norm = math.sqrt(sum(value * value for value in right_centered))
    if left_norm == 0.0 or right_norm == 0.0:
        return 0.0
    correlation = sum(
        left_value * right_value
        for left_value, right_value in zip(left_centered, right_centered, strict=True)
    ) / (left_norm * right_norm)
    return min(1.0, max(0.0, (correlation + 1.0) / 2.0))


def _ratio_similarity(left: float, right: float) -> float:
    if left == right:
        return 1.0
    maximum = max(left, right)
    if maximum == 0.0:
        return 1.0
    return min(left, right) / maximum
