from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from .strategy_discovery_v2 import (
    BehavioralFingerprint,
    behavioral_similarity,
    select_behavioral_representatives,
)


@dataclass(frozen=True, slots=True)
class DiscoverySelectionMetrics:
    mean_return: float
    mean_expectancy: float
    trade_count: int
    regime_coverage: float
    parameter_stability: float
    cost_resilience: float
    complexity: float

    def __post_init__(self) -> None:
        values = (
            self.mean_return,
            self.mean_expectancy,
            self.regime_coverage,
            self.parameter_stability,
            self.cost_resilience,
            self.complexity,
        )
        if not all(math.isfinite(value) for value in values):
            raise ValueError("discovery selection metrics must be finite")
        if self.trade_count < 0:
            raise ValueError("trade_count must be non-negative")
        for name, value in (
            ("regime_coverage", self.regime_coverage),
            ("parameter_stability", self.parameter_stability),
            ("cost_resilience", self.cost_resilience),
        ):
            if not 0.0 <= value <= 1.0:
                raise ValueError(f"{name} must be between 0 and 1")
        if self.complexity < 0.0:
            raise ValueError("complexity must be non-negative")


@dataclass(frozen=True, slots=True)
class DiscoveryPriorityDecision:
    economically_eligible: bool
    rejection_reasons: tuple[str, ...]
    priority_vector: tuple[float, ...]


def discovery_priority_decision(
    metrics: DiscoverySelectionMetrics,
    *,
    behavioral_novelty: float,
) -> DiscoveryPriorityDecision:
    """Return a discovery-only ordering vector, not statistical/promotion evidence."""

    if not 0.0 <= behavioral_novelty <= 1.0:
        raise ValueError("behavioral_novelty must be between 0 and 1")
    reasons: list[str] = []
    if metrics.mean_return <= 0.0:
        reasons.append("non_positive_mean_return")
    if metrics.mean_expectancy <= 0.0:
        reasons.append("non_positive_mean_expectancy")
    if metrics.trade_count <= 0:
        reasons.append("no_trades")
    eligible = not reasons

    # Lexicographic vector intentionally avoids pretending heterogeneous dimensions form a
    # calibrated probability or p-value. Economics gates first; diversity is only a later tie-break.
    priority_vector = (
        1.0 if eligible else 0.0,
        metrics.regime_coverage,
        metrics.parameter_stability,
        metrics.cost_resilience,
        behavioral_novelty,
        metrics.mean_expectancy,
        metrics.mean_return,
        float(metrics.trade_count),
        -metrics.complexity,
    )
    return DiscoveryPriorityDecision(
        economically_eligible=eligible,
        rejection_reasons=tuple(reasons),
        priority_vector=priority_vector,
    )


@dataclass(frozen=True, slots=True)
class BehavioralClusterReport:
    trial_count: int
    raw_candidate_count: int
    unique_spec_count: int
    family_count: int
    fingerprinted_candidate_count: int
    behavior_cluster_count: int
    representative_candidate_ids: tuple[str, ...]
    cluster_members: Mapping[str, tuple[str, ...]]


def build_behavioral_cluster_report(
    trials: Sequence[Mapping[str, Any]],
    fingerprints: Mapping[str, BehavioralFingerprint],
    *,
    threshold: float = 0.90,
) -> BehavioralClusterReport:
    candidate_ids = {
        str(trial.get("candidate_id") or "")
        for trial in trials
        if str(trial.get("candidate_id") or "")
    }
    spec_ids = {
        str(trial.get("candidate_spec_sha256") or "")
        for trial in trials
        if str(trial.get("candidate_spec_sha256") or "")
    }
    families = {
        str(trial.get("family_id") or "")
        for trial in trials
        if str(trial.get("family_id") or "")
    }
    relevant_fingerprints = {
        candidate_id: fingerprint
        for candidate_id, fingerprint in fingerprints.items()
        if candidate_id in candidate_ids
    }
    representatives = select_behavioral_representatives(
        relevant_fingerprints,
        threshold=threshold,
    )
    clusters: dict[str, list[str]] = {candidate_id: [] for candidate_id in representatives}
    for candidate_id in sorted(relevant_fingerprints):
        fingerprint = relevant_fingerprints[candidate_id]
        best_representative: str | None = None
        best_score = -1.0
        for representative in representatives:
            result = behavioral_similarity(
                fingerprint,
                relevant_fingerprints[representative],
                threshold=threshold,
            )
            if result.score > best_score:
                best_score = result.score
                best_representative = representative
        if best_representative is None:  # pragma: no cover - representatives cover all inputs
            raise RuntimeError("behavioral cluster assignment failed")
        clusters[best_representative].append(candidate_id)

    return BehavioralClusterReport(
        trial_count=len(trials),
        raw_candidate_count=len(candidate_ids),
        unique_spec_count=len(spec_ids),
        family_count=len(families),
        fingerprinted_candidate_count=len(relevant_fingerprints),
        behavior_cluster_count=len(representatives),
        representative_candidate_ids=representatives,
        cluster_members={key: tuple(value) for key, value in clusters.items()},
    )
