from types import SimpleNamespace

import pytest

import eba_trader.strategy_factory_v2_campaign as campaign
from eba_trader.research_store import ResearchStore
from eba_trader.strategy_discovery_batch import DiscoveryBatchSummary
from eba_trader.strategy_discovery_v2 import (
    BehavioralFingerprint,
    DiscoveryCampaignPolicy,
    DiscoveryCandidate,
    DiscoveryTrialLedger,
    DiscoveryTrialStatus,
)


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
        SimpleNamespace(
            stratum=item,
            dataset_sha256=str(index) * 64,
        )
        for index, item in enumerate(_declaration().manifest.temporal_strata)
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
    registered = campaign._registered_pilot_definition(ledger)
    assert registered["stratum_dataset_sha256"] == {
        "d0s_00": "0" * 64,
        "d0s_01": "1" * 64,
    }

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


def _trial_metrics() -> dict[str, float | int]:
    return {
        "total_return": 0.01,
        "expectancy": 1.0,
        "trade_count": 2,
        "benchmark_relative_return": 0.005,
        "max_drawdown": -0.01,
        "total_cost": 1.5,
        "exposure": 0.25,
        "turnover_round_trips_per_1000_bars": 2.0,
    }


def _behavior(seed: int, *, duplicate: bool = False) -> BehavioralFingerprint:
    key_seed = 1 if duplicate else seed
    return BehavioralFingerprint(
        signal_keys=(f"{key_seed:013d}:+1",),
        trade_keys=(f"{key_seed:013d}:{key_seed + 60_000:013d}:+1",),
        regime_returns=(0.01 * key_seed, 0.0, 0.0, 0.0),
        exposure_fraction=0.25,
        turnover=2.0,
    )


def _freeze_ledger(
    tmp_path,
    *,
    incomplete_candidate_index: int | None = None,
    duplicate_behavior: bool = False,
    wrong_dataset_candidate_index: int | None = None,
):
    ledger = DiscoveryTrialLedger(ResearchStore(tmp_path / "freeze.db"))
    candidates = (
        DiscoveryCandidate("family_a", "hyp_a", {"x": 1}),
        DiscoveryCandidate("family_b", "hyp_b", {"x": 2}),
    )
    source_sha = "1" * 40
    expected_strata = ("d0s_00", "d0s_01")
    stratum_dataset_sha256 = {
        "d0s_00": "0" * 64,
        "d0s_01": "1" * 64,
    }
    definition = {
        "schema": "strategy_factory_v2_d0_campaign_v1",
        "authority": campaign.PILOT_AUTHORITY,
        "catalog_seed": campaign.PILOT_SEED,
        "planned_candidate_count": len(candidates),
        "d0_source_kind": "INSPECTED_M5_DEVELOPMENT_CORPUS",
        "d0_declaration_sha256": "a" * 64,
        "d0_dataset_sha256": "d" * 64,
        "d0_provenance_class": "INSPECTED_REUSABLE_DISCOVERY_DATA",
        "expected_strata": list(expected_strata),
        "stratum_dataset_sha256": stratum_dataset_sha256,
        "warmup_bars": campaign.DEFAULT_WARMUP_BARS,
        "behavioral_similarity_threshold": campaign.PILOT_BEHAVIORAL_SIMILARITY_THRESHOLD,
        "search_round": campaign.PILOT_SEARCH_ROUND,
        "source_code_sha": source_sha,
        "d1_opened": False,
        "frozen_oos_opened": False,
        "live_execution_allowed": False,
    }
    ledger.register_campaign(
        DiscoveryCampaignPolicy(
            campaign_id=campaign.PILOT_CAMPAIGN_ID,
            raw_candidate_cap=10,
            candidate_cap_per_family=10,
            survivor_cap=10,
        ),
        definition=definition,
    )
    for candidate_index, candidate in enumerate(candidates):
        ledger.declare_candidate(
            campaign_id=campaign.PILOT_CAMPAIGN_ID,
            candidate=candidate,
            source_code_sha=source_sha,
            search_round=campaign.PILOT_SEARCH_ROUND,
        )
        for stratum_index, stratum_id in enumerate(expected_strata):
            if candidate_index == incomplete_candidate_index and stratum_index == 1:
                continue
            dataset_sha256 = stratum_dataset_sha256[stratum_id]
            if candidate_index == wrong_dataset_candidate_index and stratum_index == 1:
                dataset_sha256 = "f" * 64
            trial_id = ledger.declare_trial(
                campaign_id=campaign.PILOT_CAMPAIGN_ID,
                candidate_id=candidate.candidate_id,
                dataset_sha256=dataset_sha256,
                fidelity=f"d0-low-v1:{stratum_id}",
            )
            ledger.record_result(
                trial_id=trial_id,
                status=DiscoveryTrialStatus.EVALUATED,
                metrics=_trial_metrics(),
                behavior=_behavior(candidate_index + 1, duplicate=duplicate_behavior),
                compute_ms=1,
            )
    run = SimpleNamespace(
        campaign_id=campaign.PILOT_CAMPAIGN_ID,
        source_code_sha=source_sha,
        d0_declaration_sha256="a" * 64,
        d0_dataset_sha256="d" * 64,
        candidate_count=len(candidates),
        stratum_count=len(expected_strata),
        authority=campaign.PILOT_AUTHORITY,
        d1_opened=False,
        frozen_oos_opened=False,
        live_execution_allowed=False,
    )
    return ledger, run, candidates


