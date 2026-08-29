from __future__ import annotations

from pathlib import Path

import pytest

from eba_trader.sf1_strategy_factory import (
    EXPECTED_SEARCH_BUDGET,
    EXPECTED_WARMUP_BARS,
    load_sf1_candidates,
)
from eba_trader.sf1_strategy_factory import (
    REPORT_SCHEMA as DEVELOPMENT_SCHEMA,
)
from eba_trader.sf1_validation import ALPHA, REPORT_SCHEMA, validate_sf1_development

ROOT = Path(__file__).resolve().parents[1]


def _development_report(deltas: list[float], *, unsafe: bool = False) -> dict:
    assert len(deltas) == 12
    baseline_windows = [
        {"windowName": f"w{index:02d}", "metrics": {"total_return": 0.01}}
        for index in range(12)
    ]
    candidate_windows = [
        {
            "windowName": f"w{index:02d}",
            "metrics": {"total_return": 0.01 + deltas[index]},
        }
        for index in range(12)
    ]
    mean_return = sum(0.01 + value for value in deltas) / 12
    return {
        "schema": DEVELOPMENT_SCHEMA,
        "evaluationId": "sf1eval-test",
        "phaseId": "sf1_independent_families_v1",
        "materializationId": "mat-test",
        "candidateSetSha256": "c" * 64,
        "candidateCount": 1,
        "multipleTestingBudget": 48,
        "warmupBars": 64,
        "windowCount": 12,
        "baseline": {"windows": baseline_windows},
        "candidates": [
            {
                "candidateId": "atr-test",
                "family": "atr_trailing_v1",
                "parameters": {"atr_period": 14, "atr_multiplier": 2.0},
                "windows": candidate_windows,
                "aggregate": {
                    "meanReturn": mean_return,
                    "meanExpectancy": 12.0,
                    "totalTradeCount": 60,
                    "beatBaselineWindowCount": sum(value > 0.0 for value in deltas),
                },
            }
        ],
        "developmentRanking": [],
        "rankingIsDevelopmentOnly": True,
        "developmentEvidenceOnly": True,
        "edgeClaimAllowed": False,
        "promotionAuthority": False,
        "frozenOosOpened": False,
        "m5FrozenOosOpened": unsafe,
        "liveExecutionAllowed": False,
    }


def test_sf1_candidate_set_preregisters_full_search_budget() -> None:
    budget, warmup, candidates = load_sf1_candidates(ROOT / "config/sf1_candidate_set_v1.json")
    assert budget == EXPECTED_SEARCH_BUDGET == 48
    assert warmup == EXPECTED_WARMUP_BARS == 64
    assert len(candidates) == 12
    assert {candidate.family for candidate in candidates} == {"atr_trailing_v1"}
    assert len({candidate.candidate_id for candidate in candidates}) == len(candidates)


def test_sf1_strong_cross_window_candidate_passes_budget_corrected_significance() -> None:
    report = validate_sf1_development(_development_report([0.02] * 12))
    assert report["schema"] == REPORT_SCHEMA
    assert report["validationState"] == "VERIFIED_CANDIDATE_AVAILABLE"
    assert report["verifiedCandidateCount"] == 1
    row = report["candidateValidation"][0]
    assert row["permutationCount"] == 4096
    assert row["rawPValue"] == pytest.approx(1 / 4096)
    assert row["adjustedPValue"] == pytest.approx(48 / 4096)
    assert row["adjustedPValue"] <= ALPHA
    assert row["verifiedForRobustness"] is True
    assert report["m5FrozenOosOpened"] is False
    assert report["liveExecutionAllowed"] is False


def test_sf1_uses_preregistered_budget_not_current_candidate_count() -> None:
    report = validate_sf1_development(_development_report([0.02] * 12))
    row = report["candidateValidation"][0]
    assert report["candidateCount"] == 1
    assert row["multipleTestingBudget"] == 48
    assert row["adjustedPValue"] == pytest.approx(row["rawPValue"] * 48)


def test_sf1_rejects_candidate_without_systematic_advantage() -> None:
    report = validate_sf1_development(_development_report([0.01, -0.01] * 6))
    assert report["validationState"] == "NO_VERIFIED_CANDIDATE"
    row = report["candidateValidation"][0]
    assert row["verifiedForRobustness"] is False
    assert "baselineCoverageSufficient" in row["failedChecks"]


def test_sf1_validation_fails_closed_if_oos_is_open() -> None:
    with pytest.raises(RuntimeError, match="unsafe SF1 development evidence"):
        validate_sf1_development(_development_report([0.02] * 12, unsafe=True))
