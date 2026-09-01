from pathlib import Path

import pytest

from eba_trader.research_store import ResearchStore
from eba_trader.strategy_discovery_batch import (
    DiscoveryBatchContext,
    DiscoveryEvaluation,
    run_discovery_batch,
)
from eba_trader.strategy_discovery_v2 import (
    BehavioralFingerprint,
    DiscoveryCampaignPolicy,
    DiscoveryCandidate,
    DiscoveryTrialLedger,
)


def _candidate(index: int) -> DiscoveryCandidate:
    return DiscoveryCandidate(
        family_id="trend",
        hypothesis_fingerprint="hyp_trend",
        parameters={"lookback": 10 + index},
    )


def _fingerprint(index: int) -> BehavioralFingerprint:
    return BehavioralFingerprint(
        signal_keys=(f"s{index}",),
        trade_keys=(f"t{index}",),
        regime_returns=(0.01 * index, -0.01, 0.02),
        exposure_fraction=0.2,
        turnover=2.0,
    )


def _ledger(tmp_path: Path) -> DiscoveryTrialLedger:
    store = ResearchStore(tmp_path / "research.db")
    ledger = DiscoveryTrialLedger(store)
    ledger.register_campaign(
        DiscoveryCampaignPolicy(
            campaign_id="pilot",
            raw_candidate_cap=10,
            candidate_cap_per_family=10,
            survivor_cap=3,
        ),
        definition={"zone": "D0"},
    )
    return ledger


def test_batch_records_all_evaluated_candidates_in_one_dataset_context(tmp_path: Path) -> None:
    ledger = _ledger(tmp_path)
    candidates = tuple(_candidate(index) for index in range(3))

    def evaluator(candidate: DiscoveryCandidate) -> DiscoveryEvaluation:
        index = int(candidate.parameters["lookback"]) - 10
        return DiscoveryEvaluation(
            metrics={"mean_return": index / 1000},
            behavior=_fingerprint(index),
            compute_ms=10,
        )

    summary = run_discovery_batch(
        ledger=ledger,
        context=DiscoveryBatchContext(
            campaign_id="pilot",
            dataset_sha256="dataset",
            source_code_sha="code",
            fidelity="low",
            search_round=0,
            max_compute_ms=100,
        ),
        candidates=candidates,
        evaluator=evaluator,
    )

    assert len(summary.declared_candidate_ids) == 3
    assert len(summary.evaluated_trial_ids) == 3
    assert summary.reused_terminal_trial_ids == ()
    assert summary.total_compute_ms == 30
    assert summary.stopped_for_compute_budget is False
    assert len(ledger.list_candidates("pilot")) == 3
    assert len(ledger.list_trials("pilot")) == 3


def test_batch_stops_declaring_new_candidates_after_compute_budget(tmp_path: Path) -> None:
    ledger = _ledger(tmp_path)
    candidates = tuple(_candidate(index) for index in range(5))

    def evaluator(candidate: DiscoveryCandidate) -> DiscoveryEvaluation:
        index = int(candidate.parameters["lookback"]) - 10
        return DiscoveryEvaluation(
            metrics={"mean_return": 0.001},
            behavior=_fingerprint(index),
            compute_ms=25,
        )

    summary = run_discovery_batch(
        ledger=ledger,
        context=DiscoveryBatchContext(
            campaign_id="pilot",
            dataset_sha256="dataset",
            source_code_sha="code",
            fidelity="low",
            search_round=0,
            max_compute_ms=50,
        ),
        candidates=candidates,
        evaluator=evaluator,
    )

    assert len(summary.evaluated_trial_ids) == 2
    assert summary.total_compute_ms == 50
    assert summary.stopped_for_compute_budget is True
    assert len(ledger.list_candidates("pilot")) == 2


