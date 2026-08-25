from __future__ import annotations

import os
import re
import sqlite3
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_RESEARCH_DB = PROJECT_ROOT / "artifacts" / "research" / "eba_research.db"


def _read_text(root: Path, name: str) -> str:
    path = root / name
    try:
        return path.read_text(encoding="utf-8")
    except OSError:
        return ""


def _first_unchecked_m5_task(todo_text: str) -> str:
    in_m5 = False
    for raw_line in todo_text.splitlines():
        line = raw_line.strip()
        if line.startswith("## NOW — M5"):
            in_m5 = True
            continue
        if in_m5 and line.startswith("## "):
            break
        if in_m5 and line.startswith("- [ ] "):
            return line[6:].strip().strip("`")
    return "No open M5 task recorded in TODO.md"


def _m5_progress(todo_text: str) -> dict[str, int]:
    in_m5 = False
    completed = 0
    remaining = 0
    for raw_line in todo_text.splitlines():
        line = raw_line.strip()
        if line.startswith("## NOW — M5"):
            in_m5 = True
            continue
        if in_m5 and line.startswith("## "):
            break
        if in_m5 and line.startswith("- [x] "):
            completed += 1
        elif in_m5 and line.startswith("- [ ] "):
            remaining += 1
    return {"completed": completed, "remaining": remaining}


def _current_stage(project_state: str) -> str:
    match = re.search(r"^- AI Strategy Factory:\s*\*\*(.+?)\*\*", project_state, re.MULTILINE)
    return match.group(1) if match else "M5 IN PROGRESS"


def _research_db_summary(path: Path) -> dict[str, Any]:
    summary: dict[str, Any] = {
        "available": False,
        "path": str(path),
        "strategies": 0,
        "versions": 0,
        "experiments": 0,
        "experimentStatus": {},
        "lifecycleStatus": {},
    }
    if not path.is_file():
        return summary

    uri = f"file:{path.resolve().as_posix()}?mode=ro"
    try:
        connection = sqlite3.connect(uri, uri=True, timeout=2)
        connection.row_factory = sqlite3.Row
        try:
            tables = {
                str(row[0])
                for row in connection.execute(
                    "SELECT name FROM sqlite_master WHERE type='table'"
                ).fetchall()
            }
            required = {"strategies", "strategy_versions", "experiment_runs"}
            if not required.issubset(tables):
                summary["error"] = "research database schema is incomplete"
                return summary

            summary["available"] = True
            summary["strategies"] = int(
                connection.execute("SELECT COUNT(*) FROM strategies").fetchone()[0]
            )
            summary["versions"] = int(
                connection.execute("SELECT COUNT(*) FROM strategy_versions").fetchone()[0]
            )
            summary["experiments"] = int(
                connection.execute("SELECT COUNT(*) FROM experiment_runs").fetchone()[0]
            )
            summary["experimentStatus"] = {
                str(row[0]): int(row[1])
                for row in connection.execute(
                    "SELECT status, COUNT(*) FROM experiment_runs GROUP BY status ORDER BY status"
                ).fetchall()
            }
            summary["lifecycleStatus"] = {
                str(row[0]): int(row[1])
                for row in connection.execute(
                    "SELECT lifecycle_state, COUNT(*) FROM strategy_versions "
                    "GROUP BY lifecycle_state ORDER BY lifecycle_state"
                ).fetchall()
            }
        finally:
            connection.close()
    except sqlite3.Error as exc:
        summary["error"] = f"research database read failed: {exc}"
    return summary


def build_research_status(
    *,
    root: str | Path = PROJECT_ROOT,
    db_path: str | Path | None = None,
) -> dict[str, Any]:
    """Build the read-only Research / AI Lab status payload for the PWA."""

    project_root = Path(root)
    project_state = _read_text(project_root, "PROJECT_STATE.md")
    todo = _read_text(project_root, "TODO.md")
    chosen_db = Path(
        db_path
        or os.getenv("EBA_RESEARCH_DB", "").strip()
        or project_root / "artifacts" / "research" / "eba_research.db"
    )

    return {
        "ok": True,
        "milestone": "M5",
        "stage": _current_stage(project_state),
        "focus": _first_unchecked_m5_task(todo),
        "progress": _m5_progress(todo),
        "dataPlane": {
            "venue": "Binance USD-M Futures",
            "symbol": "BTCUSDT",
            "footprintIntegrity": "READY",
            "causalAlignment": "READY",
            "featureDataset": "READY",
        },
        "ablation": {
            "status": "ADAPTER_READY",
            "baselineAdapter": "ema_feature_baseline_v1",
            "orderflowAdapter": "ema_orderflow_v1",
            "features": ["of_delta_ratio", "of_cvd"],
            "executionAssumptions": "shared dataset / fees / slippage / EMA exits",
        },
        "researchStore": _research_db_summary(chosen_db),
        "locks": {
            "frozenOos": True,
            "realExecution": True,
            "rankingHasLifecycleAuthority": False,
        },
        "sources": {
            "projectState": "PROJECT_STATE.md",
            "todo": "TODO.md",
        },
    }
