from __future__ import annotations

import json
from pathlib import Path

from eba_trader.sfv2_dashboard import read_sfv2_d0_postmortem
from eba_trader.strategy_factory_v2_pilot import LowFidelityCandidateSummary
from eba_trader.strategy_factory_v2_postmortem import (
    POSTMORTEM_SCHEMA,
    _candidate_failure_flags,
    _cost_proxies,
    _delay_observations,
    _primary_diagnosis,
)


def _summary(
    *,
    candidate_id: str = "dc_test",
    total_return: float = -0.001,
    expectancy: float = -1.0,
    trades: int = 20,
    benchmark_delta: float = -0.001,
    total_cost: float = 20.0,
) -> LowFidelityCandidateSummary:
    return LowFidelityCandidateSummary(
        candidate_id=candidate_id,
        family_id="family_v1",
        complete=True,
        rejected=False,
        stratum_count=12,
        mean_total_return=total_return,
        mean_expectancy=expectancy,
        total_trade_count=trades,
        mean_benchmark_relative_return=benchmark_delta,
        mean_max_drawdown=-0.01,
        mean_total_cost=total_cost,
        mean_exposure=0.1,
        mean_turnover=2.0,
        behavior=None,
    )


def test_cost_proxy_can_identify_cost_suppressed_negative_net() -> None:
    item = _summary(total_return=-0.001, total_cost=20.0)
    proxies = _cost_proxies(item)
    assert proxies["costRecoveredReturnProxy"] == 0.001
    assert "cost_sensitive_proxy" in _candidate_failure_flags(item)
    assert _primary_diagnosis(summaries=[item]) == "COST_SENSITIVE_PROXY"


def test_sparse_activity_is_not_relabelled_as_negative_edge() -> None:
    item = _summary(trades=4, total_return=0.01, expectancy=2.0, benchmark_delta=0.005)
    assert "sparse_activity" in _candidate_failure_flags(item)
    assert _primary_diagnosis(summaries=[item]) == "SPARSE_ACTIVITY"


def test_one_bar_delay_diagnostic_matches_preceding_signal() -> None:
    trial = {
        "behavior": {
            "signal_keys": ["0000000060000:+1"],
            "trade_keys": ["0000000120000:0000000180000:+1"],
        }
    }
    observations = _delay_observations(
        trial=trial,
        open_by_time={60_000: 100.0, 120_000: 101.0},
        step_ms=60_000,
    )
    assert observations == [100.0]


def _postmortem_payload() -> dict[str, object]:
    family = {
        "familyId": "mean_reversion_z_v1",
        "primaryDiagnosis": "NEGATIVE_NET_EDGE",
        "candidateCount": 64,
        "completeNonRejectedCandidateCount": 20,
        "rejectedOrIncompleteCandidateCount": 44,
        "adequateActivityCandidateCount": 10,
        "positiveNetCandidateCount": 0,
        "costSensitiveProxyCandidateCount": 1,
        "totalTradeCount": 100,
        "medianCandidateTradeCount": 10,
        "meanCandidateNetReturn": -0.001,
        "meanCandidateExpectancy": -2.0,
        "meanCandidateBenchmarkDelta": -0.001,
        "meanCandidateTotalCostUsd": 4.0,
        "failureFlagCounts": {"non_positive_net_return": 20},
        "rejectionReasonCounts": {"no_executed_trade_on_declared_d0_dataset": 44},
        "bestCandidate": {
            "candidateId": "dc_best",
            "meanNetReturn": -0.0005,
            "meanExpectancy": -1.0,
            "totalTradeCount": 23,
            "meanBenchmarkDelta": -0.001,
            "costRecoveredReturnProxy": 0.0001,
            "feeBurdenReturnProxy": 0.0004,
            "slippageBurdenReturnProxy": 0.0002,
            "failureFlags": ["non_positive_net_return"],
        },
        "oneBarDelayDiagnostic": {
            "matchedTradeCount": 20,
            "meanPreEntryDirectionalMoveBps": 1.0,
        },
        "regimeDiagnostics": {},
    }
    families = []
    for index in range(8):
        item = dict(family)
        item["familyId"] = f"family_{index}"
        families.append(item)
    return {
        "schema": POSTMORTEM_SCHEMA,
        "authority": "DISCOVERY_DIAGNOSTIC_ONLY",
        "campaignId": "sfv2-discovery-pilot-v1",
        "sourceCodeSha": "a" * 40,
        "analysisCodeSha": "b" * 40,
        "generatedAt": "2026-09-04T00:00:00Z",
        "candidateCount": 406,
        "familyCount": 8,
        "stratumCount": 12,
        "terminalTrialCount": 4872,
        "survivorCount": 0,
        "roundTripFrictionBps": 11.0,
        "failureFlagCounts": {"non_positive_net_return": 100},
        "familyDiagnosisCounts": {"NEGATIVE_NET_EDGE": 8},
        "oneBarDelayDiagnostic": {"matchedTradeCount": 100},
        "families": families,
        "freshConfirmationEvidence": False,
        "verificationAuthority": False,
        "d1Opened": False,
        "frozenOosOpened": False,
        "liveExecutionAllowed": False,
        "realExecutionAllowed": False,
    }


def test_dashboard_exposes_only_safe_closed_postmortem(tmp_path: Path) -> None:
    path = tmp_path / "postmortem.json"
    path.write_text(json.dumps(_postmortem_payload()), encoding="utf-8")
    summary = read_sfv2_d0_postmortem(postmortem_path=path)
    assert summary["available"] is True
    assert summary["candidateCount"] == 406
    assert summary["familyCount"] == 8
    assert summary["survivorCount"] == 0
    assert summary["d1Opened"] is False
    assert summary["realExecutionAllowed"] is False


def test_dashboard_rejects_postmortem_with_downstream_authority(tmp_path: Path) -> None:
    payload = _postmortem_payload()
    payload["d1Opened"] = True
    path = tmp_path / "postmortem.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    summary = read_sfv2_d0_postmortem(postmortem_path=path)
    assert summary["available"] is False
    assert summary["reason"] == "postmortem_safety_rejected"