def test_batch_resume_reuses_terminal_trials_without_re_evaluation(tmp_path: Path) -> None:
    ledger = _ledger(tmp_path)
    candidates = tuple(_candidate(index) for index in range(5))
    first_calls: list[str] = []

    def first_evaluator(candidate: DiscoveryCandidate) -> DiscoveryEvaluation:
        first_calls.append(candidate.candidate_id)
        index = int(candidate.parameters["lookback"]) - 10
        return DiscoveryEvaluation(
            metrics={"mean_return": index / 1000},
            behavior=_fingerprint(index),
            compute_ms=25,
        )

    first = run_discovery_batch(
        ledger=ledger,
        context=DiscoveryBatchContext(
            campaign_id="pilot",
            dataset_sha256="dataset",
            source_code_sha="code",
            fidelity="low",
            search_round=0,
            max_compute_ms=50,
        ),
        candidates=candidates,
        evaluator=first_evaluator,
    )
    assert len(first.evaluated_trial_ids) == 2
    assert len(first_calls) == 2

    resume_calls: list[str] = []

    def resume_evaluator(candidate: DiscoveryCandidate) -> DiscoveryEvaluation:
        resume_calls.append(candidate.candidate_id)
        index = int(candidate.parameters["lookback"]) - 10
        return DiscoveryEvaluation(
            metrics={"mean_return": index / 1000},
            behavior=_fingerprint(index),
            compute_ms=25,
        )

    resumed = run_discovery_batch(
        ledger=ledger,
        context=DiscoveryBatchContext(
            campaign_id="pilot",
            dataset_sha256="dataset",
            source_code_sha="code",
            fidelity="low",
            search_round=0,
            max_compute_ms=100,
        ),
        candidates=candidates,
        evaluator=resume_evaluator,
    )

    assert len(resumed.reused_terminal_trial_ids) == 2
    assert len(resumed.evaluated_trial_ids) == 3
    assert resume_calls == [candidate.candidate_id for candidate in candidates[2:]]
    assert resumed.total_compute_ms == 75
    assert resumed.stopped_for_compute_budget is False
    assert len(ledger.list_trials("pilot")) == 5

    replay = run_discovery_batch(
        ledger=ledger,
        context=DiscoveryBatchContext(
            campaign_id="pilot",
            dataset_sha256="dataset",
            source_code_sha="code",
            fidelity="low",
            search_round=0,
            max_compute_ms=1,
        ),
        candidates=candidates,
        evaluator=lambda _: (_ for _ in ()).throw(AssertionError("must not re-evaluate")),
    )
    assert len(replay.reused_terminal_trial_ids) == 5
    assert replay.evaluated_trial_ids == ()
    assert replay.total_compute_ms == 0
    assert replay.stopped_for_compute_budget is False


def test_batch_rejects_duplicate_candidate_specs_before_evaluation(tmp_path: Path) -> None:
    ledger = _ledger(tmp_path)
    candidate = _candidate(1)

    with pytest.raises(ValueError, match="duplicate"):
        run_discovery_batch(
            ledger=ledger,
            context=DiscoveryBatchContext(
                campaign_id="pilot",
                dataset_sha256="dataset",
                source_code_sha="code",
                fidelity="low",
                search_round=0,
                max_compute_ms=100,
            ),
            candidates=(candidate, candidate),
            evaluator=lambda _: DiscoveryEvaluation(
                metrics={},
                behavior=None,
                compute_ms=1,
            ),
        )


def test_batch_can_record_rejection_without_promotion(tmp_path: Path) -> None:
    ledger = _ledger(tmp_path)

    summary = run_discovery_batch(
        ledger=ledger,
        context=DiscoveryBatchContext(
            campaign_id="pilot",
            dataset_sha256="dataset",
            source_code_sha="code",
            fidelity="static-screen",
            search_round=0,
            max_compute_ms=100,
        ),
        candidates=(_candidate(1),),
        evaluator=lambda _: DiscoveryEvaluation(
            metrics={"trade_count": 0},
            behavior=None,
            compute_ms=1,
            rejection_reason="zero opportunity",
        ),
    )

    trial = ledger.list_trials("pilot")[0]
    assert len(summary.evaluated_trial_ids) == 1
    assert trial["status"] == "rejected"
    assert trial["rejection_reason"] == "zero opportunity"
