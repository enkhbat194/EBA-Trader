from __future__ import annotations

import json
from pathlib import Path

import pytest

from eba_trader.m5_candidate_activity_runtime import (
    STATUS_SCHEMA,
    run_candidate_activity_diagnostics,
)
from eba_trader.m5_multiwindow import REPORT_SCHEMA
from eba_trader.m5_multiwindow_runtime import STATUS_SCHEMA as MULTIWINDOW_STATUS_SCHEMA


def _metrics(trades: int, total_return: float) -> dict[str, float | int]:
    return {
        "trade_count": trades,
        "total_return": total_return,
        "expectancy": 0.0,
        "exposure": 0.0,
    }


def _write_fixture(root: Path) -> None:
    evidence = root / "evidence"
    evidence.mkdir(parents=True)
    report_path = evidence / "multiwindow.json"
    report = {
        "schema": REPORT_SCHEMA,
        "evaluationId": "eval_1",
        "materializationId": "mat_1",
        "rankingIsDevelopmentOnly": True,
        "edgeClaimAllowed": False,
        "promotionAuthority": False,
        "frozenOosOpened": False,
        "m5FrozenOosOpened": False,
        "liveExecutionAllowed": False,
        "baseline": {
            "windows": [
                {"windowName": "w1", "metrics": _metrics(5, -0.1)},
                {"windowName": "w2", "metrics": _metrics(5, -0.1)},
            ],
            "aggregate": {"totalTradeCount": 10},
        },
        "candidates": [
            {
                "candidateId": "absorption_020",
                "parameters": {"absorption_threshold": 0.2},
                "windows": [
                    {"windowName": "w1", "metrics": _metrics(1, 0.0)},
                    {"windowName": "w2", "metrics": _metrics(0, 0.0)},
                ],
                "aggregate": {"totalTradeCount": 1},
            }
        ],
    }
    report_path.write_text(json.dumps(report), encoding="utf-8")
    status = {
        "schema": MULTIWINDOW_STATUS_SCHEMA,
        "phase": "COMPLETE",
        "complete": True,
        "safe": True,
        "rankingIsDevelopmentOnly": True,
        "edgeClaimAllowed": False,
        "promotionAuthority": False,
        "frozenOosOpened": False,
        "m5FrozenOosOpened": False,
        "liveExecutionAllowed": False,
        "topDevelopmentCandidate": "absorption_020",
        "reportPath": str(report_path),
    }
    (root / "m5-multiwindow-evaluation-latest.json").write_text(
        json.dumps(status),
        encoding="utf-8",
    )


def test_runtime_writes_safe_activity_status_and_immutable_report(tmp_path: Path) -> None:
    _write_fixture(tmp_path)

    result = run_candidate_activity_diagnostics(research_root=tmp_path)

    assert result["schema"] == STATUS_SCHEMA
    assert result["phase"] == "COMPLETE"
    assert result["complete"] is True
    assert result["safe"] is True
    assert result["candidateId"] == "absorption_020"
    assert result["activeTradeWindows"] == ["w1"]
    assert result["candidateTradeCount"] == 1
    assert result["sampleSufficientForRobustness"] is False
    assert result["independentSignalGenerator"] is False
    assert result["m5FrozenOosOpened"] is False
    assert result["liveExecutionAllowed"] is False
    assert Path(result["reportPath"]).is_file()


def test_runtime_rejects_report_outside_evidence_root(tmp_path: Path) -> None:
    _write_fixture(tmp_path)
    status_path = tmp_path / "m5-multiwindow-evaluation-latest.json"
    status = json.loads(status_path.read_text(encoding="utf-8"))
    outside = tmp_path / "outside.json"
    outside.write_text("{}", encoding="utf-8")
    status["reportPath"] = str(outside)
    status_path.write_text(json.dumps(status), encoding="utf-8")

    with pytest.raises(RuntimeError, match="escapes the evidence root"):
        run_candidate_activity_diagnostics(research_root=tmp_path)

    failed = json.loads((tmp_path / "m5-candidate-activity-latest.json").read_text())
    assert failed["phase"] == "FAILED"
    assert failed["safe"] is True
    assert failed["m5FrozenOosOpened"] is False
    assert failed["liveExecutionAllowed"] is False
