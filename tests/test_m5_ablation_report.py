from __future__ import annotations

import json
import sqlite3
from pathlib import Path

import pytest

from eba_trader.m5_ablation_report import (
    build_m5_real_ablation_report,
    write_immutable_report,
)


def _db(path: Path) -> None:
    with sqlite3.connect(path) as connection:
        connection.execute(
            """
            CREATE TABLE experiment_runs (
                experiment_id TEXT PRIMARY KEY,
                strategy_id TEXT NOT NULL,
                strategy_version INTEGER NOT NULL,
                stage TEXT NOT NULL,
                status TEXT NOT NULL,
                parameters_json TEXT NOT NULL,
                dataset_ref TEXT,
                evidence_ref TEXT,
                metrics_json TEXT NOT NULL,
                created_at TEXT,
                completed_at TEXT
            )
            """
        )
        rows = [
            (
                "exp_base",
                "BASE",
                1,
                "m5_orderflow_ablation_dev",
                "passed",
                "{}",
                "dataset.csv",
                "evidence/base.json",
                json.dumps({"return_pct": 1.0, "profit_factor": 1.1, "trades": 5}),
            ),
            (
                "exp_delta",
                "ORDERFLOW",
                1,
                "m5_orderflow_ablation_dev",
                "passed",
                json.dumps({"delta_ratio_threshold": 0.1}),
                "dataset.csv",
                "evidence/delta.json",
                json.dumps({"return_pct": 1.25, "profit_factor": 1.2, "trades": 4}),
            ),
        ]
        connection.executemany(
            """
            INSERT INTO experiment_runs(
                experiment_id, strategy_id, strategy_version, stage, status,
                parameters_json, dataset_ref, evidence_ref, metrics_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            rows,
        )


def _batch() -> dict:
    return {
        "batch_id": "abl_test",
        "workflow_id": "m5ds_test",
        "dataset_ref": "dataset.csv",
        "baseline_experiment_id": "exp_base",
        "experiment_ids": ["exp_base", "exp_delta"],
        "treatment_count": 1,
        "stage": "m5_orderflow_ablation_dev",
        "frozen_oos_opened": False,
        "live_execution_allowed": False,
    }


def test_report_compares_same_batch_without_granting_authority(tmp_path: Path) -> None:
    db = tmp_path / "research.db"
    _db(db)
    report = build_m5_real_ablation_report(db_path=db, batch=_batch())

    assert report["allTerminal"] is True
    assert report["allExperimentsPassed"] is True
    assert report["evidenceComplete"] is True
    assert report["developmentComparisonOnly"] is True
    assert report["edgeClaimAllowed"] is False
    assert report["promotionAuthority"] is False
    assert report["frozenOosOpened"] is False
    assert report["liveExecutionAllowed"] is False
    delta = report["treatments"][0]["metricDeltaVsBaseline"]
    assert delta["return_pct"] == pytest.approx(0.25)
    assert delta["profit_factor"] == pytest.approx(0.1)
    assert delta["trades"] == pytest.approx(-1.0)


def test_report_requires_every_experiment_and_is_immutable(tmp_path: Path) -> None:
    db = tmp_path / "research.db"
    _db(db)
    batch = _batch()
    batch["experiment_ids"].append("missing")
    with pytest.raises(RuntimeError, match="missing from research DB"):
        build_m5_real_ablation_report(db_path=db, batch=batch)

    report = build_m5_real_ablation_report(db_path=db, batch=_batch())
    path = write_immutable_report(tmp_path / "report.json", report)
    assert write_immutable_report(path, report) == path
    changed = dict(report)
    changed["allExperimentsPassed"] = False
    with pytest.raises(RuntimeError, match="immutable M5 ablation report collision"):
        write_immutable_report(path, changed)


def test_report_rejects_any_oos_or_live_authority(tmp_path: Path) -> None:
    db = tmp_path / "research.db"
    _db(db)
    batch = _batch()
    batch["frozen_oos_opened"] = True
    with pytest.raises(ValueError, match="frozen OOS must remain closed"):
        build_m5_real_ablation_report(db_path=db, batch=batch)

    batch = _batch()
    batch["live_execution_allowed"] = True
    with pytest.raises(ValueError, match="live execution must remain locked"):
        build_m5_real_ablation_report(db_path=db, batch=batch)
