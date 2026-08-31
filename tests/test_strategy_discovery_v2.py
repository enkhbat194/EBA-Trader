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


def _ledger(
    tmp_path: Path,
    *,
    raw_cap: int = 4,
    family_cap: int = 3,
    survivor_cap: int = 2,
) -> tuple[ResearchStore, DiscoveryTrialLedger]:
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


def _declare(
    ledger: DiscoveryTrialLedger,
    candidate: DiscoveryCandidate,
    *,
    search_round: int = 0,
) -> str:
    return ledger.declare_candidate(
        campaign_id="pilot",
        candidate=candidate,
        source_code_sha="code-a",
        search_round=search_round,
    )


def _trial(
    ledger: DiscoveryTrialLedger,
    candidate_id: str,
    *,
    dataset: str = "dataset-a",
    fidelity: str = "low",
) -> str:
    return ledger.declare_trial(
        campaign_id="pilot",
        candidate_id=candidate_id,
        dataset_sha256=dataset,
        fidelity=fidelity,
    )


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


def test_candidate_and_trial_replays_are_idempotent(tmp_path: Path) -> None:
    _, ledger = _ledger(tmp_path)
    candidate = _candidate("trend", 1)
    candidate_id = _declare(ledger, candidate)
    replay_id = _declare(ledger, candidate)
    assert replay_id == candidate_id

    trial_id = _trial(ledger, candidate_id)
    replay_trial_id = _trial(ledger, candidate_id)
    assert replay_trial_id == trial_id

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
            status=DiscoveryTrialStatus.EVALUATED,
            metrics={"net_expectancy": 5.0},
            behavior=_fingerprint(),
            compute_ms=15,
        )


def test_candidate_budget_is_separate_from_evaluation_trial_count(tmp_path: Path) -> None:
    _, ledger = _ledger(tmp_path, raw_cap=2, family_cap=2)
    first_id = _declare(ledger, _candidate("trend", 1))

    first_trial = _trial(ledger, first_id, dataset="dataset-a", fidelity="low")
    second_trial = _trial(ledger, first_id, dataset="dataset-b", fidelity="high")
    assert first_trial != second_trial
    assert len(ledger.list_candidates("pilot")) == 1
    assert len(ledger.list_trials("pilot")) == 2

    _declare(ledger, _candidate("trend", 2))
    with pytest.raises(RuntimeError, match="raw candidate cap"):
        _declare(ledger, _candidate("reversion", 3))


def test_ledger_enforces_per_family_candidate_cap(tmp_path: Path) -> None:
    _, ledger = _ledger(tmp_path, raw_cap=4, family_cap=2)
    _declare(ledger, _candidate("trend", 1))
    _declare(ledger, _candidate("trend", 2))

    with pytest.raises(RuntimeError, match="per-family"):
        _declare(ledger, _candidate("trend", 3))

    _declare(ledger, _candidate("reversion", 4))
    assert len(ledger.list_candidates("pilot")) == 3


def test_survivor_selection_is_separate_immutable_and_capped(tmp_path: Path) -> None:
    _, ledger = _ledger(tmp_path, raw_cap=3, family_cap=3, survivor_cap=1)
    first_id = _declare(ledger, _candidate("trend", 1))
    second_id = _declare(ledger, _candidate("trend", 2))

    for candidate_id in (first_id, second_id):
        trial_id = _trial(ledger, candidate_id)
        ledger.record_result(
            trial_id=trial_id,
            status=DiscoveryTrialStatus.EVALUATED,
            metrics={"mean_return": 0.01},
            behavior=_fingerprint(shifted=candidate_id == second_id),
        )

    selection_id = ledger.freeze_survivor_selection(
        campaign_id="pilot",
        candidate_ids=(first_id,),
        definition={"method": "cluster-representative-v1"},
    )
    replay_id = ledger.freeze_survivor_selection(
        campaign_id="pilot",
        candidate_ids=(first_id,),
        definition={"method": "cluster-representative-v1"},
    )
    assert replay_id == selection_id
    selection = ledger.get_survivor_selection("pilot")
    assert selection is not None
    assert selection["candidate_ids"] == (first_id,)

    with pytest.raises(RuntimeError, match="survivor cap"):
        ledger.freeze_survivor_selection(
            campaign_id="pilot",
            candidate_ids=(first_id, second_id),
            definition={"method": "different"},
        )


def test_rejected_candidate_cannot_be_frozen_as_survivor(tmp_path: Path) -> None:
    _, ledger = _ledger(tmp_path)
    candidate_id = _declare(ledger, _candidate("trend", 1))
    trial_id = _trial(ledger, candidate_id)
    ledger.record_result(
        trial_id=trial_id,
        status=DiscoveryTrialStatus.REJECTED,
        metrics={"mean_return": -0.01},
        rejection_reason="negative economics",
    )

    with pytest.raises(RuntimeError, match="rejected"):
        ledger.freeze_survivor_selection(
            campaign_id="pilot",
            candidate_ids=(candidate_id,),
            definition={"method": "invalid"},
        )


def test_discovery_survivor_freeze_cannot_promote_strategy_lifecycle(tmp_path: Path) -> None:
    store, ledger = _ledger(tmp_path)
    store.register_strategy_version(
        strategy_id="STR-DISCOVERY-SAFETY",
        name="Discovery Safety",
        version=1,
        spec={"adapter": "ema_trend_v1"},
    )
    candidate_id = _declare(ledger, _candidate("trend", 1))
    trial_id = _trial(ledger, candidate_id)
    ledger.record_result(
        trial_id=trial_id,
        status=DiscoveryTrialStatus.EVALUATED,
        metrics={"discovery_priority_score": 99.0},
        behavior=_fingerprint(),
    )
    ledger.freeze_survivor_selection(
        campaign_id="pilot",
        candidate_ids=(candidate_id,),
        definition={"method": "test"},
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
