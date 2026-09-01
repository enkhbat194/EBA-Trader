from types import SimpleNamespace

import pytest

from eba_trader.research_store import ResearchStore
from eba_trader.strategy_discovery_v2 import (
    BehavioralFingerprint,
    DiscoveryCampaignPolicy,
    DiscoveryCandidate,
    DiscoveryTrialLedger,
    DiscoveryTrialStatus,
)
from eba_trader import strategy_factory_v2_campaign as campaign


def _metrics() -> dict[str, float | int]:
    return {
        "total_return": -0.01,
        "expectancy": -1.0,
        "trade_count": 2,
        "benchmark_relative_return": -0.005,
        "max_drawdown": -0.02,
        "total_cost": 1.5,
        "exposure": 0.25,
        "turnover_round_trips_per_1000_bars": 2.0,
    }


def _behavior(seed: int) -> BehavioralFingerprint:
    return BehavioralFingerprint(
        signal_keys=(f"{seed:013d}:+1",),
        trade_keys=(f"{seed:013d}:{seed + 60_000:013d}:+1",),
        regime_returns=(-0.01 * seed, 0.0, 0.0, 0.0),
        exposure_fraction=0.25,
        turnover=2.0,
    )


def _complete_factory_ledger(tmp_path):
    ledger = DiscoveryTrialLedger(ResearchStore(tmp_path / "freeze-zero.db"))
    candidates = (
        DiscoveryCandidate("family_a", "hyp_a", {"x": 1}),
        DiscoveryCandidate("family_b", "hyp_b", {"x": 2}),
    )
    source_sha = "1" * 40
    expected_strata = ("d0s_00", "d0s_01")
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
            trial_id = ledger.declare_trial(
                campaign_id=campaign.PILOT_CAMPAIGN_ID,
                candidate_id=candidate.candidate_id,
                dataset_sha256=f"{candidate_index}{stratum_index}".ljust(64, "0"),
                fidelity=f"d0-low-v1:{stratum_id}",
            )
            ledger.record_result(
                trial_id=trial_id,
                status=DiscoveryTrialStatus.EVALUATED,
                metrics=_metrics(),
                behavior=_behavior(candidate_index + 1),
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


def test_factory_can_freeze_zero_survivors_as_immutable_negative_outcome(tmp_path):
    ledger, run, candidates = _complete_factory_ledger(tmp_path)

    selection_id = campaign.freeze_d0_pilot_survivors(
        ledger=ledger,
        campaign_run=run,
        candidate_ids=(),
        selection_definition={"ranking_schema": "frozen-test-v1", "outcome": "no_survivors"},
    )

    frozen = ledger.get_survivor_selection(campaign.PILOT_CAMPAIGN_ID)
    assert selection_id.startswith("dsel_")
    assert frozen is not None
    assert frozen["candidate_ids"] == ()
    definition = frozen["definition"]["definition"]
    assert definition["authority"] == campaign.PILOT_AUTHORITY
    assert definition["d1_opened"] is False
    assert definition["frozen_oos_opened"] is False
    assert definition["live_execution_allowed"] is False

    with pytest.raises(RuntimeError, match="immutable"):
        campaign.freeze_d0_pilot_survivors(
            ledger=ledger,
            campaign_run=run,
            candidate_ids=(candidates[0].candidate_id,),
            selection_definition={"ranking_schema": "frozen-test-v1"},
        )
