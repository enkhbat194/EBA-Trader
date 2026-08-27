from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from eba_trader.research_dashboard import build_research_status


def _write_continuity(root: Path) -> None:
    (root / "PROJECT_STATE.md").write_text(
        "# State\n\n- AI Strategy Factory: **M5 IN PROGRESS**.\n",
        encoding="utf-8",
    )
    (root / "TODO.md").write_text(
        "# TODO\n\n"
        "## NOW — M5 AI Strategy Factory / Order-Flow Ablation\n\n"
        "- [x] Build causal feature dataset.\n"
        "- [ ] Run controlled candle-vs-footprint ablation.\n\n"
        "## NEXT\n\n- [ ] Later task.\n",
        encoding="utf-8",
    )


def _write_m5_report(path: Path, *, schema: str = "m5_real_ablation_report_v1") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {
                "schema": schema,
                "batchId": "abl-test",
                "workflowId": "wf-test",
                "stage": "m5_orderflow_ablation_dev",
                "treatmentCount": 1,
                "allTerminal": True,
                "allExperimentsPassed": True,
                "evidenceComplete": True,
                "developmentComparisonOnly": True,
                "edgeClaimAllowed": False,
                "promotionAuthority": False,
                "frozenOosOpened": False,
                "liveExecutionAllowed": False,
                "baseline": {
                    "experimentId": "EXP-BASE",
                    "strategyId": "STR-BASE",
                    "strategyVersion": 1,
                    "status": "passed",
                    "parameters": {"fast": 8, "apiSecret": "must-not-leak"},
                    "metrics": {"netReturn": 1.25, "tradeCount": 10},
                    "evidenceRef": "/private/evidence/base.json",
                    "completedAt": "2026-08-27T09:00:00Z",
                },
                "treatments": [
                    {
                        "experimentId": "EXP-DELTA",
                        "strategyId": "STR-DELTA",
                        "strategyVersion": 1,
                        "status": "passed",
                        "parameters": {"deltaRatioMin": 0.2},
                        "metrics": {"netReturn": 1.75, "tradeCount": 8},
                        "metricDeltaVsBaseline": {"netReturn": 0.5, "tradeCount": -2},
                        "evidenceRef": "/private/evidence/delta.json",
                        "completedAt": "2026-08-27T09:01:00Z",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )


def test_status_uses_repo_continuity_when_research_db_is_absent(tmp_path: Path) -> None:
    _write_continuity(tmp_path)

    status = build_research_status(root=tmp_path, db_path=tmp_path / "missing.db")

    assert status["stage"] == "M5 IN PROGRESS"
    assert status["focus"] == "Run controlled candle-vs-footprint ablation."
    assert status["progress"] == {"completed": 1, "remaining": 1}
    assert status["researchStore"]["available"] is False
    assert status["locks"]["frozenOos"] is True
    assert status["locks"]["realExecution"] is True
    assert status["ablation"]["baselineAdapter"] == "ema_feature_baseline_v1"
    assert status["ablation"]["orderflowAdapter"] == "ema_orderflow_v1"


def test_status_reads_existing_research_db_without_mutating_it(tmp_path: Path) -> None:
    _write_continuity(tmp_path)
    db_path = tmp_path / "research.db"
    connection = sqlite3.connect(db_path)
    try:
        connection.executescript(
            """
            CREATE TABLE strategies (
                strategy_id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                family TEXT,
                active_version INTEGER
            );
            CREATE TABLE strategy_versions (
                strategy_id TEXT NOT NULL,
                version INTEGER NOT NULL,
                lifecycle_state TEXT NOT NULL,
                spec_json TEXT NOT NULL,
                spec_sha256 TEXT NOT NULL,
                PRIMARY KEY(strategy_id, version)
            );
            CREATE TABLE experiment_runs (
                experiment_id TEXT PRIMARY KEY,
                strategy_id TEXT NOT NULL,
                strategy_version INTEGER NOT NULL,
                stage TEXT NOT NULL,
                status TEXT NOT NULL,
                parameters_json TEXT NOT NULL DEFAULT '{}',
                dataset_ref TEXT,
                evidence_ref TEXT,
                metrics_json TEXT NOT NULL DEFAULT '{}'
            );
            INSERT INTO strategies VALUES ('STR-1', 'Order Flow', 'orderflow', 1);
            INSERT INTO strategy_versions VALUES ('STR-1', 1, 'backtested', '{}', 'sha');
            INSERT INTO experiment_runs(
                experiment_id, strategy_id, strategy_version, stage, status
            ) VALUES
                ('EXP-1', 'STR-1', 1, 'development', 'passed'),
                ('EXP-2', 'STR-1', 1, 'development', 'queued');
            """
        )
        connection.commit()
    finally:
        connection.close()

    before_size = db_path.stat().st_size
    status = build_research_status(root=tmp_path, db_path=db_path)

    store = status["researchStore"]
    assert store["available"] is True
    assert store["strategies"] == 1
    assert store["versions"] == 1
    assert store["experiments"] == 2
    assert store["experimentStatus"] == {"passed": 1, "queued": 1}
    assert store["lifecycleStatus"] == {"backtested": 1}
    assert db_path.stat().st_size == before_size


def test_status_exposes_only_sanitized_m5_report_summary(tmp_path: Path) -> None:
    _write_continuity(tmp_path)
    evidence_root = tmp_path / "evidence"
    report_path = evidence_root / "m5-report.json"
    _write_m5_report(report_path)
    proof = {"m5RealAblation": {"reportPath": str(report_path)}}

    status = build_research_status(
        root=tmp_path,
        db_path=tmp_path / "missing.db",
        production_proof=proof,
        evidence_root=evidence_root,
    )

    report = status["m5Report"]
    assert report["available"] is True
    assert report["batchId"] == "abl-test"
    assert report["allTerminal"] is True
    assert report["evidenceComplete"] is True
    assert report["edgeClaimAllowed"] is False
    assert report["promotionAuthority"] is False
    assert report["frozenOosOpened"] is False
    assert report["liveExecutionAllowed"] is False
    assert report["baseline"]["metrics"]["netReturn"] == 1.25
    assert "apiSecret" not in report["baseline"]["parameters"]
    assert "evidenceRef" not in report["baseline"]
    treatment = report["treatments"][0]
    assert treatment["metricDeltaVsBaseline"]["netReturn"] == 0.5
    assert "evidenceRef" not in treatment


def test_status_rejects_m5_report_outside_evidence_root(tmp_path: Path) -> None:
    _write_continuity(tmp_path)
    evidence_root = tmp_path / "evidence"
    evidence_root.mkdir()
    report_path = tmp_path / "outside.json"
    _write_m5_report(report_path)
    proof = {"m5RealAblation": {"reportPath": str(report_path)}}

    status = build_research_status(
        root=tmp_path,
        db_path=tmp_path / "missing.db",
        production_proof=proof,
        evidence_root=evidence_root,
    )

    assert status["m5Report"]["available"] is False
    assert status["m5Report"]["reason"] == "report_path_rejected"
    assert status["m5Report"]["liveExecutionAllowed"] is False


def test_status_rejects_unknown_m5_report_schema(tmp_path: Path) -> None:
    _write_continuity(tmp_path)
    evidence_root = tmp_path / "evidence"
    report_path = evidence_root / "m5-report.json"
    _write_m5_report(report_path, schema="unexpected_schema")
    proof = {"m5RealAblation": {"reportPath": str(report_path)}}

    status = build_research_status(
        root=tmp_path,
        db_path=tmp_path / "missing.db",
        production_proof=proof,
        evidence_root=evidence_root,
    )

    assert status["m5Report"]["available"] is False
    assert status["m5Report"]["reason"] == "report_schema_rejected"
    assert status["m5Report"]["edgeClaimAllowed"] is False