def test_survivor_freeze_rebuilds_complete_evidence_from_ledger_and_keeps_d1_closed(tmp_path):
    ledger, run, candidates = _freeze_ledger(tmp_path)
    selected = tuple(candidate.candidate_id for candidate in candidates)

    selection_id = campaign.freeze_d0_pilot_survivors(
        ledger=ledger,
        campaign_run=run,
        candidate_ids=selected,
        selection_definition={"ranking_schema": "frozen-test-v1"},
    )

    frozen = ledger.get_survivor_selection(campaign.PILOT_CAMPAIGN_ID)
    assert selection_id.startswith("dsel_")
    assert frozen is not None
    assert tuple(frozen["candidate_ids"]) == tuple(sorted(selected))
    definition = frozen["definition"]["definition"]
    assert definition["schema"] == campaign.SURVIVOR_SELECTION_SCHEMA
    assert definition["expected_strata"] == ["d0s_00", "d0s_01"]
    assert definition["stratum_dataset_sha256"] == {
        "d0s_00": "0" * 64,
        "d0s_01": "1" * 64,
    }
    assert definition["d1_opened"] is False
    assert definition["frozen_oos_opened"] is False
    assert definition["live_execution_allowed"] is False


def test_survivor_freeze_rejects_fabricated_complete_run_when_ledger_catalog_is_incomplete(
    tmp_path,
):
    ledger, run, candidates = _freeze_ledger(tmp_path, incomplete_candidate_index=1)

    with pytest.raises(RuntimeError, match="D0 trial provenance is incomplete"):
        campaign.freeze_d0_pilot_survivors(
            ledger=ledger,
            campaign_run=run,
            candidate_ids=(candidates[0].candidate_id,),
            selection_definition={"ranking_schema": "frozen-test-v1"},
        )

    assert ledger.get_survivor_selection(campaign.PILOT_CAMPAIGN_ID) is None


def test_survivor_freeze_rejects_terminal_trial_with_wrong_stratum_dataset_sha(tmp_path):
    ledger, run, candidates = _freeze_ledger(tmp_path, wrong_dataset_candidate_index=1)

    with pytest.raises(RuntimeError, match="D0 trial dataset SHA does not match registered stratum"):
        campaign.freeze_d0_pilot_survivors(
            ledger=ledger,
            campaign_run=run,
            candidate_ids=(candidates[0].candidate_id,),
            selection_definition={"ranking_schema": "frozen-test-v1"},
        )

    assert ledger.get_survivor_selection(campaign.PILOT_CAMPAIGN_ID) is None


def test_survivor_freeze_rejects_multiple_candidates_from_same_behavioral_cluster(tmp_path):
    ledger, run, candidates = _freeze_ledger(tmp_path, duplicate_behavior=True)

    with pytest.raises(RuntimeError, match="multiple candidates from one cluster"):
        campaign.freeze_d0_pilot_survivors(
            ledger=ledger,
            campaign_run=run,
            candidate_ids=tuple(candidate.candidate_id for candidate in candidates),
            selection_definition={"ranking_schema": "frozen-test-v1"},
        )

    assert ledger.get_survivor_selection(campaign.PILOT_CAMPAIGN_ID) is None


def test_survivor_freeze_rejects_run_identity_that_disagrees_with_immutable_campaign(tmp_path):
    ledger, run, candidates = _freeze_ledger(tmp_path)
    run.source_code_sha = "2" * 40

    with pytest.raises(RuntimeError, match="source code does not match immutable campaign"):
        campaign.freeze_d0_pilot_survivors(
            ledger=ledger,
            campaign_run=run,
            candidate_ids=(candidates[0].candidate_id,),
            selection_definition={"ranking_schema": "frozen-test-v1"},
        )

    assert ledger.get_survivor_selection(campaign.PILOT_CAMPAIGN_ID) is None
