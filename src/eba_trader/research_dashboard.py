from __future__ import annotations

import json
import math
import os
import re
import sqlite3
from pathlib import Path
from typing import Any

from .production_proof import read_production_proof
from .sf1_dashboard import read_sf1_summary
from .sf2_dashboard import read_sf2_summary
from .sf3_dashboard import read_sf3_summary
from .sfv2_dashboard import read_sfv2_d0_summary
from .sfv2_next_d0_dashboard import read_sfv2_next_d0_materialization_summary

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_RESEARCH_DB = PROJECT_ROOT / "artifacts" / "research" / "eba_research.db"
DEFAULT_RESEARCH_EVIDENCE_ROOT = Path("/var/lib/eba-trader/research/evidence")
M5_REPORT_SCHEMA = "m5_real_ablation_report_v1"
_BLOCKED_REPORT_KEY_PARTS = (
    "apikey",
    "apisecret",
    "authorization",
    "bearer",
    "credential",
    "password",
    "secret",
    "signature",
    "token",
)


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


def _report_unavailable(reason: str) -> dict[str, Any]:
    return {
        "available": False,
        "reason": reason,
        "developmentComparisonOnly": True,
        "edgeClaimAllowed": False,
        "promotionAuthority": False,
        "frozenOosOpened": False,
        "liveExecutionAllowed": False,
    }


def _safe_report_map(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        return {}
    result: dict[str, Any] = {}
    for raw_key, item in value.items():
        key = str(raw_key)
        normalized = key.replace("_", "").replace("-", "").lower()
        if any(part in normalized for part in _BLOCKED_REPORT_KEY_PARTS):
            continue
        safe_scalar = (
            isinstance(item, (bool, int))
            or (isinstance(item, float) and math.isfinite(item))
            or (isinstance(item, str) and len(item) <= 256)
        )
        if safe_scalar:
            result[key] = item
    return result


def _safe_report_arm(value: Any, *, include_delta: bool = False) -> dict[str, Any]:
    if not isinstance(value, dict):
        return {}
    arm = {
        "experimentId": value.get("experimentId"),
        "strategyId": value.get("strategyId"),
        "strategyVersion": value.get("strategyVersion"),
        "status": value.get("status"),
        "parameters": _safe_report_map(value.get("parameters")),
        "metrics": _safe_report_map(value.get("metrics")),
        "completedAt": value.get("completedAt"),
    }
    if include_delta:
        arm["metricDeltaVsBaseline"] = _safe_report_map(
            value.get("metricDeltaVsBaseline")
        )
    return arm


def read_m5_report_summary(
    production_proof: dict[str, Any],
    *,
    evidence_root: str | Path | None = None,
) -> dict[str, Any]:
    marker = production_proof.get("m5RealAblation")
    if not isinstance(marker, dict):
        return _report_unavailable("marker_unavailable")
    report_path_raw = marker.get("reportPath")
    if not isinstance(report_path_raw, str) or not report_path_raw.strip():
        return _report_unavailable("report_path_unavailable")

    configured_root = (
        evidence_root
        or os.getenv("EBA_RESEARCH_EVIDENCE_DIR", "").strip()
        or DEFAULT_RESEARCH_EVIDENCE_ROOT
    )
    try:
        root = Path(configured_root).resolve()
        report_path = Path(report_path_raw).resolve()
        report_path.relative_to(root)
    except (OSError, RuntimeError, ValueError):
        return _report_unavailable("report_path_rejected")
    if report_path.suffix != ".json" or not report_path.is_file():
        return _report_unavailable("report_unavailable")

    try:
        payload = json.loads(report_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return _report_unavailable("report_invalid")
    if not isinstance(payload, dict) or payload.get("schema") != M5_REPORT_SCHEMA:
        return _report_unavailable("report_schema_rejected")

    safety_contract = (
        payload.get("developmentComparisonOnly") is True
        and payload.get("edgeClaimAllowed") is False
        and payload.get("promotionAuthority") is False
        and payload.get("frozenOosOpened") is False
        and payload.get("liveExecutionAllowed") is False
    )
    if not safety_contract:
        return _report_unavailable("report_safety_rejected")

    treatments_raw = payload.get("treatments")
    treatments = (
        [
            _safe_report_arm(item, include_delta=True)
            for item in treatments_raw
            if isinstance(item, dict)
        ]
        if isinstance(treatments_raw, list)
        else []
    )
    return {
        "available": True,
        "schema": M5_REPORT_SCHEMA,
        "batchId": payload.get("batchId"),
        "workflowId": payload.get("workflowId"),
        "stage": payload.get("stage"),
        "treatmentCount": payload.get("treatmentCount"),
        "allTerminal": payload.get("allTerminal") is True,
        "allExperimentsPassed": payload.get("allExperimentsPassed") is True,
        "evidenceComplete": payload.get("evidenceComplete") is True,
        "baseline": _safe_report_arm(payload.get("baseline")),
        "treatments": treatments,
        "developmentComparisonOnly": True,
        "edgeClaimAllowed": False,
        "promotionAuthority": False,
        "frozenOosOpened": False,
        "liveExecutionAllowed": False,
    }


def build_research_status(
    *,
    root: str | Path = PROJECT_ROOT,
    db_path: str | Path | None = None,
    production_proof: dict[str, Any] | None = None,
    evidence_root: str | Path | None = None,
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
    proof = production_proof if production_proof is not None else read_production_proof()

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
        "productionProof": proof,
        "m5Report": read_m5_report_summary(proof, evidence_root=evidence_root),
        "sf1": read_sf1_summary(evidence_root=evidence_root),
        "sf2": read_sf2_summary(evidence_root=evidence_root),
        "sf3": read_sf3_summary(evidence_root=evidence_root),
        "strategyFactoryV2": read_sfv2_d0_summary(),
        "strategyFactoryV2NextD0": read_sfv2_next_d0_materialization_summary(),
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
