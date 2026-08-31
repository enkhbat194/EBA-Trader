from __future__ import annotations

import json
from pathlib import Path

from eba_trader.sf2_dashboard import read_sf2_summary


def _write_bundle(root: Path) -> tuple[Path, Path]:
    evidence = root / "evidence"
    evidence.mkdir(parents=True)
    development_path = evidence / "sf2-development.json"
    validation_path = evidence / "sf2-validation.json"
    development = {
        "schema": "sf2_development_report_v1",
        "evaluationId": "sf2dev_x",
        "protocolId": "sf2protocol_x",
        "materializationId": "sf2mat_x",
        "candidateSetSha256": "a" * 64,
        "candidateCount": 24,
        "multipleTestingBudget": 48,
        "windowCount": 12,
        "developmentRanking": [
            {
                "developmentPriorityRank": 1,
                "candidateId": "s2_div_l001",
                "family": "divergence_reversal_v1",
                "parameters": {
                    "side": 1,
                    "signal_threshold": 0.01,
                    "apiSecret": "never-public",
                },
                "aggregate": {
                    "meanReturn": 0.01,
                    "meanExpectancy": 2.0,
                    "totalTradeCount": 31,
                    "datasetRef": "/private/data.csv",
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
        "schema": "sf2_validation_report_v1",
        "validationId": "sf2val_x",
        "developmentEvaluationId": "sf2dev_x",
        "protocolId": "sf2protocol_x",
        "materializationId": "sf2mat_x",
        "candidateSetSha256": "a" * 64,
        "candidateCount": 24,
        "multipleTestingBudget": 48,
        "windowCount": 12,
        "validationState": "NO_VERIFIED_CANDIDATE",
        "verifiedCandidateCount": 0,
        "topVerifiedCandidate": None,
        "candidateValidation": [
            {
                "candidateId": "s2_div_l001",
                "family": "divergence_reversal_v1",
                "parameters": {"side": 1, "signal_threshold": 0.01},
                "qualified": True,
                "verifiedForRobustness": False,
                "failedChecks": ["statisticalSignificance"],
                "checks": {"minimumTrades": 30},
                "windowCount": 12,
                "positiveDeltaWindowCount": 10,
                "observedMeanReturnDeltaVsBaseline": 0.002,
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
    development_path.write_text(json.dumps(development), encoding="utf-8")
    validation_path.write_text(json.dumps(validation), encoding="utf-8")
    status_path = root / "sf2-development-latest.json"
    status_path.write_text(
        json.dumps(
            {
                "schema": "sf2_runtime_status_v1",
                "phase": "COMPLETE",
                "complete": True,
                "safe": True,
                "protocolId": "sf2protocol_x",
                "materializationId": "sf2mat_x",
                "candidateSetSha256": "a" * 64,
                "candidateCount": 24,
                "multipleTestingBudget": 48,
                "windowCount": 12,
                "developmentEvaluationId": "sf2dev_x",
                "developmentReportPath": str(development_path),
                "validationId": "sf2val_x",
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
        ),
        encoding="utf-8",
    )
    return status_path, evidence


def test_sf2_summary_is_sanitized_and_read_only(tmp_path: Path) -> None:
    status_path, evidence = _write_bundle(tmp_path)

    result = read_sf2_summary(status_path=status_path, evidence_root=evidence)

    assert result["available"] is True
    assert result["candidateCount"] == 24
    assert result["multipleTestingBudget"] == 48
    assert result["windowCount"] == 12
    assert result["validationState"] == "NO_VERIFIED_CANDIDATE"
    assert result["topDevelopmentCandidate"] == "s2_div_l001"
    assert result["topDevelopmentAggregate"]["meanReturn"] == 0.01
    ranking = result["developmentRanking"][0]
    assert "apiSecret" not in ranking["parameters"]
    assert "datasetRef" not in ranking["aggregate"]
    validation = result["candidateValidation"][0]
    assert validation["verifiedForRobustness"] is False
    assert validation["adjustedPValue"] == 0.48
    assert result["frozenOosOpened"] is False
    assert result["m5FrozenOosOpened"] is False
    assert result["liveExecutionAllowed"] is False


def test_sf2_summary_rejects_unsafe_status(tmp_path: Path) -> None:
    status_path, evidence = _write_bundle(tmp_path)
    status = json.loads(status_path.read_text(encoding="utf-8"))
    status["liveExecutionAllowed"] = True
    status_path.write_text(json.dumps(status), encoding="utf-8")

    result = read_sf2_summary(status_path=status_path, evidence_root=evidence)

    assert result["available"] is False
    assert result["reason"] == "status_safety_rejected"
    assert result["liveExecutionAllowed"] is False


def test_sf2_summary_rejects_evidence_path_escape(tmp_path: Path) -> None:
    status_path, evidence = _write_bundle(tmp_path)
    outside = tmp_path / "outside.json"
    outside.write_text("{}", encoding="utf-8")
    status = json.loads(status_path.read_text(encoding="utf-8"))
    status["developmentReportPath"] = str(outside)
    status_path.write_text(json.dumps(status), encoding="utf-8")

    result = read_sf2_summary(status_path=status_path, evidence_root=evidence)

    assert result["available"] is False
    assert result["reason"] == "report_path_rejected"
