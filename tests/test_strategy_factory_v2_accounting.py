from __future__ import annotations

import pytest

from eba_trader.strategy_discovery_v2 import BehavioralFingerprint
from eba_trader.strategy_factory_v2_accounting import build_low_fidelity_campaign_accounting
from eba_trader.strategy_factory_v2_pilot import (
    LowFidelityCandidateSummary,
    LowFidelityDiscoveryReport,
)


def _behavior(seed: int) -> BehavioralFingerprint:
    return BehavioralFingerprint(
        signal_keys=(f"s{seed}",),
        trade_keys=(f"t{seed}",),
        regime_returns=(0.01 * seed, 0.0, -0.01 * seed, 0.02 * seed),
        exposure_fraction=0.25,
        turnover=2.0,
    )


def _summary(
    candidate_id: str,
    family_id: str,
    *,
    complete: bool = True,
    rejected: bool = False,
    behavior: BehavioralFingerprint | None = None,
) -> LowFidelityCandidateSummary:
    return LowFidelityCandidateSummary(
        candidate_id=candidate_id,
        family_id=family_id,
        complete=complete,
        rejected=rejected,
        stratum_count=2 if complete else 1,
        mean_total_return=0.01,
        mean_expectancy=1.0,
        total_trade_count=4,
        mean_benchmark_relative_return=0.005,
        mean_max_drawdown=-0.01,
        mean_total_cost=1.5,
        mean_exposure=0.25,
        mean_turnover=2.0,
        behavior=behavior,
    )


def _declared(candidate_id: str, family_id: str, spec: str) -> dict[str, object]:
    return {
        "candidate_id": candidate_id,
        "family_id": family_id,
        "candidate_spec_sha256": spec,
    }


def test_accounting_keeps_raw_unique_family_and_behavioral_cluster_counts_separate() -> None:
    clone = _behavior(1)
    distinct = _behavior(9)
    report = LowFidelityDiscoveryReport(
        expected_strata=("d0-t01", "d0-t02"),
        candidates=(
            _summary("a", "family-a", behavior=clone),
            _summary("b", "family-b", behavior=clone),
            _summary("c", "family-b", behavior=distinct),
            _summary("d", "family-c", complete=False, behavior=None),
            _summary("e", "family-c", rejected=True, behavior=None),
        ),
        representative_candidate_ids=("a", "c"),
    )
    declared = (
        _declared("a", "family-a", "spec-a"),
        _declared("b", "family-b", "spec-b"),
        _declared("c", "family-b", "spec-c"),
        _declared("d", "family-c", "spec-d"),
        _declared("e", "family-c", "spec-e"),
    )

    accounting = build_low_fidelity_campaign_accounting(
        declared_candidates=declared,
        report=report,
        behavioral_similarity_threshold=0.90,
    )

    assert accounting.authority == "DISCOVERY_ONLY"
    assert accounting.raw_candidate_count == 5
    assert accounting.unique_specification_count == 5
    assert accounting.independent_family_count == 3
    assert accounting.complete_candidate_count == 4
    assert accounting.rejected_candidate_count == 1
    assert accounting.behaviorally_eligible_candidate_count == 3
    assert accounting.behavioral_cluster_count == 2
    assert accounting.clusters[0].representative_candidate_id == "a"
    assert accounting.clusters[0].member_candidate_ids == ("a", "b")
    assert accounting.clusters[0].family_ids == ("family-a", "family-b")
    assert accounting.clusters[1].member_candidate_ids == ("c",)


def test_incomplete_and_rejected_candidates_never_enter_behavioral_clusters() -> None:
    report = LowFidelityDiscoveryReport(
        expected_strata=("d0-t01", "d0-t02"),
        candidates=(
            _summary("a", "family-a", behavior=_behavior(1)),
            _summary("b", "family-a", complete=False, behavior=None),
            _summary("c", "family-b", rejected=True, behavior=None),
        ),
        representative_candidate_ids=("a",),
    )
    declared = (
        _declared("a", "family-a", "spec-a"),
        _declared("b", "family-a", "spec-b"),
        _declared("c", "family-b", "spec-c"),
    )

    accounting = build_low_fidelity_campaign_accounting(
        declared_candidates=declared,
        report=report,
        behavioral_similarity_threshold=0.90,
    )

    assert accounting.behaviorally_eligible_candidate_count == 1
    assert accounting.behavioral_cluster_count == 1
    assert accounting.clusters[0].member_candidate_ids == ("a",)


def test_accounting_fails_closed_on_undeclared_report_candidate() -> None:
    report = LowFidelityDiscoveryReport(
        expected_strata=("d0-t01",),
        candidates=(_summary("unknown", "family-a", behavior=_behavior(1)),),
        representative_candidate_ids=("unknown",),
    )

    with pytest.raises(ValueError, match="undeclared candidates"):
        build_low_fidelity_campaign_accounting(
            declared_candidates=(_declared("a", "family-a", "spec-a"),),
            report=report,
            behavioral_similarity_threshold=0.90,
        )
