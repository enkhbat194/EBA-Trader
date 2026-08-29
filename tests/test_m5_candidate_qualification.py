from __future__ import annotations

from eba_trader.m5_candidate_qualification import (
    MIN_BEAT_BASELINE_WINDOWS,
    MIN_ROBUSTNESS_TRADES,
    evaluate_candidate_qualification,
    qualify_aggregate,
)
from eba_trader.m5_multiwindow import REPORT_SCHEMA as MULTIWINDOW_REPORT_SCHEMA


def _aggregate(
    *,
    mean_return: float,
    mean_expectancy: float,
    trades: int,
    beat_windows: int,
) -> dict[str, float | int]:
    return {
        "windowCount": 12,
        "meanReturn": mean_return,
        "medianReturn": 0.0,
        "worstWindowReturn": min(0.0, mean_return),
        "bestWindowReturn": max(0.0, mean_return),
        "positiveWindowCount": 2 if mean_return <= 0 else 9,
        "beatBaselineWindowCount": beat_windows,
        "notWorseThanBaselineWindowCount": beat_windows,
        "meanReturnDeltaVsBaseline": 0.005,
        "medianReturnDeltaVsBaseline": 0.004,
        "worstReturnDeltaVsBaseline": -0.001,
        "bestReturnDeltaVsBaseline": 0.01,
        "meanExpectancy": mean_expectancy,
        "worstMaxDrawdown": -0.003,
        "totalTradeCount": trades,
        "totalCost": float(trades) * 10.0,
    }


def _report(rows: list[dict[str, object]]) -> dict[str, object]:
    return {
        "schema": MULTIWINDOW_REPORT_SCHEMA,
        "evaluationId": "m5multi_test",
        "materializationId": "m5corpusmat_test",
        "candidateSetSha256": "a" * 64,
        "candidateCount": len(rows),
        "developmentRanking": rows,
        "rankingIsDevelopmentOnly": True,
        "edgeClaimAllowed": False,
        "promotionAuthority": False,
        "frozenOosOpened": False,
        "m5FrozenOosOpened": False,
        "liveExecutionAllowed": False,
    }


def test_sparse_baseline_beater_is_not_robustness_eligible() -> None:
    # Mirrors the production absorption_020 failure mode: it beats a weak baseline
    # in many windows, but only trades four times and remains negative overall.
    result = qualify_aggregate(
        _aggregate(
            mean_return=-0.00009114069527957347,
            mean_expectancy=-0.911406952795763,
            trades=4,
            beat_windows=11,
        )
    )

    assert result["eligibleForRobustness"] is False
    assert result["checks"]["profitable"] is False
    assert result["checks"]["sampleSufficient"] is False
    assert result["checks"]["baselineCoverageSufficient"] is True
    assert result["failedChecks"] == ["profitable", "sampleSufficient"]


def test_positive_adequately_sampled_candidate_is_eligible() -> None:
    result = qualify_aggregate(
        _aggregate(
            mean_return=0.002,
            mean_expectancy=4.5,
            trades=36,
            beat_windows=9,
        )
    )

    assert result["eligibleForRobustness"] is True
    assert result["failedChecks"] == []
    assert result["checks"]["minimumTrades"] == MIN_ROBUSTNESS_TRADES == 30
    assert (
        result["checks"]["minimumBeatBaselineWindows"]
        == MIN_BEAT_BASELINE_WINDOWS
        == 9
    )


def test_report_keeps_diagnostic_ranking_but_returns_only_qualified_candidates() -> None:
    sparse = {
        "developmentPriorityRank": 1,
        "candidateId": "absorption_020",
        "parameters": {"absorption_threshold": 0.2},
        "aggregate": _aggregate(
            mean_return=-0.0001,
            mean_expectancy=-1.0,
            trades=4,
            beat_windows=11,
        ),
    }
    qualified = {
        "developmentPriorityRank": 2,
        "candidateId": "candidate_positive",
        "parameters": {"delta_ratio_threshold": 0.2},
        "aggregate": _aggregate(
            mean_return=0.002,
            mean_expectancy=2.0,
            trades=36,
            beat_windows=10,
        ),
    }

    result = evaluate_candidate_qualification(_report([sparse, qualified]))

    assert result["candidateCount"] == 2
    assert result["eligibleCandidateCount"] == 1
    assert result["topEligibleCandidate"] == "candidate_positive"
    assert result["qualificationState"] == "ELIGIBLE_CANDIDATE_AVAILABLE"
    assert result["candidateQualifications"][0]["candidateId"] == "absorption_020"
    assert (
        result["candidateQualifications"][0]["qualification"]["eligibleForRobustness"]
        is False
    )
    assert result["eligibleCandidates"][0]["candidateId"] == "candidate_positive"
    assert result["developmentEvidenceOnly"] is True
    assert result["edgeClaimAllowed"] is False
    assert result["promotionAuthority"] is False
    assert result["m5FrozenOosOpened"] is False
    assert result["liveExecutionAllowed"] is False


def test_no_candidate_is_forced_when_all_development_candidates_fail() -> None:
    rows = [
        {
            "developmentPriorityRank": 1,
            "candidateId": "absorption_020",
            "parameters": {"absorption_threshold": 0.2},
            "aggregate": _aggregate(
                mean_return=-0.0001,
                mean_expectancy=-0.9,
                trades=4,
                beat_windows=11,
            ),
        },
        {
            "developmentPriorityRank": 2,
            "candidateId": "delta_020",
            "parameters": {"delta_ratio_threshold": 0.2},
            "aggregate": _aggregate(
                mean_return=-0.003,
                mean_expectancy=-12.0,
                trades=33,
                beat_windows=7,
            ),
        },
    ]

    result = evaluate_candidate_qualification(_report(rows))

    assert result["eligibleCandidateCount"] == 0
    assert result["eligibleCandidates"] == []
    assert result["topEligibleCandidate"] is None
    assert result["topEligibleParameters"] is None
    assert result["qualificationState"] == "NO_ELIGIBLE_CANDIDATE"
