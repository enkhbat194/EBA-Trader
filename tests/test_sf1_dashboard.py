from __future__ import annotations

import json
from pathlib import Path

from eba_trader.sf1_dashboard import read_sf1_summary


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


def _fixture(tmp_path: Path) -> tuple[Path, Path]:
    evidence = tmp_path / "evidence"
    development_path = evidence / "sf1-development-test.json"
    validation_path = evidence / "sf1-validation-test.json"
    status_path = tmp_path / "sf1-development-latest.json"

    development = {
        "schema": "sf1_development_report_v1",
        "evaluationId": "sf1eval-test",
        "phaseId": "sf1_independent_families_v1",
        "materializationId": "mat-test",
        "candidateSetSha256": "a" * 64,
        "candidateCount": 12,
        "multipleTestingBudget": 48,
        "warmupBars": 64,
        "windowCount": 12,
        "developmentRanking": [
            {
                "developmentPriorityRank": 1,
                "candidateId": "atr_14x200",
                "family": "atr_trailing_v1",
                "parameters": {"atr_period": 14, "atr_multiplier": 2.0},
                "aggregate": {
                    "meanReturn": 0.012,
                    "meanExpectancy": 9.5,
                    "totalTradeCount": 44,
                    "beatBaselineWindowCount": 10,
                    "privatePath": "/must/not/leak",
                },
            }
        ],
        "developmentEvidenceOnly": True,
        "edgeClaimAllowed": False,
        "promotionAuthority": False,
        "frozenOosOpened": False,
        "m5FrozenOosOpened": False,
        "liveExecutionAllowed": False,
    }
    validation = {
        "schema": "sf1_validation_report_v1",
        "validationId": "sf1val-test",
        "developmentEvaluationId": "sf1eval-test",
        "materializationId": "mat-test",
        "candidateSetSha256": "a" * 64,
        "candidateCount": 12,
        "multipleTestingBudget": 48,
        "windowCount": 12,
        "validationState": "NO_VERIFIED_CANDIDATE",
        "verifiedCandidateCount": 0,
        "topVerifiedCandidate": None,
        "candidateValidation": [
            {
                "candidateId": "atr_14x200",
                "family": "atr_trailing_v1",
                "parameters": {"atr_period": 14, "atr_multiplier": 2.0},
                "qualified": True,
                "verifiedForRobustness": False,
                "failedChecks": ["statisticalSignificance"],
                "checks": {
                    "profitable": True,
                    "sampleSufficient": True,
                    "baselineCoverageSufficient": True,
                    "minimumTrades": 30,
                },
                "windowCount": 12,
                "positiveDeltaWindowCount": 10,
                "observedMeanReturnDeltaVsBaseline": 0.006,
                "rawPValue": 0.01,
                "adjustedPValue": 0.48,
                "multipleTestingBudget": 48,
                "permutationCount": 4096,
            }
        ],
        "developmentEvidenceOnly": True,
        "edgeClaimAllowed": False,
        "promotionAuthority": False,
        "frozenOosOpened": False,
        "m5FrozenOosOpened": False,
        "liveExecutionAllowed": False,
    }
    status = {
        "schema": "sf1_runtime_status_v1",
        "phase": "COMPLETE",
        "complete": True,
        "safe": True,
        "materializationId": "mat-test",
        "candidateSetSha256": "a" * 64,
        "candidateCount": 12,
        "multipleTestingBudget": 48,
        "warmupBars": 64,
        "windowCount": 12,
        "developmentEvaluationId": "sf1eval-test",
        "developmentReportPath": str(development_path),
        "validationId": "sf1val-test",
        "validationReportPath": str(validation_path),
        "validationState": "NO_VERIFIED_CANDIDATE",
        "verifiedCandidateCount": 0,
        "topVerifiedCandidate": None,
        "developmentEvidenceOnly": True,
        "edgeClaimAllowed": False,
        "promotionAuthority": False,
        "frozenOosOpened": False,
        "m5FrozenOosOpened": False,
        "liveExecutionAllowed": False,
    }
    _write_json(development_path, development)
    _write_json(validation_path, validation)
    _write_json(status_path, status)
    return status_path, evidence


def test_sf1_summary_exposes_only_sanitized_validation_and_ranking(tmp_path: Path) -> None:
    status_path, evidence = _fixture(tmp_path)
    summary = read_sf1_summary(status_path=status_path, evidence_root=evidence)

    assert summary["available"] is True
    assert summary["candidateCount"] == 12
    assert summary["multipleTestingBudget"] == 48
    assert summary["windowCount"] == 12
    assert summary["validationState"] == "NO_VERIFIED_CANDIDATE"
    assert summary["topDevelopmentCandidate"] == "atr_14x200"
    assert summary["topDevelopmentAggregate"]["meanReturn"] == 0.012
    assert summary["candidateValidation"][0]["adjustedPValue"] == 0.48
    assert summary["candidateValidation"][0]["failedChecks"] == [
        "statisticalSignificance"
    ]
    assert "privatePath" in summary["topDevelopmentAggregate"]
    assert "developmentReportPath" not in summary
    assert "validationReportPath" not in summary
    assert summary["frozenOosOpened"] is False
    assert summary["m5FrozenOosOpened"] is False
    assert summary["liveExecutionAllowed"] is False


def test_sf1_summary_rejects_report_outside_evidence_root(tmp_path: Path) -> None:
    status_path, evidence = _fixture(tmp_path)
    payload = json.loads(status_path.read_text(encoding="utf-8"))
    outside = tmp_path / "outside.json"
    _write_json(outside, {"schema": "sf1_validation_report_v1"})
    payload["validationReportPath"] = str(outside)
    _write_json(status_path, payload)

    summary = read_sf1_summary(status_path=status_path, evidence_root=evidence)
    assert summary["available"] is False
    assert summary["reason"] == "report_path_rejected"
    assert summary["liveExecutionAllowed"] is False


def test_sf1_summary_rejects_unsafe_status(tmp_path: Path) -> None:
    status_path, evidence = _fixture(tmp_path)
    payload = json.loads(status_path.read_text(encoding="utf-8"))
    payload["m5FrozenOosOpened"] = True
    _write_json(status_path, payload)

    summary = read_sf1_summary(status_path=status_path, evidence_root=evidence)
    assert summary["available"] is False
    assert summary["reason"] == "status_safety_rejected"
    assert summary["m5FrozenOosOpened"] is False
