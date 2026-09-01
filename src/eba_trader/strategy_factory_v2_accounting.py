from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from .strategy_discovery_v2 import BehavioralFingerprint, behavioral_similarity
from .strategy_factory_v2_pilot import LowFidelityDiscoveryReport


@dataclass(frozen=True, slots=True)
class BehavioralClusterAccounting:
    representative_candidate_id: str
    member_candidate_ids: tuple[str, ...]
    family_ids: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class LowFidelityCampaignAccounting:
    raw_candidate_count: int
    unique_specification_count: int
    independent_family_count: int
    complete_candidate_count: int
    rejected_candidate_count: int
    behaviorally_eligible_candidate_count: int
    behavioral_cluster_count: int
    clusters: tuple[BehavioralClusterAccounting, ...]
    authority: str = "DISCOVERY_ONLY"


def build_low_fidelity_campaign_accounting(
    *,
    declared_candidates: Sequence[Mapping[str, Any]],
    report: LowFidelityDiscoveryReport,
    behavioral_similarity_threshold: float,
) -> LowFidelityCampaignAccounting:
    """Build auditable discovery counts and deterministic behavioral clusters.

    This is accounting/selection evidence only. Incomplete and rejected candidates are counted,
    but only complete non-rejected candidates with behavioral fingerprints may enter clusters.
    No profitability gate, survivor freeze, D1 access, lifecycle transition, or execution authority
    is introduced here.
    """

    if not 0.0 < behavioral_similarity_threshold <= 1.0:
        raise ValueError("behavioral similarity threshold must be in (0, 1]")

    candidate_rows = tuple(declared_candidates)
    candidate_ids = [str(row.get("candidate_id") or "").strip() for row in candidate_rows]
    specification_ids = [
        str(row.get("candidate_spec_sha256") or "").strip() for row in candidate_rows
    ]
    family_ids = [str(row.get("family_id") or "").strip() for row in candidate_rows]
    if any(not value for value in candidate_ids):
        raise ValueError("declared candidate_id is required")
    if any(not value for value in specification_ids):
        raise ValueError("declared candidate_spec_sha256 is required")
    if any(not value for value in family_ids):
        raise ValueError("declared family_id is required")
    if len(candidate_ids) != len(set(candidate_ids)):
        raise ValueError("declared candidate_ids must be unique")

    declared_by_id = {
        candidate_id: {
            "family_id": family_id,
            "specification_sha256": specification_sha256,
        }
        for candidate_id, family_id, specification_sha256 in zip(
            candidate_ids, family_ids, specification_ids, strict=True
        )
    }

    report_ids = [item.candidate_id for item in report.candidates]
    if len(report_ids) != len(set(report_ids)):
        raise ValueError("low-fidelity report candidate_ids must be unique")
    undeclared = sorted(set(report_ids) - set(declared_by_id))
    if undeclared:
        raise ValueError(f"low-fidelity report contains undeclared candidates: {undeclared}")
    for item in report.candidates:
        if declared_by_id[item.candidate_id]["family_id"] != item.family_id:
            raise ValueError("low-fidelity report family_id mismatches declared candidate")

    eligible = {
        item.candidate_id: item
        for item in report.candidates
        if item.complete and not item.rejected and item.behavior is not None
    }
    clusters = _cluster_eligible_candidates(
        eligible,
        threshold=behavioral_similarity_threshold,
    )
    cluster_representatives = tuple(item.representative_candidate_id for item in clusters)
    if cluster_representatives != report.representative_candidate_ids:
        raise ValueError("behavioral cluster representatives drift from low-fidelity report")

    return LowFidelityCampaignAccounting(
        raw_candidate_count=len(candidate_rows),
        unique_specification_count=len(set(specification_ids)),
        independent_family_count=len(set(family_ids)),
        complete_candidate_count=report.complete_candidate_count,
        rejected_candidate_count=report.rejected_candidate_count,
        behaviorally_eligible_candidate_count=len(eligible),
        behavioral_cluster_count=len(clusters),
        clusters=clusters,
    )


def _cluster_eligible_candidates(
    eligible: Mapping[str, Any],
    *,
    threshold: float,
) -> tuple[BehavioralClusterAccounting, ...]:
    representatives: list[str] = []
    members_by_representative: dict[str, list[str]] = {}

    for candidate_id in sorted(eligible):
        item = eligible[candidate_id]
        fingerprint = item.behavior
        if not isinstance(fingerprint, BehavioralFingerprint):
            raise ValueError("eligible candidate is missing BehavioralFingerprint")

        assigned_representative: str | None = None
        for representative_id in representatives:
            representative_fingerprint = eligible[representative_id].behavior
            if behavioral_similarity(
                fingerprint,
                representative_fingerprint,
                threshold=threshold,
            ).near_duplicate:
                assigned_representative = representative_id
                break

        if assigned_representative is None:
            assigned_representative = candidate_id
            representatives.append(candidate_id)
            members_by_representative[candidate_id] = []
        members_by_representative[assigned_representative].append(candidate_id)

    output: list[BehavioralClusterAccounting] = []
    for representative_id in representatives:
        member_ids = tuple(members_by_representative[representative_id])
        output.append(
            BehavioralClusterAccounting(
                representative_candidate_id=representative_id,
                member_candidate_ids=member_ids,
                family_ids=tuple(sorted({eligible[item].family_id for item in member_ids})),
            )
        )
    return tuple(output)
