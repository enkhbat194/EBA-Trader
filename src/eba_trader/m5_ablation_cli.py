from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any

from .candle_acquisition import CandleVenue
from .holdout_guard import assert_not_first_cycle_oos_overlap
from .m5_ablation import (
    AblationDefinition,
    M5OrderFlowAblationOrchestrator,
    OrderFlowGate,
)
from .m5_dataset_workflow import WORKFLOW_SCHEMA
from .orderflow_feature_dataset import (
    FEATURE_DATASET_SCHEMA,
    SUPPORTED_FEATURE_DATASET_SCHEMAS,
)
from .research_evidence import sha256_file
from .research_queue import ExperimentQueue
from .research_store import ResearchStore

GATE_SET_SCHEMA = "m5_orderflow_gate_set_v2"
LEGACY_GATE_SET_SCHEMA = "m5_orderflow_gate_set_v1"
SUPPORTED_GATE_SET_SCHEMAS = {LEGACY_GATE_SET_SCHEMA, GATE_SET_SCHEMA}
DEFAULT_RESEARCH_ROOT = Path("/var/lib/eba-trader/research")


def _json_object(path: Path, *, label: str) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{label} must be a JSON object")
    return payload


def _resolve_under(root: Path, relative: str, *, label: str) -> Path:
    if not relative.strip() or Path(relative).is_absolute():
        raise ValueError(f"{label} must be a non-empty relative path")
    resolved_root = root.resolve()
    candidate = (resolved_root / relative).resolve()
    try:
        candidate.relative_to(resolved_root)
    except ValueError as exc:
        raise ValueError(f"{label} escapes the configured dataset root") from exc
    return candidate


def _load_verified_workflow(
    workflow_manifest_path: Path,
    dataset_root: Path,
) -> dict[str, Any]:
    workflow = _json_object(workflow_manifest_path, label="workflow manifest")
    required = {
        "workflow_id",
        "schema",
        "symbol",
        "venue",
        "interval",
        "start_ms",
        "end_ms",
        "price_bucket",
        "candle_acquisition_id",
        "candle_manifest_path",
        "orderflow_dataset_id",
        "orderflow_manifest_path",
        "orderflow_acquisition_id",
        "orderflow_acquisition_path",
        "feature_dataset_id",
        "feature_manifest_path",
        "feature_csv_sha256",
        "dataset_ref",
    }
    if set(workflow) != required:
        raise ValueError("invalid M5 feature workflow manifest fields")
    if workflow["schema"] != WORKFLOW_SCHEMA:
        raise ValueError("unsupported M5 feature workflow schema")
    if workflow["venue"] != CandleVenue.USD_M_FUTURES.value:
        raise ValueError("real M5 ablation requires USD-M futures data")

    symbol = str(workflow["symbol"]).strip().upper()
    interval = str(workflow["interval"]).strip()
    start_ms = workflow["start_ms"]
    end_ms = workflow["end_ms"]
    if not symbol or not interval:
        raise ValueError("workflow symbol and interval are required")
    if not isinstance(start_ms, int) or isinstance(start_ms, bool):
        raise ValueError("workflow start_ms must be an integer")
    if not isinstance(end_ms, int) or isinstance(end_ms, bool) or end_ms <= start_ms:
        raise ValueError("workflow end_ms must be an integer greater than start_ms")

    dataset_ref = str(workflow["dataset_ref"])
    dataset_path = _resolve_under(dataset_root, dataset_ref, label="dataset_ref")
    if not dataset_path.is_file():
        raise ValueError("workflow dataset_ref does not exist")
    expected_sha = str(workflow["feature_csv_sha256"])
    if sha256_file(dataset_path) != expected_sha:
        raise ValueError("workflow feature CSV hash mismatch")

    feature_dataset_id = str(workflow["feature_dataset_id"])
    feature_manifest_path = dataset_path.with_suffix(".manifest.json")
    feature_manifest = _json_object(feature_manifest_path, label="feature manifest")
    feature_schema = feature_manifest.get("schema")
    if feature_schema not in SUPPORTED_FEATURE_DATASET_SCHEMAS:
        raise ValueError("unsupported order-flow feature manifest schema")
    if feature_manifest.get("dataset_id") != feature_dataset_id:
        raise ValueError("feature manifest dataset_id does not match workflow")
    if str(feature_manifest.get("symbol", "")).upper() != symbol:
        raise ValueError("feature manifest symbol does not match workflow")
    if feature_manifest.get("interval") != interval:
        raise ValueError("feature manifest interval does not match workflow")
    if feature_manifest.get("start_ms") != start_ms or feature_manifest.get("end_ms") != end_ms:
        raise ValueError("feature manifest time range does not match workflow")
    if feature_manifest.get("venue") != CandleVenue.USD_M_FUTURES.value:
        raise ValueError("feature manifest venue is not USD-M futures")
    if feature_manifest.get("feature_csv_sha256") != expected_sha:
        raise ValueError("feature manifest CSV hash does not match workflow")
    if feature_schema == FEATURE_DATASET_SCHEMA:
        ratio = feature_manifest.get("imbalance_ratio")
        minimum = feature_manifest.get("imbalance_min_volume")
        if not isinstance(ratio, (int, float)) or isinstance(ratio, bool) or float(ratio) <= 1.0:
            raise ValueError("v2 feature manifest requires imbalance_ratio > 1")
        if (
            not isinstance(minimum, (int, float))
            or isinstance(minimum, bool)
            or float(minimum) < 0.0
        ):
            raise ValueError("v2 feature manifest requires imbalance_min_volume >= 0")

    assert_not_first_cycle_oos_overlap(
        symbol=symbol,
        interval=interval,
        start_ms=start_ms,
        end_ms=end_ms,
        context="M5 real order-flow ablation queue",
    )
    return workflow


