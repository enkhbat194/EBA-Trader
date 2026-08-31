from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass

from .strategy_discovery_v2 import (
    BehavioralFingerprint,
    DiscoveryCandidate,
    DiscoveryTrialLedger,
    DiscoveryTrialStatus,
)


@dataclass(frozen=True, slots=True)
class DiscoveryBatchContext:
    campaign_id: str
    dataset_sha256: str
    source_code_sha: str
    fidelity: str
    search_round: int
    max_compute_ms: int

    def __post_init__(self) -> None:
        for name, value in (
            ("campaign_id", self.campaign_id),
            ("dataset_sha256", self.dataset_sha256),
            ("source_code_sha", self.source_code_sha),
            ("fidelity", self.fidelity),
        ):
            if not value.strip():
                raise ValueError(f"{name} is required")
        if self.search_round < 0:
            raise ValueError("search_round must be non-negative")
        if self.max_compute_ms <= 0:
            raise ValueError("max_compute_ms must be positive")


@dataclass(frozen=True, slots=True)
class DiscoveryEvaluation:
    metrics: Mapping[str, object]
    behavior: BehavioralFingerprint | None
    compute_ms: int
    rejection_reason: str | None = None

    def __post_init__(self) -> None:
        if self.compute_ms < 0:
            raise ValueError("compute_ms must be non-negative")
        if self.rejection_reason is not None and not self.rejection_reason.strip():
            raise ValueError("rejection_reason cannot be blank")

    @property
    def status(self) -> DiscoveryTrialStatus:
        if self.rejection_reason is not None:
            return DiscoveryTrialStatus.REJECTED
        return DiscoveryTrialStatus.EVALUATED


@dataclass(frozen=True, slots=True)
class DiscoveryBatchSummary:
    declared_candidate_ids: tuple[str, ...]
    evaluated_trial_ids: tuple[str, ...]
    total_compute_ms: int
    stopped_for_compute_budget: bool


CandidateEvaluator = Callable[[DiscoveryCandidate], DiscoveryEvaluation]


def run_discovery_batch(
    *,
    ledger: DiscoveryTrialLedger,
    context: DiscoveryBatchContext,
    candidates: Sequence[DiscoveryCandidate],
    evaluator: CandidateEvaluator,
) -> DiscoveryBatchSummary:
    candidate_ids = tuple(candidate.candidate_id for candidate in candidates)
    if len(candidate_ids) != len(set(candidate_ids)):
        raise ValueError("discovery batch contains duplicate candidate specifications")

    declared: list[str] = []
    evaluated: list[str] = []
    total_compute_ms = 0
    stopped = False

    for candidate in candidates:
        if total_compute_ms >= context.max_compute_ms:
            stopped = True
            break
        candidate_id = ledger.declare_candidate(
            campaign_id=context.campaign_id,
            candidate=candidate,
            source_code_sha=context.source_code_sha,
            search_round=context.search_round,
        )
        declared.append(candidate_id)
        trial_id = ledger.declare_trial(
            campaign_id=context.campaign_id,
            candidate_id=candidate_id,
            dataset_sha256=context.dataset_sha256,
            fidelity=context.fidelity,
        )
        evaluation = evaluator(candidate)
        ledger.record_result(
            trial_id=trial_id,
            status=evaluation.status,
            metrics=evaluation.metrics,
            behavior=evaluation.behavior,
            rejection_reason=evaluation.rejection_reason,
            compute_ms=evaluation.compute_ms,
        )
        evaluated.append(trial_id)
        total_compute_ms += evaluation.compute_ms

    if len(evaluated) < len(candidates) and total_compute_ms >= context.max_compute_ms:
        stopped = True
    return DiscoveryBatchSummary(
        declared_candidate_ids=tuple(declared),
        evaluated_trial_ids=tuple(evaluated),
        total_compute_ms=total_compute_ms,
        stopped_for_compute_budget=stopped,
    )
