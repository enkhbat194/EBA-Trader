from pathlib import Path

import pytest

from eba_trader.m5_candidate_qualification import REPORT_SCHEMA as QUALIFICATION_SCHEMA
from eba_trader.m5_candidate_significance import (
    ALPHA,
    REPORT_SCHEMA,
    evaluate_candidate_significance,
    write_immutable_significance_report,
)
from eba_trader.m5_multiwindow import REPORT_SCHEMA as MULTIWINDOW_SCHEMA


def _reports(deltas: list[float], *, eligible: bool = True) -> tuple[dict, dict]:
    assert len(deltas) == 12
    baseline_windows = [
        {"windowName": f"w{index:02d}", "metrics": {"total_return": 0.01}}
        for index in range(12)
    ]
    target_windows = [
        {
            "windowName": f"w{index:02d}",
            "metrics": {"total_return": 0.01 + deltas[index]},
        }
        for index in range(12)
    ]
    candidates = [
        {
            "candidateId": "target",
            "parameters": {"absorption_threshold": 0.2},
            "windows": target_windows,
        }
    ]
    candidates.extend({"candidateId": f"other_{index:02d}"} for index in range(16))
    multi = {
        "schema": MULTIWINDOW_SCHEMA,
        "evaluationId": "eval-1",
        "materializationId": "mat-1",
        "candidateSetSha256": "a" * 64,
        "candidateCount": 17,
        "baseline": {"windows": baseline_windows},
        "candidates": candidates,
        "rankingIsDevelopmentOnly": True,
        "edgeClaimAllowed": False,
        "promotionAuthority": False,
        "frozenOosOpened": False,
        "m5FrozenOosOpened": False,
        "liveExecutionAllowed": False,
    }
    eligible_rows = (
        [
            {
                "developmentPriorityRank": 1,
                "candidateId": "target",
                "parameters": {"absorption_threshold": 0.2},
            }
        ]
        if eligible
        else []
    )
    qualification = {
        "schema": QUALIFICATION_SCHEMA,
        "qualificationId": "qual-1",
        "evaluationId": "eval-1",
        "materializationId": "mat-1",
        "candidateSetSha256": "a" * 64,
        "eligibleCandidateCount": len(eligible_rows),
        "eligibleCandidates": eligible_rows,
        "developmentEvidenceOnly": True,
        "edgeClaimAllowed": False,
        "promotionAuthority": False,
        "frozenOosOpened": False,
        "m5FrozenOosOpened": False,
        "liveExecutionAllowed": False,
    }
    return multi, qualification


def test_exact_sign_flip_gate_accepts_uniform_cross_window_advantage() -> None:
    multi, qualification = _reports([0.02] * 12)
    report = evaluate_candidate_significance(multi, qualification)

    assert report["schema"] == REPORT_SCHEMA
    assert report["significanceState"] == "SIGNIFICANT_CANDIDATE_AVAILABLE"
    assert report["significantCandidateCount"] == 1
    assert report["topSignificantCandidate"] == "target"
    row = report["candidateSignificance"][0]
    assert row["permutationCount"] == 4096
    assert row["rawPValue"] == pytest.approx(1 / 4096)
    assert row["adjustedPValue"] == pytest.approx(17 / 4096)
    assert row["adjustedPValue"] <= ALPHA
    assert row["statisticallySignificant"] is True
    assert report["frozenOosOpened"] is False
    assert report["liveExecutionAllowed"] is False


def test_significance_gate_rejects_no_systematic_advantage() -> None:
    multi, qualification = _reports([0.01, -0.01] * 6)
    report = evaluate_candidate_significance(multi, qualification)

    assert report["significanceState"] == "NO_SIGNIFICANT_CANDIDATE"
    assert report["significantCandidateCount"] == 0
    assert report["topSignificantCandidate"] is None
    row = report["candidateSignificance"][0]
    assert row["observedMeanReturnDeltaVsBaseline"] == pytest.approx(0.0)
    assert row["statisticallySignificant"] is False


def test_significance_gate_records_safe_no_eligible_candidate_state() -> None:
    multi, qualification = _reports([0.02] * 12, eligible=False)
    report = evaluate_candidate_significance(multi, qualification)

    assert report["eligibleCandidateCount"] == 0
    assert report["testedCandidateCount"] == 0
    assert report["significanceState"] == "NO_ELIGIBLE_CANDIDATE"
    assert report["topSignificantCandidate"] is None


def test_significance_gate_fails_closed_on_unsafe_input() -> None:
    multi, qualification = _reports([0.02] * 12)
    multi["m5FrozenOosOpened"] = True
    with pytest.raises(RuntimeError, match="development-only safety"):
        evaluate_candidate_significance(multi, qualification)


def test_significance_report_is_immutable(tmp_path: Path) -> None:
    multi, qualification = _reports([0.02] * 12)
    report = evaluate_candidate_significance(multi, qualification)
    path = tmp_path / "significance.json"
    assert write_immutable_significance_report(path, report) == path
    assert write_immutable_significance_report(path, report) == path
    changed = dict(report)
    changed["significanceState"] = "MUTATED"
    with pytest.raises(RuntimeError, match="refusing to overwrite"):
        write_immutable_significance_report(path, changed)
