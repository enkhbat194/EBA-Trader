from types import SimpleNamespace

import pytest

import eba_trader.strategy_factory_v2_campaign as campaign
from eba_trader.research_store import ResearchStore
from eba_trader.strategy_discovery_batch import DiscoveryBatchSummary
from eba_trader.strategy_discovery_v2 import DiscoveryCandidate, DiscoveryTrialLedger


def _declaration():
    strata = (
        SimpleNamespace(stratum_id="d0s_00"),
        SimpleNamespace(stratum_id="d0s_01"),
    )
    manifest = SimpleNamespace(dataset_sha256="d" * 64, temporal_strata=strata)
    return SimpleNamespace(
        authority="DISCOVERY_ONLY",
        source_kind="INSPECTED_M5_DEVELOPMENT_CORPUS",
        provenance_class="INSPECTED_REUSABLE_DISCOVERY_DATA",
        declaration_sha256="a" * 64,
        manifest=manifest,
    )


def test_d0_pilot_campaign_is_resume_safe_and_keeps_downstream_gates_closed(tmp_path, monkeypatch):
    candidates = (
        DiscoveryCandidate("family_a", "hyp_a", {"x": 1}),
        DiscoveryCandidate("family_b", "hyp_b", {"x": 2}),
    )
    fake_strata = tuple(
        SimpleNamespace(stratum=item) for item in _declaration().manifest.temporal_strata
    )
    monkeypatch.setattr(campaign, "generate_pilot_candidates", lambda *, seed: candidates)
    monkeypatch.setattr(
        campaign,
        "materialize_low_fidelity_strata",
        lambda **kwargs: fake_strata,
    )
    calls = []

    def fake_run_low_fidelity_stratum(**kwargs):
        calls.append(kwargs["stratum_dataset"].stratum.stratum_id)
        return DiscoveryBatchSummary(
            declared_candidate_ids=tuple(item.candidate_id for item in candidates),
            evaluated_trial_ids=(f"trial_{len(calls)}",),
            total_compute_ms=10,
            stopped_for_compute_budget=False,
        )

    monkeypatch.setattr(campaign, "run_low_fidelity_stratum", fake_run_low_fidelity_stratum)

    ledger = DiscoveryTrialLedger(ResearchStore(tmp_path / "research.db"))
    rows = (SimpleNamespace(candle=object()),)
    declaration = _declaration()
    result = campaign.run_d0_pilot_campaign(
        ledger=ledger,
        declaration=declaration,
        source_code_sha="1" * 40,
        rows=rows,
        max_compute_ms_per_stratum=1000,
    )

    assert result.candidate_count == 2
    assert result.stratum_count == 2
    assert result.newly_evaluated_trial_count == 2
    assert calls == ["d0s_00", "d0s_01"]
    assert result.authority == "DISCOVERY_ONLY"
    assert result.d1_opened is False
    assert result.frozen_oos_opened is False
    assert result.live_execution_allowed is False
    assert ledger.get_survivor_selection(campaign.PILOT_CAMPAIGN_ID) is None

    campaign.run_d0_pilot_campaign(
        ledger=ledger,
        declaration=declaration,
        source_code_sha="1" * 40,
        rows=rows,
        max_compute_ms_per_stratum=2000,
    )

    with pytest.raises(ValueError, match="campaign definition is immutable"):
        campaign.run_d0_pilot_campaign(
            ledger=ledger,
            declaration=declaration,
            source_code_sha="2" * 40,
            rows=rows,
            max_compute_ms_per_stratum=1000,
        )


def test_d0_pilot_campaign_rejects_non_discovery_authority(tmp_path):
    declaration = _declaration()
    declaration.authority = "VERIFICATION"
    ledger = DiscoveryTrialLedger(ResearchStore(tmp_path / "research.db"))
    with pytest.raises(ValueError, match="DISCOVERY_ONLY"):
        campaign.run_d0_pilot_campaign(
            ledger=ledger,
            declaration=declaration,
            source_code_sha="1" * 40,
            rows=(SimpleNamespace(candle=object()),),
            max_compute_ms_per_stratum=1000,
        )


def test_clean_checkout_sha_uses_actual_git_commit(monkeypatch):
    actual_sha = "a" * 40
    monkeypatch.setattr(
        campaign,
        "collect_source_provenance",
        lambda **kwargs: {
            "git_commit": actual_sha,
            "tracked_working_tree_clean": True,
        },
    )

    assert campaign._clean_checkout_sha(expected_source_code_sha=actual_sha) == actual_sha


def test_clean_checkout_sha_rejects_expected_mismatch(monkeypatch):
    actual_sha = "a" * 40
    monkeypatch.setattr(
        campaign,
        "collect_source_provenance",
        lambda **kwargs: {
            "git_commit": actual_sha,
            "tracked_working_tree_clean": True,
        },
    )

    with pytest.raises(RuntimeError, match="source checkout mismatch"):
        campaign._clean_checkout_sha(expected_source_code_sha="b" * 40)


