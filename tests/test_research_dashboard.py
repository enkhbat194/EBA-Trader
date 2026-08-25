from __future__ import annotations

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
