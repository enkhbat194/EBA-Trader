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
