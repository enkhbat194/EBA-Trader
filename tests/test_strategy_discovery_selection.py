from eba_trader.strategy_discovery_selection import (
    DiscoverySelectionMetrics,
    build_behavioral_cluster_report,
    discovery_priority_decision,
)
from eba_trader.strategy_discovery_v2 import BehavioralFingerprint


def _fingerprint(name: str) -> BehavioralFingerprint:
    if name == "clone-a" or name == "clone-b":
        return BehavioralFingerprint(
            signal_keys=("s1", "s2"),
            trade_keys=("t1", "t2"),
            regime_returns=(0.01, 0.02, -0.01, 0.03),
            exposure_fraction=0.4,
            turnover=8.0,
        )
    return BehavioralFingerprint(
        signal_keys=("s8", "s9"),
        trade_keys=("t8", "t9"),
        regime_returns=(-0.02, 0.01, 0.03, -0.01),
        exposure_fraction=0.2,
        turnover=3.0,
    )


def test_negative_economics_cannot_be_rescued_by_diversity() -> None:
    metrics = DiscoverySelectionMetrics(
        mean_return=-0.001,
        mean_expectancy=-2.0,
        trade_count=100,
        regime_coverage=1.0,
        parameter_stability=1.0,
        cost_resilience=1.0,
        complexity=0.0,
    )

    decision = discovery_priority_decision(metrics, behavioral_novelty=1.0)

    assert decision.economically_eligible is False
    assert "non_positive_mean_return" in decision.rejection_reasons
    assert "non_positive_mean_expectancy" in decision.rejection_reasons
    assert decision.priority_vector[0] == 0.0


def test_positive_candidate_gets_non_statistical_priority_vector() -> None:
    metrics = DiscoverySelectionMetrics(
        mean_return=0.002,
        mean_expectancy=1.5,
        trade_count=40,
        regime_coverage=0.75,
        parameter_stability=0.8,
        cost_resilience=0.7,
        complexity=2.0,
    )

    decision = discovery_priority_decision(metrics, behavioral_novelty=0.6)

    assert decision.economically_eligible is True
    assert decision.rejection_reasons == ()
    assert decision.priority_vector[0] == 1.0
    assert decision.priority_vector[4] == 0.6


def test_cluster_report_separates_trials_candidates_specs_families_and_behavior() -> None:
    trials = [
        {
            "trial_id": "t1",
            "candidate_id": "clone-a",
            "candidate_spec_sha256": "spec-a",
            "family_id": "trend",
        },
        {
            "trial_id": "t2",
            "candidate_id": "clone-a",
            "candidate_spec_sha256": "spec-a",
            "family_id": "trend",
        },
        {
            "trial_id": "t3",
            "candidate_id": "clone-b",
            "candidate_spec_sha256": "spec-b",
            "family_id": "trend",
        },
        {
            "trial_id": "t4",
            "candidate_id": "distinct",
            "candidate_spec_sha256": "spec-c",
            "family_id": "reversion",
        },
    ]
    fingerprints = {
        "clone-a": _fingerprint("clone-a"),
        "clone-b": _fingerprint("clone-b"),
        "distinct": _fingerprint("distinct"),
    }

    report = build_behavioral_cluster_report(trials, fingerprints, threshold=0.9)

    assert report.trial_count == 4
    assert report.raw_candidate_count == 3
    assert report.unique_spec_count == 3
    assert report.family_count == 2
    assert report.fingerprinted_candidate_count == 3
    assert report.behavior_cluster_count == 2
    assert report.representative_candidate_ids == ("clone-a", "distinct")
    assert report.cluster_members["clone-a"] == ("clone-a", "clone-b")
    assert report.cluster_members["distinct"] == ("distinct",)
