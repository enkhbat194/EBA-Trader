from pathlib import Path

import pytest

from eba_trader.research_store import ResearchStore
from eba_trader.strategy_confirmation_freeze_v2 import HiddenConfirmationFreezeStore
from eba_trader.strategy_discovery_v2 import (
    DiscoveryCampaignPolicy,
    DiscoveryCandidate,
    DiscoveryTrialLedger,
    DiscoveryTrialStatus,
)


def _prepared(tmp_path: Path) -> tuple[DiscoveryTrialLedger, str]:
    store = ResearchStore(tmp_path / "research.db")
    ledger = DiscoveryTrialLedger(store)
    ledger.register_campaign(
        DiscoveryCampaignPolicy(
            campaign_id="pilot",
            raw_candidate_cap=5,
            candidate_cap_per_family=5,
            survivor_cap=2,
        ),
        definition={"zone": "D0"},
    )
    candidate = DiscoveryCandidate(
        family_id="trend",
        hypothesis_fingerprint="hyp_trend",
        parameters={"lookback": 20},
    )
    candidate_id = ledger.declare_candidate(
        campaign_id="pilot",
        candidate=candidate,
        source_code_sha="code-sha",
        search_round=0,
    )
    trial_id = ledger.declare_trial(
        campaign_id="pilot",
        candidate_id=candidate_id,
        dataset_sha256="d0-dataset",
        fidelity="high",
    )
    ledger.record_result(
        trial_id=trial_id,
        status=DiscoveryTrialStatus.EVALUATED,
        metrics={"mean_return": 0.01},
    )
    ledger.freeze_survivor_selection(
        campaign_id="pilot",
        candidate_ids=(candidate_id,),
        definition={"selection_method": "cluster-representative-v1"},
    )
    return ledger, candidate_id


def test_hidden_confirmation_freeze_requires_survivor_selection(tmp_path: Path) -> None:
    store = ResearchStore(tmp_path / "research.db")
    ledger = DiscoveryTrialLedger(store)
    ledger.register_campaign(
        DiscoveryCampaignPolicy(campaign_id="pilot"),
        definition={"zone": "D0"},
    )
    freeze_store = HiddenConfirmationFreezeStore(ledger)

    with pytest.raises(RuntimeError, match="survivor selection"):
        freeze_store.freeze(
            campaign_id="pilot",
            execution_contract={"fee_bps": 4.0},
            universe_contract={"symbol": "BTCUSDT"},
            feature_contract={"version": 1},
        )


def test_hidden_confirmation_freeze_is_sealed_and_immutable(tmp_path: Path) -> None:
    ledger, candidate_id = _prepared(tmp_path)
    freeze_store = HiddenConfirmationFreezeStore(ledger)

    first = freeze_store.freeze(
        campaign_id="pilot",
        execution_contract={"fee_bps": 4.0, "slippage_bps": 1.5},
        universe_contract={"symbol_rule": "predeclared-liquid-universe-v1"},
        feature_contract={"version": 1},
    )
    replay = freeze_store.freeze(
        campaign_id="pilot",
        execution_contract={"fee_bps": 4.0, "slippage_bps": 1.5},
        universe_contract={"symbol_rule": "predeclared-liquid-universe-v1"},
        feature_contract={"version": 1},
    )

    assert replay.freeze_id == first.freeze_id
    assert first.candidate_ids == (candidate_id,)
    assert first.definition["d1_opened"] is False
    assert first.definition["frozen_oos_allowed"] is False
    assert first.definition["confirmation_zone"] == "D1"
    assert first.definition["frozen_oos_zone"] == "D3"

    with pytest.raises(RuntimeError, match="immutable"):
        freeze_store.freeze(
            campaign_id="pilot",
            execution_contract={"fee_bps": 3.0, "slippage_bps": 1.5},
            universe_contract={"symbol_rule": "predeclared-liquid-universe-v1"},
            feature_contract={"version": 1},
        )


def test_d1_dataset_cannot_reuse_d0_dataset_hash(tmp_path: Path) -> None:
    ledger, _ = _prepared(tmp_path)
    freeze_store = HiddenConfirmationFreezeStore(ledger)
    freeze = freeze_store.freeze(
        campaign_id="pilot",
        execution_contract={"fee_bps": 4.0},
        universe_contract={"symbol": "BTCUSDT"},
        feature_contract={"version": 1},
    )

    with pytest.raises(ValueError, match="already consumed"):
        freeze_store.assert_unseen_confirmation_dataset(freeze, "d0-dataset")

    freeze_store.assert_unseen_confirmation_dataset(freeze, "new-d1-dataset")
