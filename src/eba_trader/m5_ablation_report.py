from __future__ import annotations

import argparse
import json
import math
import sqlite3
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

REPORT_SCHEMA = "m5_real_ablation_report_v1"
TERMINAL_STATUSES = {"passed", "failed"}


def _json_object(value: str, *, label: str) -> dict[str, Any]:
    payload = json.loads(value)
    if not isinstance(payload, dict):
        raise ValueError(f"{label} must be a JSON object")
    return payload


def _finite_numbers(payload: dict[str, Any]) -> dict[str, float]:
    result: dict[str, float] = {}
    for key, value in payload.items():
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            continue
        number = float(value)
        if math.isfinite(number):
            result[str(key)] = number
    return result


def _metric_delta(
    baseline: dict[str, Any],
    treatment: dict[str, Any],
) -> dict[str, float]:
    base = _finite_numbers(baseline)
    trial = _finite_numbers(treatment)
    return {
        key: trial[key] - base[key]
        for key in sorted(base.keys() & trial.keys())
    }


def build_m5_real_ablation_report(
    *,
    db_path: str | Path,
    batch: dict[str, Any],
) -> dict[str, Any]:
    required = {
        "batch_id",
        "workflow_id",
        "dataset_ref",
        "baseline_experiment_id",
        "experiment_ids",
        "treatment_count",
        "stage",
        "frozen_oos_opened",
        "live_execution_allowed",
    }
    if set(batch) != required:
        raise ValueError("invalid M5 real ablation batch fields")
    if batch["stage"] != "m5_orderflow_ablation_dev":
        raise ValueError("report accepts development M5 ablation batches only")
    if batch["frozen_oos_opened"] is not False:
        raise ValueError("frozen OOS must remain closed")
    if batch["live_execution_allowed"] is not False:
        raise ValueError("live execution must remain locked")

    experiment_ids = batch["experiment_ids"]
    if not isinstance(experiment_ids, list) or not experiment_ids:
        raise ValueError("experiment_ids must be a non-empty list")
    baseline_id = str(batch["baseline_experiment_id"])
    if baseline_id not in experiment_ids:
        raise ValueError("baseline experiment is missing from batch")

    with sqlite3.connect(db_path) as connection:
        connection.row_factory = sqlite3.Row
        rows = connection.execute(
            f"""
            SELECT experiment_id, strategy_id, strategy_version, stage, status,
                   parameters_json, dataset_ref, evidence_ref, metrics_json,
                   created_at, completed_at
            FROM experiment_runs
            WHERE experiment_id IN ({','.join('?' for _ in experiment_ids)})
            """,
            tuple(str(item) for item in experiment_ids),
        ).fetchall()

    by_id = {str(row["experiment_id"]): row for row in rows}
    missing = [str(item) for item in experiment_ids if str(item) not in by_id]
    if missing:
        raise RuntimeError(f"batch experiments missing from research DB: {missing}")

    def arm(experiment_id: str) -> dict[str, Any]:
        row = by_id[experiment_id]
        metrics = _json_object(str(row["metrics_json"]), label="metrics_json")
        parameters = _json_object(str(row["parameters_json"]), label="parameters_json")
        return {
            "experimentId": experiment_id,
            "strategyId": str(row["strategy_id"]),
            "strategyVersion": int(row["strategy_version"]),
            "status": str(row["status"]).lower(),
            "parameters": parameters,
            "metrics": metrics,
            "datasetRef": row["dataset_ref"],
            "evidenceRef": row["evidence_ref"],
            "completedAt": row["completed_at"],
        }

    baseline = arm(baseline_id)
    treatments = []
    for experiment_id in (str(item) for item in experiment_ids):
        if experiment_id == baseline_id:
            continue
        item = arm(experiment_id)
        item["metricDeltaVsBaseline"] = _metric_delta(
            baseline["metrics"],
            item["metrics"],
        )
        treatments.append(item)

    statuses = [baseline["status"], *(item["status"] for item in treatments)]
    all_terminal = all(status in TERMINAL_STATUSES for status in statuses)
    all_passed = all(status == "passed" for status in statuses)
    evidence_complete = all(
        bool(item.get("evidenceRef"))
        for item in [baseline, *treatments]
    )
    return {
        "schema": REPORT_SCHEMA,
        "generatedAt": datetime.now(tz=UTC).isoformat(),
        "batchId": str(batch["batch_id"]),
        "workflowId": str(batch["workflow_id"]),
        "datasetRef": str(batch["dataset_ref"]),
        "stage": str(batch["stage"]),
        "baseline": baseline,
        "treatments": treatments,
        "treatmentCount": len(treatments),
        "allTerminal": all_terminal,
        "allExperimentsPassed": all_passed,
        "evidenceComplete": evidence_complete,
        "developmentComparisonOnly": True,
        "edgeClaimAllowed": False,
        "promotionAuthority": False,
        "frozenOosOpened": False,
        "liveExecutionAllowed": False,
    }


def write_immutable_report(path: str | Path, report: dict[str, Any]) -> Path:
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(report, sort_keys=True, indent=2) + "\n"
    if output.exists():
        existing = json.loads(output.read_text(encoding="utf-8"))
        # generatedAt is observational metadata and may differ on an idempotent rerun.
        left = dict(existing)
        right = dict(report)
        left.pop("generatedAt", None)
        right.pop("generatedAt", None)
        if left != right:
            raise RuntimeError("immutable M5 ablation report collision")
        return output
    output.write_text(text, encoding="utf-8")
    output.chmod(0o640)
    return output


def main() -> int:
    parser = argparse.ArgumentParser(description="Build a sanitized M5 real ablation report")
    parser.add_argument("--db", required=True)
    parser.add_argument("--batch-json", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    batch = _json_object(args.batch_json, label="batch JSON")
    report = build_m5_real_ablation_report(db_path=args.db, batch=batch)
    if not report["allTerminal"] or not report["evidenceComplete"]:
        raise RuntimeError("M5 ablation batch is not terminal with complete evidence")
    path = write_immutable_report(args.output, report)
    print(json.dumps({"report": str(path), **report}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