class _FreezeLedger:
    def __init__(self):
        self.calls = []

    def freeze_survivor_selection(self, **kwargs):
        self.calls.append(kwargs)
        return "dsel_test"


def _freeze_run(*, candidate_rows, clusters, stopped=False):
    report = SimpleNamespace(
        expected_strata=("d0s_00", "d0s_01"),
        candidates=tuple(candidate_rows),
    )
    accounting = SimpleNamespace(
        clusters=tuple(clusters),
        authority="DISCOVERY_ONLY",
    )
    return SimpleNamespace(
        campaign_id=campaign.PILOT_CAMPAIGN_ID,
        source_code_sha="1" * 40,
        d0_declaration_sha256="a" * 64,
        d0_dataset_sha256="d" * 64,
        candidate_count=len(candidate_rows),
        stratum_count=2,
        stopped_for_compute_budget=stopped,
        report=report,
        accounting=accounting,
        authority="DISCOVERY_ONLY",
        d1_opened=False,
        frozen_oos_opened=False,
        live_execution_allowed=False,
    )


def _eligible_candidate(candidate_id, *, complete=True, rejected=False, stratum_count=2):
    return SimpleNamespace(
        candidate_id=candidate_id,
        complete=complete,
        rejected=rejected,
        stratum_count=stratum_count,
        behavior=object() if complete and not rejected else None,
    )


def test_survivor_freeze_binds_complete_d0_evidence_and_keeps_d1_closed():
    ledger = _FreezeLedger()
    run = _freeze_run(
        candidate_rows=[_eligible_candidate("a"), _eligible_candidate("b")],
        clusters=[
            SimpleNamespace(representative_candidate_id="a", member_candidate_ids=("a",)),
            SimpleNamespace(representative_candidate_id="b", member_candidate_ids=("b",)),
        ],
    )

    selection_id = campaign.freeze_d0_pilot_survivors(
        ledger=ledger,
        campaign_run=run,
        candidate_ids=("a", "b"),
        selection_definition={"ranking_schema": "frozen-test-v1"},
    )

    assert selection_id == "dsel_test"
    assert len(ledger.calls) == 1
    call = ledger.calls[0]
    assert call["campaign_id"] == campaign.PILOT_CAMPAIGN_ID
    assert call["candidate_ids"] == ("a", "b")
    definition = call["definition"]
    assert definition["schema"] == campaign.SURVIVOR_SELECTION_SCHEMA
    assert definition["expected_strata"] == ["d0s_00", "d0s_01"]
    assert definition["d1_opened"] is False
    assert definition["frozen_oos_opened"] is False
    assert definition["live_execution_allowed"] is False


def test_survivor_freeze_rejects_incomplete_candidate_before_ledger_write():
    ledger = _FreezeLedger()
    run = _freeze_run(
        candidate_rows=[_eligible_candidate("a", complete=False, stratum_count=1)],
        clusters=[],
    )

    with pytest.raises(RuntimeError, match="not complete behaviorally eligible"):
        campaign.freeze_d0_pilot_survivors(
            ledger=ledger,
            campaign_run=run,
            candidate_ids=("a",),
            selection_definition={"ranking_schema": "frozen-test-v1"},
        )

    assert ledger.calls == []


def test_survivor_freeze_rejects_multiple_candidates_from_same_behavioral_cluster():
    ledger = _FreezeLedger()
    run = _freeze_run(
        candidate_rows=[_eligible_candidate("a"), _eligible_candidate("b")],
        clusters=[
            SimpleNamespace(
                representative_candidate_id="a",
                member_candidate_ids=("a", "b"),
            )
        ],
    )

    with pytest.raises(RuntimeError, match="multiple candidates from one cluster"):
        campaign.freeze_d0_pilot_survivors(
            ledger=ledger,
            campaign_run=run,
            candidate_ids=("a", "b"),
            selection_definition={"ranking_schema": "frozen-test-v1"},
        )

    assert ledger.calls == []


def test_survivor_freeze_rejects_compute_budget_stopped_campaign():
    ledger = _FreezeLedger()
    run = _freeze_run(
        candidate_rows=[_eligible_candidate("a")],
        clusters=[SimpleNamespace(representative_candidate_id="a", member_candidate_ids=("a",))],
        stopped=True,
    )

    with pytest.raises(RuntimeError, match="completed D0 campaign pass"):
        campaign.freeze_d0_pilot_survivors(
            ledger=ledger,
            campaign_run=run,
            candidate_ids=("a",),
            selection_definition={"ranking_schema": "frozen-test-v1"},
        )

    assert ledger.calls == []
