from __future__ import annotations

import json
from pathlib import Path

from eba_trader import m5_candidate_qualification_runtime as runtime
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
        "totalCost": float(trades),
    }


def _write_multiwindow_state(research_root: Path) -> Path:
    evidence = research_root / "evidence"
    evidence.mkdir(parents=True, exist_ok=True)
    report_path = evidence / "m5-multiwindow-development-test.json"
    report = {
        "schema": MULTIWINDOW_REPORT_SCHEMA,
        "evaluationId": "m5multi_test",
        "materializationId": "m5corpusmat_test",
        "candidateSetSha256": "a" * 64,
        "candidateCount": 2,
        "developmentRanking": [
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
        ],
        "rankingIsDevelopmentOnly": True,
        "edgeClaimAllowed": False,
        "promotionAuthority": False,
        "frozenOosOpened": False,
        "m5FrozenOosOpened": False,
        "liveExecutionAllowed": False,
    }
    report_path.write_text(json.dumps(report), encoding="utf-8")

    status_path = research_root / "m5-multiwindow-evaluation-latest.json"
    status = {
        "schema": "m5_multiwindow_runtime_status_v1",
        "phase": "COMPLETE",
        "complete": True,
        "safe": True,
        "evaluationId": "m5multi_test",
        "materializationId": "m5corpusmat_test",
        "candidateSetSha256": "a" * 64,
        "reportPath": str(report_path),
        "rankingIsDevelopmentOnly": True,
        "edgeClaimAllowed": False,
        "promotionAuthority": False,
        "frozenOosOpened": False,
        "m5FrozenOosOpened": False,
        "liveExecutionAllowed": False,
    }
    status_path.write_text(json.dumps(status), encoding="utf-8")
    return status_path


def test_runtime_writes_safe_no_eligible_candidate_terminal_state(tmp_path: Path) -> None:
    research_root = tmp_path / "research"
    multiwindow_status = _write_multiwindow_state(research_root)
    status_path = research_root / "m5-robustness-qualification-latest.json"

    result = runtime.run_candidate_qualification(
        research_root=research_root,
        multiwindow_status_path=multiwindow_status,
        status_path=status_path,
    )

    assert result["phase"] == "COMPLETE"
    assert result["complete"] is True
    assert result["safe"] is True
    assert result["qualificationState"] == "NO_ELIGIBLE_CANDIDATE"
    assert result["eligibleCandidateCount"] == 0
    assert result["topEligibleCandidate"] is None
    assert result["policy"]["minimumTrades"] == 30
    assert result["policy"]["minimumBeatBaselineWindows"] == 9
    assert result["developmentEvidenceOnly"] is True
    assert result["edgeClaimAllowed"] is False
    assert result["promotionAuthority"] is False
    assert result["m5FrozenOosOpened"] is False
    assert result["liveExecutionAllowed"] is False
    report_path = Path(str(result["reportPath"]))
    report = json.loads(report_path.read_text(encoding="utf-8"))
    assert report["eligibleCandidateCount"] == 0
    assert report["candidateQualifications"][0]["candidateId"] == "absorption_020"


def test_runtime_reuses_same_immutable_qualification_report(tmp_path: Path) -> None:
    research_root = tmp_path / "research"
    multiwindow_status = _write_multiwindow_state(research_root)
    status_path = research_root / "m5-robustness-qualification-latest.json"

    first = runtime.run_candidate_qualification(
        research_root=research_root,
        multiwindow_status_path=multiwindow_status,
        status_path=status_path,
    )
    first_report = Path(str(first["reportPath"])).read_text(encoding="utf-8")
    second = runtime.run_candidate_qualification(
        research_root=research_root,
        multiwindow_status_path=multiwindow_status,
        status_path=status_path,
    )

    assert second == first
    assert Path(str(second["reportPath"])).read_text(encoding="utf-8") == first_report
