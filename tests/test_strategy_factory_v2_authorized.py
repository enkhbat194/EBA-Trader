from __future__ import annotations

import json
from pathlib import Path

import pytest

from eba_trader.strategy_discovery_v2 import BehavioralFingerprint
from eba_trader.strategy_factory_v2_accounting import (
    BehavioralClusterAccounting,
    LowFidelityCampaignAccounting,
)
from eba_trader.strategy_factory_v2_authorized import (
    EXPECTED_MINIMUM_TOTAL_TRADES,
    load_sfv2_d0_authorization,
    select_d0_pilot_survivors,
)
from eba_trader.strategy_factory_v2_campaign import D0PilotCampaignRun
from eba_trader.strategy_factory_v2_pilot import (
    LowFidelityCandidateSummary,
    LowFidelityDiscoveryReport,
)

ROOT = Path(__file__).resolve().parents[1]
AUTH_PATH = ROOT / "config" / "sfv2_d0_production_authorization_v1.json"


def _behavior(key: str) -> BehavioralFingerprint:
    return BehavioralFingerprint(
        signal_keys=(f"signal:{key}",),
        trade_keys=(f"trade:{key}",),
        regime_returns=(0.01, 0.02),
        exposure_fraction=0.1,
        turnover=1.0,
    )


def _summary(
    candidate_id: str,
    *,
    family_id: str = "family",
    total_return: float = 0.01,
    expectancy: float = 1.0,
    benchmark_delta: float = 0.005,
    trades: int = 20,
    drawdown: float = -0.02,
) -> LowFidelityCandidateSummary:
    return LowFidelityCandidateSummary(
        candidate_id=candidate_id,
        family_id=family_id,
        complete=True,
        rejected=False,
        stratum_count=12,
        mean_total_return=total_return,
        mean_expectancy=expectancy,
        total_trade_count=trades,
        mean_benchmark_relative_return=benchmark_delta,
        mean_max_drawdown=drawdown,
        mean_total_cost=1.0,
        mean_exposure=0.1,
        mean_turnover=1.0,
        behavior=_behavior(candidate_id),
    )


def _campaign(
    summaries: tuple[LowFidelityCandidateSummary, ...],
    clusters: tuple[BehavioralClusterAccounting, ...],
) -> D0PilotCampaignRun:
    report = LowFidelityDiscoveryReport(
        expected_strata=tuple(f"s{index}" for index in range(12)),
        candidates=summaries,
        representative_candidate_ids=tuple(item.representative_candidate_id for item in clusters),
    )
    accounting = LowFidelityCampaignAccounting(
        raw_candidate_count=len(summaries),
        unique_specification_count=len(summaries),
        independent_family_count=len({item.family_id for item in summaries}),
        complete_candidate_count=len(summaries),
        rejected_candidate_count=0,
        behaviorally_eligible_candidate_count=len(summaries),
        behavioral_cluster_count=len(clusters),
        clusters=clusters,
    )
    return D0PilotCampaignRun(
        campaign_id="sfv2-discovery-pilot-v1",
        source_code_sha="a" * 40,
        d0_declaration_sha256="b" * 64,
        d0_dataset_sha256="c" * 64,
        candidate_count=len(summaries),
        stratum_count=12,
        newly_evaluated_trial_count=0,
        reused_terminal_trial_count=0,
        stopped_for_compute_budget=False,
        report=report,
        accounting=accounting,
    )


def _payload() -> dict[str, object]:
    return json.loads(AUTH_PATH.read_text(encoding="utf-8"))


def _write(tmp_path: Path, payload: dict[str, object]) -> Path:
    path = tmp_path / "authorization.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def test_authorization_is_single_use_discovery_only_and_predeclares_selection() -> None:
    authorization = load_sfv2_d0_authorization(AUTH_PATH)
    assert authorization.request_id == "sfv2-d0-prod-20260901-v1"
    assert authorization.max_compute_ms_per_stratum == 30000
    assert authorization.max_cycles_per_invocation == 4
    assert authorization.minimum_total_trades == EXPECTED_MINIMUM_TOTAL_TRADES == 12
    assert authorization.maximum_survivors == 30


def test_authorization_rejects_public_trigger_or_gate_weakening(tmp_path: Path) -> None:
    payload = _payload()
    safety = dict(payload["safety"])
    safety["public_trigger_allowed"] = True
    payload["safety"] = safety
    with pytest.raises(ValueError, match="safety authorization changed"):
        load_sfv2_d0_authorization(_write(tmp_path, payload))

    payload = _payload()
    policy = dict(payload["selection_policy"])
    policy["minimum_total_trades"] = 4
    payload["selection_policy"] = policy
    with pytest.raises(ValueError, match="activity floor changed"):
        load_sfv2_d0_authorization(_write(tmp_path, payload))


def test_selection_chooses_best_positive_member_per_behavioral_cluster() -> None:
    negative_first = _summary("a-negative", total_return=-0.01, expectancy=-1.0)
    strong_same_cluster = _summary(
        "b-strong",
        total_return=0.02,
        expectancy=2.0,
        benchmark_delta=0.01,
        trades=30,
    )
    too_sparse = _summary("c-sparse", total_return=0.03, expectancy=3.0, trades=4)
    second_cluster = _summary(
        "d-second",
        total_return=0.01,
        expectancy=1.5,
        benchmark_delta=0.006,
        trades=18,
    )
    campaign = _campaign(
        (negative_first, strong_same_cluster, too_sparse, second_cluster),
        (
            BehavioralClusterAccounting(
                representative_candidate_id="a-negative",
                member_candidate_ids=("a-negative", "b-strong"),
                family_ids=("family",),
            ),
            BehavioralClusterAccounting(
                representative_candidate_id="c-sparse",
                member_candidate_ids=("c-sparse",),
                family_ids=("family",),
            ),
            BehavioralClusterAccounting(
                representative_candidate_id="d-second",
                member_candidate_ids=("d-second",),
                family_ids=("family",),
            ),
        ),
    )
    assert select_d0_pilot_survivors(campaign) == ("b-strong", "d-second")


def test_selection_never_uses_diversity_to_rescue_negative_economics() -> None:
    negative = _summary(
        "negative",
        total_return=-0.001,
        expectancy=-0.1,
        benchmark_delta=0.02,
        trades=100,
    )
    campaign = _campaign(
        (negative,),
        (
            BehavioralClusterAccounting(
                representative_candidate_id="negative",
                member_candidate_ids=("negative",),
                family_ids=("family",),
            ),
        ),
    )
    assert select_d0_pilot_survivors(campaign) == ()
