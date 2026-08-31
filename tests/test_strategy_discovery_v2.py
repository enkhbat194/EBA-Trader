from pathlib import Path

import pytest

from eba_trader.lifecycle import StrategyLifecycle
from eba_trader.research_store import ResearchStore
from eba_trader.strategy_discovery_v2 import (
    BehavioralFingerprint,
    DiscoveryCampaignPolicy,
    DiscoveryCandidate,
    DiscoveryTrialLedger,
    DiscoveryTrialStatus,
    behavioral_similarity,
    select_behavioral_representatives,
)


def _candidate(family: str, index: int) -> DiscoveryCandidate:
    return DiscoveryCandidate(
        family_id=family,
        hypothesis_fingerprint=f"hyp_{family}",
        parameters={"lookback": 10 + index, "threshold": 0.1 * (index + 1)},
    )


def _fingerprint(*, shifted: bool = False) -> BehavioralFingerprint:
    if shifted:
        return BehavioralFingerprint(
            signal_keys=("s8", "s9"),
            trade_keys=("t8", "t9"),
            regime_returns=(-0.03, -0.02, 0.01, 0.02),
            exposure_fraction=0.20,
            turnover=4.0,
        )
    return BehavioralFingerprint(
        signal_keys=("s1", "s2", "s3"),
        trade_keys=("t1", "t2"),
        regime_returns=(0.01, 0.02, -0.01, 0.03),
        exposure_fraction=0.42,
        turnover=9.0,
    )


def _ledger(tmp_path: Path, *, raw_cap: int = 4, family_cap: int = 3, survivor_cap: int = 2):
    store = ResearchStore(tmp_path / "research.db")
    ledger = DiscoveryTrialLedger(store)
    policy = DiscoveryCampaignPolicy(
        campaign_id="pilot",
        raw_candidate_cap=raw_cap,
        candidate_cap_per_family=family_cap,
        survivor_cap=survivor_cap,
    )
    ledger.register_campaign(policy, definition={"dataset_zone": "D0", "version": 1})
    return store, ledger


def test_policy_rejects_promotion_authority_and_oversized_budget() -> None:
    with pytest.raises(ValueError, match="DISCOVERY_ONLY"):
        DiscoveryCampaignPolicy(campaign_id="bad", authority="VERIFICATION")
    with pytest.raises(ValueError, match="raw_candidate_cap"):
        DiscoveryCampaignPolicy(campaign_id="bad", raw_candidate_cap=501)
    with pytest.raises(ValueError, match="candidate_cap_per_family"):
        DiscoveryCampaignPolicy(campaign_id="bad", candidate_cap_per_family=65)


def test_candidate_identity_is_deterministic_and_parameter_sensitive() -> None:
    first = _candidate("trend", 1)
    replay = _candidate("trend", 1)
    changed = _candidate("trend", 2)

    assert first.candidate_id == replay.candidate_id
    assert first.specification_sha256 == replay.specification_sha256
    assert first.candidate_id != changed.candidate_id


def test_behavioral_similarity_detects_clone_behavior() -> None:
    left = _fingerprint()
    clone = _fingerprint()
    distinct = _fingerprint(shifted=True)

    clone_result = behavioral_similarity(left, clone)
    distinct_result = behavioral_similarity(left, distinct)

    assert clone_result.score == 1.0
    assert clone_result.near_duplicate is True
    assert distinct_result.score < 0.90
    assert distinct_result.near_duplicate is False


def test_behavioral_representatives_remove_clones_deterministically() -> None:
    fingerprints = {
        "cand_b": _fingerprint(),
        "cand_a": _fingerprint(),
        "cand_c": _fingerprint(shifted=True),
    }

    kept = select_behavioral_representatives(fingerprints)

    assert kept == ("cand_a", "cand_c")


