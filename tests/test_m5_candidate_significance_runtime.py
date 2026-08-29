import json
from pathlib import Path

from eba_trader.m5_candidate_qualification import REPORT_SCHEMA as QUALIFICATION_REPORT_SCHEMA
from eba_trader.m5_candidate_qualification_runtime import (
    STATUS_SCHEMA as QUALIFICATION_STATUS_SCHEMA,
)
from eba_trader.m5_candidate_significance_runtime import (
    STATUS_SCHEMA,
    run_candidate_significance,
)
from eba_trader.m5_multiwindow import REPORT_SCHEMA as MULTIWINDOW_REPORT_SCHEMA
from eba_trader.m5_multiwindow_runtime import STATUS_SCHEMA as MULTIWINDOW_STATUS_SCHEMA


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


def _prepare_inputs(
    root: Path,
    *,
    eligible: bool,
    deltas: list[float] | None = None,
) -> tuple[Path, Path]:
    research_root = root / "research"
    evidence = research_root / "evidence"
    evidence.mkdir(parents=True)
    deltas = deltas or [0.02] * 12
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
    multi_report = {
        "schema": MULTIWINDOW_REPORT_SCHEMA,
        "evaluationId": "eval-runtime",
        "materializationId": "mat-runtime",
        "candidateSetSha256": "b" * 64,
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
    qualification_report = {
        "schema": QUALIFICATION_REPORT_SCHEMA,
        "qualificationId": "qual-runtime",
        "evaluationId": "eval-runtime",
        "materializationId": "mat-runtime",
        "candidateSetSha256": "b" * 64,
        "eligibleCandidateCount": len(eligible_rows),
        "eligibleCandidates": eligible_rows,
        "developmentEvidenceOnly": True,
        "edgeClaimAllowed": False,
        "promotionAuthority": False,
        "frozenOosOpened": False,
        "m5FrozenOosOpened": False,
        "liveExecutionAllowed": False,
    }
    multi_report_path = evidence / "multi.json"
    qualification_report_path = evidence / "qualification.json"
    _write_json(multi_report_path, multi_report)
    _write_json(qualification_report_path, qualification_report)

    multi_status_path = research_root / "m5-multiwindow-evaluation-latest.json"
    qualification_status_path = research_root / "m5-robustness-qualification-latest.json"
    _write_json(
        multi_status_path,
        {
            "schema": MULTIWINDOW_STATUS_SCHEMA,
            "phase": "COMPLETE",
            "complete": True,
            "safe": True,
            "evaluationId": "eval-runtime",
            "materializationId": "mat-runtime",
            "candidateSetSha256": "b" * 64,
            "reportPath": str(multi_report_path),
            "rankingIsDevelopmentOnly": True,
            "edgeClaimAllowed": False,
            "promotionAuthority": False,
            "frozenOosOpened": False,
            "m5FrozenOosOpened": False,
            "liveExecutionAllowed": False,
        },
    )
    _write_json(
        qualification_status_path,
        {
            "schema": QUALIFICATION_STATUS_SCHEMA,
            "phase": "COMPLETE",
            "complete": True,
            "safe": True,
            "evaluationId": "eval-runtime",
            "materializationId": "mat-runtime",
            "qualificationId": "qual-runtime",
            "reportPath": str(qualification_report_path),
            "developmentEvidenceOnly": True,
            "edgeClaimAllowed": False,
            "promotionAuthority": False,
            "frozenOosOpened": False,
            "m5FrozenOosOpened": False,
            "liveExecutionAllowed": False,
        },
    )
    return multi_status_path, qualification_status_path


def test_runtime_records_safe_no_eligible_candidate(tmp_path: Path) -> None:
    multi, qualification = _prepare_inputs(tmp_path, eligible=False)
    research_root = tmp_path / "research"
    status = run_candidate_significance(
        research_root=research_root,
        multiwindow_status_path=multi,
        qualification_status_path=qualification,
    )

    assert status["schema"] == STATUS_SCHEMA
    assert status["phase"] == "COMPLETE"
    assert status["complete"] is True
    assert status["safe"] is True
    assert status["significanceState"] == "NO_ELIGIBLE_CANDIDATE"
    assert status["significanceVerified"] is False
    assert status["topSignificantCandidate"] is None
    assert Path(status["reportPath"]).is_file()
    assert status["frozenOosOpened"] is False
    assert status["liveExecutionAllowed"] is False


def test_runtime_verifies_strong_exact_window_evidence_and_reuses_it(tmp_path: Path) -> None:
    multi, qualification = _prepare_inputs(tmp_path, eligible=True, deltas=[0.02] * 12)
    research_root = tmp_path / "research"
    first = run_candidate_significance(
        research_root=research_root,
        multiwindow_status_path=multi,
        qualification_status_path=qualification,
    )
    second = run_candidate_significance(
        research_root=research_root,
        multiwindow_status_path=multi,
        qualification_status_path=qualification,
    )

    assert first == second
    assert first["significanceVerified"] is True
    assert first["significanceState"] == "SIGNIFICANT_CANDIDATE_AVAILABLE"
    assert first["topSignificantCandidate"] == "target"
    assert first["significantCandidateCount"] == 1