def _load_gates(path: Path) -> tuple[OrderFlowGate, ...]:
    payload = _json_object(path, label="gate set")
    if set(payload) != {"schema", "gates"} or payload["schema"] not in SUPPORTED_GATE_SET_SCHEMAS:
        raise ValueError("invalid M5 order-flow gate set")
    schema = str(payload["schema"])
    raw_gates = payload["gates"]
    if not isinstance(raw_gates, list) or not raw_gates:
        raise ValueError("gate set requires a non-empty gates list")

    gates: list[OrderFlowGate] = []
    for raw in raw_gates:
        if not isinstance(raw, dict):
            raise ValueError("each order-flow gate must be an object")
        allowed = {"delta_ratio_threshold", "cvd_threshold"}
        if schema == GATE_SET_SCHEMA:
            allowed.add("stacked_imbalance_threshold")
        if not raw or not set(raw) <= allowed:
            raise ValueError("order-flow gate contains unsupported fields")
        gates.append(
            OrderFlowGate(
                delta_ratio_threshold=raw.get("delta_ratio_threshold"),
                cvd_threshold=raw.get("cvd_threshold"),
                stacked_imbalance_threshold=raw.get("stacked_imbalance_threshold"),
            )
        )
    return tuple(gates)


def emit_real_ablation_batch(
    *,
    workflow_manifest_path: str | Path,
    gates_path: str | Path,
    dataset_root: str | Path,
    db_path: str | Path,
    fast_ema: int,
    slow_ema: int,
    initial_cash: float,
    fee_bps: float,
    slippage_bps: float,
    trade_start_time_ms: int | None = None,
    max_attempts: int = 3,
) -> dict[str, object]:
    dataset_root_path = Path(dataset_root)
    workflow = _load_verified_workflow(Path(workflow_manifest_path), dataset_root_path)
    gates = _load_gates(Path(gates_path))

    store = ResearchStore(db_path)
    queue = ExperimentQueue(store)
    orchestrator = M5OrderFlowAblationOrchestrator(store, queue)
    batch = orchestrator.emit(
        AblationDefinition(
            dataset_ref=str(workflow["dataset_ref"]),
            symbol=str(workflow["symbol"]),
            interval=str(workflow["interval"]),
            start_ms=int(workflow["start_ms"]),
            end_ms=int(workflow["end_ms"]),
            fast_ema=fast_ema,
            slow_ema=slow_ema,
            initial_cash=initial_cash,
            fee_bps=fee_bps,
            slippage_bps=slippage_bps,
            trade_start_time_ms=trade_start_time_ms,
            gates=gates,
            max_attempts=max_attempts,
        )
    )
    return {
        "batch_id": batch.batch_id,
        "workflow_id": workflow["workflow_id"],
        "dataset_ref": workflow["dataset_ref"],
        "baseline_experiment_id": batch.baseline_experiment_id,
        "experiment_ids": list(batch.experiment_ids),
        "treatment_count": len(batch.pairs),
        "stage": "m5_orderflow_ablation_dev",
        "frozen_oos_opened": False,
        "live_execution_allowed": False,
    }


def m5_real_ablation_cli() -> None:
    research_root = Path(os.environ.get("EBA_RESEARCH_ROOT", str(DEFAULT_RESEARCH_ROOT)))
    default_dataset_root = os.environ.get(
        "EBA_RESEARCH_DATASET_ROOT",
        str(research_root / "datasets"),
    )
    default_db = os.environ.get("EBA_RESEARCH_DB", str(research_root / "eba_research.db"))

    parser = argparse.ArgumentParser(
        description="Verify a real M5 USD-M feature workflow and queue deterministic ablation jobs"
    )
    parser.add_argument("--workflow-manifest", required=True)
    parser.add_argument("--gates-json", required=True)
    parser.add_argument("--dataset-root", default=default_dataset_root)
    parser.add_argument("--db", default=default_db)
    parser.add_argument("--fast-ema", type=int, default=12)
    parser.add_argument("--slow-ema", type=int, default=26)
    parser.add_argument("--initial-cash", type=float, default=10_000.0)
    parser.add_argument("--fee-bps", type=float, default=4.0)
    parser.add_argument("--slippage-bps", type=float, default=1.5)
    parser.add_argument("--trade-start-time-ms", type=int)
    parser.add_argument("--max-attempts", type=int, default=3)
    args = parser.parse_args()

    result = emit_real_ablation_batch(
        workflow_manifest_path=args.workflow_manifest,
        gates_path=args.gates_json,
        dataset_root=args.dataset_root,
        db_path=args.db,
        fast_ema=args.fast_ema,
        slow_ema=args.slow_ema,
        initial_cash=args.initial_cash,
        fee_bps=args.fee_bps,
        slippage_bps=args.slippage_bps,
        trade_start_time_ms=args.trade_start_time_ms,
        max_attempts=args.max_attempts,
    )
    print(json.dumps(result, sort_keys=True))