def test_ledger_is_idempotent_and_result_is_immutable(tmp_path: Path) -> None:
    _, ledger = _ledger(tmp_path)
    candidate = _candidate("trend", 1)
    trial_id = ledger.declare_trial(
        campaign_id="pilot",
        candidate=candidate,
        dataset_sha256="dataset-a",
        source_code_sha="code-a",
        search_round=0,
    )
    replay_id = ledger.declare_trial(
        campaign_id="pilot",
        candidate=candidate,
        dataset_sha256="dataset-a",
        source_code_sha="code-a",
        search_round=0,
    )
    assert replay_id == trial_id

    ledger.record_result(
        trial_id=trial_id,
        status=DiscoveryTrialStatus.REJECTED,
        metrics={"net_expectancy": -1.0},
        behavior=_fingerprint(),
        rejection_reason="negative expectancy",
        compute_ms=15,
    )
    ledger.record_result(
        trial_id=trial_id,
        status=DiscoveryTrialStatus.REJECTED,
        metrics={"net_expectancy": -1.0},
        behavior=_fingerprint(),
        rejection_reason="negative expectancy",
        compute_ms=15,
    )

    with pytest.raises(RuntimeError, match="immutable"):
        ledger.record_result(
            trial_id=trial_id,
            status=DiscoveryTrialStatus.SURVIVOR,
            metrics={"net_expectancy": 5.0},
            behavior=_fingerprint(),
            compute_ms=15,
        )


def test_ledger_enforces_raw_family_and_survivor_caps(tmp_path: Path) -> None:
    _, ledger = _ledger(tmp_path, raw_cap=3, family_cap=2, survivor_cap=1)
    first = _candidate("trend", 1)
    second = _candidate("trend", 2)
    third = _candidate("reversion", 3)

    first_id = ledger.declare_trial(
        campaign_id="pilot",
        candidate=first,
        dataset_sha256="dataset",
        source_code_sha="code",
        search_round=0,
    )
    ledger.declare_trial(
        campaign_id="pilot",
        candidate=second,
        dataset_sha256="dataset",
        source_code_sha="code",
        search_round=0,
    )
    with pytest.raises(RuntimeError, match="per-family"):
        ledger.declare_trial(
            campaign_id="pilot",
            candidate=_candidate("trend", 4),
            dataset_sha256="dataset",
            source_code_sha="code",
            search_round=0,
        )

    third_id = ledger.declare_trial(
        campaign_id="pilot",
        candidate=third,
        dataset_sha256="dataset",
        source_code_sha="code",
        search_round=0,
    )
    ledger.record_result(
        trial_id=first_id,
        status=DiscoveryTrialStatus.SURVIVOR,
        metrics={"discovery_priority_score": 1.0},
        behavior=_fingerprint(),
    )
    with pytest.raises(RuntimeError, match="survivor cap"):
        ledger.record_result(
            trial_id=third_id,
            status=DiscoveryTrialStatus.SURVIVOR,
            metrics={"discovery_priority_score": 0.9},
            behavior=_fingerprint(shifted=True),
        )

    with pytest.raises(RuntimeError, match="raw candidate cap"):
        ledger.declare_trial(
            campaign_id="pilot",
            candidate=_candidate("breakout", 5),
            dataset_sha256="dataset",
            source_code_sha="code",
            search_round=1,
        )


def test_discovery_work_cannot_promote_strategy_lifecycle(tmp_path: Path) -> None:
    store, ledger = _ledger(tmp_path)
    store.register_strategy_version(
        strategy_id="STR-DISCOVERY-SAFETY",
        name="Discovery Safety",
        version=1,
        spec={"adapter": "ema_trend_v1"},
    )
    trial_id = ledger.declare_trial(
        campaign_id="pilot",
        candidate=_candidate("trend", 1),
        dataset_sha256="dataset",
        source_code_sha="code",
        search_round=0,
    )
    ledger.record_result(
        trial_id=trial_id,
        status=DiscoveryTrialStatus.SURVIVOR,
        metrics={"discovery_priority_score": 99.0},
        behavior=_fingerprint(),
    )

    strategy = store.get_strategy_version("STR-DISCOVERY-SAFETY", 1)
    assert strategy is not None
    assert strategy["lifecycle_state"] is StrategyLifecycle.GENERATED


def test_campaign_definition_is_immutable(tmp_path: Path) -> None:
    store = ResearchStore(tmp_path / "research.db")
    ledger = DiscoveryTrialLedger(store)
    policy = DiscoveryCampaignPolicy(campaign_id="pilot")
    ledger.register_campaign(policy, definition={"dataset_zone": "D0"})
    ledger.register_campaign(policy, definition={"dataset_zone": "D0"})

    with pytest.raises(ValueError, match="immutable"):
        ledger.register_campaign(policy, definition={"dataset_zone": "D1"})
