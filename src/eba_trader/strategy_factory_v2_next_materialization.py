from __future__ import annotations

import json
import os
import tempfile
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .research_evidence import canonical_json, sha256_file, sha256_text
from .strategy_factory_v2_next_dataset_plan import load_next_d0_dataset_plan
from .strategy_factory_v2_next_dataset_workflow import (
    NextD0FeatureBuildManifest,
    build_next_d0_window_feature_dataset,
)

AUTHORIZATION_SCHEMA = "sfv2_next_d0_materialization_authorization_v1"
STATUS_SCHEMA = "sfv2_next_d0_materialization_status_v1"
REQUEST_ID = "sfv2-next-d0-materialize-20260904-v1"
AUTHORITY = "D0_DATA_MATERIALIZATION_ONLY"
CAMPAIGN_ID = "sfv2-existing-data-low-turnover-v1"
EXPECTED_PLAN_SHA256 = "c3ae7735f657d905c2931613062fa9091c72dd9458d7cdfae678a01bcea26171"
EXPECTED_CATALOG_SHA256 = (
    "0aa793ca70ba8719486ba6edae314c77803e1b87884665d17ec88019ec71654a"
)
EXPECTED_WINDOW_COUNT = 10
EXPECTED_MAX_WINDOWS_PER_INVOCATION = 1

BuildWindow = Callable[..., tuple[NextD0FeatureBuildManifest, Path]]


@dataclass(frozen=True, slots=True)
class NextD0MaterializationAuthorization:
    max_windows_per_invocation: int


def load_next_d0_materialization_authorization(
    path: str | Path,
) -> NextD0MaterializationAuthorization:
    try:
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError("cannot read next D0 materialization authorization") from exc
    if not isinstance(payload, dict):
        raise ValueError("next D0 materialization authorization must be an object")
    expected_fields = {
        "schema",
        "request_id",
        "enabled",
        "single_use",
        "authority",
        "campaign_id",
        "expected_dataset_plan_sha256",
        "expected_catalog_sha256",
        "expected_window_count",
        "runtime",
        "safety",
    }
    if set(payload) != expected_fields:
        raise ValueError("next D0 materialization authorization fields changed")
    if payload["schema"] != AUTHORIZATION_SCHEMA:
        raise ValueError("unsupported next D0 materialization authorization schema")
    if payload["request_id"] != REQUEST_ID:
        raise ValueError("next D0 materialization request identity changed")
    if payload["enabled"] is not True or payload["single_use"] is not True:
        raise ValueError("next D0 materialization authorization must remain enabled and single-use")
    if payload["authority"] != AUTHORITY:
        raise ValueError("next D0 materialization authority changed")
    if payload["campaign_id"] != CAMPAIGN_ID:
        raise ValueError("next D0 materialization campaign identity changed")
    if payload["expected_dataset_plan_sha256"] != EXPECTED_PLAN_SHA256:
        raise ValueError("next D0 materialization dataset-plan SHA changed")
    if payload["expected_catalog_sha256"] != EXPECTED_CATALOG_SHA256:
        raise ValueError("next D0 materialization catalog SHA changed")
    if payload["expected_window_count"] != EXPECTED_WINDOW_COUNT:
        raise ValueError("next D0 materialization window count changed")

    runtime = payload["runtime"]
    if not isinstance(runtime, dict) or set(runtime) != {"max_windows_per_invocation"}:
        raise ValueError("next D0 materialization runtime fields changed")
    max_windows = runtime["max_windows_per_invocation"]
    if isinstance(max_windows, bool) or max_windows != EXPECTED_MAX_WINDOWS_PER_INVOCATION:
        raise ValueError("next D0 materialization invocation budget changed")

    expected_safety = {
        "performance_evaluation_allowed": False,
        "fresh_confirmation_evidence": False,
        "verification_authority": False,
        "d1_opened": False,
        "frozen_oos_opened": False,
        "sf4_data_access_allowed": False,
        "demo_promotion_allowed": False,
        "live_execution_allowed": False,
        "real_execution_allowed": False,
        "public_mutation_allowed": False,
    }
    if payload["safety"] != expected_safety:
        raise ValueError("next D0 materialization safety boundary changed")
    return NextD0MaterializationAuthorization(max_windows_per_invocation=max_windows)


def _load_status(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise RuntimeError("next D0 materialization status is unreadable") from exc
    if not isinstance(payload, dict):
        raise RuntimeError("next D0 materialization status must be an object")
    return payload


def _atomic_write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = canonical_json(payload)
    fd, temp_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_name, path)
    finally:
        Path(temp_name).unlink(missing_ok=True)


def _safe_ref(root: Path, path: Path) -> str:
    try:
        return str(path.resolve().relative_to(root.resolve()))
    except ValueError as exc:
        raise RuntimeError("materialization receipt path escaped dataset root") from exc


def _receipt_from_manifest(
    manifest: NextD0FeatureBuildManifest,
    manifest_path: Path,
    *,
    dataset_root: Path,
    source_code_sha: str,
) -> dict[str, Any]:
    feature_path = dataset_root / manifest.dataset_ref
    if not feature_path.is_file():
        raise RuntimeError("materialized feature CSV is missing")
    if sha256_file(feature_path) != manifest.feature_csv_sha256:
        raise RuntimeError("materialized feature CSV SHA does not match workflow manifest")
    return {
        "windowName": manifest.window_name,
        "workflowId": manifest.workflow_id,
        "workflowManifestRef": _safe_ref(dataset_root, manifest_path),
        "featureDatasetId": manifest.feature_dataset_id,
        "featureCsvSha256": manifest.feature_csv_sha256,
        "datasetRef": manifest.dataset_ref,
        "rowCount": manifest.row_count,
        "startMs": manifest.start_ms,
        "endMs": manifest.end_ms,
        "requiredOrderflowStartMs": manifest.required_orderflow_start_ms,
        "candleAcquisitionId": manifest.candle_acquisition_id,
        "orderflowDatasetId": manifest.orderflow_dataset_id,
        "orderflowAcquisitionId": manifest.orderflow_acquisition_id,
        "sourceCodeSha": source_code_sha,
    }


def _validate_existing_status(
    payload: dict[str, Any],
    *,
    dataset_root: Path,
    source_code_sha: str,
) -> list[dict[str, Any]]:
    expected_keys = {
        "schema",
        "requestId",
        "authority",
        "campaignId",
        "datasetPlanSha256",
        "catalogSha256",
        "phase",
        "sourceCodeSha",
        "expectedWindowCount",
        "completedWindowCount",
        "nextWindowName",
        "datasetBundleSha256",
        "receipts",
        "performanceEvaluationAllowed",
        "freshConfirmationEvidence",
        "verificationAuthority",
        "d1Opened",
        "frozenOosOpened",
        "sf4DataAccessAllowed",
        "demoPromotionAllowed",
        "liveExecutionAllowed",
        "realExecutionAllowed",
    }
    if set(payload) != expected_keys:
        raise RuntimeError("next D0 materialization status fields changed")
    fixed = {
        "schema": STATUS_SCHEMA,
        "requestId": REQUEST_ID,
        "authority": AUTHORITY,
        "campaignId": CAMPAIGN_ID,
        "datasetPlanSha256": EXPECTED_PLAN_SHA256,
        "catalogSha256": EXPECTED_CATALOG_SHA256,
        "expectedWindowCount": EXPECTED_WINDOW_COUNT,
        "performanceEvaluationAllowed": False,
        "freshConfirmationEvidence": False,
        "verificationAuthority": False,
        "d1Opened": False,
        "frozenOosOpened": False,
        "sf4DataAccessAllowed": False,
        "demoPromotionAllowed": False,
        "liveExecutionAllowed": False,
        "realExecutionAllowed": False,
    }
    for key, value in fixed.items():
        if payload.get(key) != value:
            raise RuntimeError(f"next D0 materialization status safety mismatch: {key}")
    if payload.get("sourceCodeSha") != source_code_sha:
        raise RuntimeError(
            "next D0 materialization source code changed before dataset receipt freeze"
        )
    receipts = payload.get("receipts")
    if not isinstance(receipts, list):
        raise RuntimeError("next D0 materialization receipts must be an array")
    if payload.get("completedWindowCount") != len(receipts):
        raise RuntimeError("next D0 materialization completed count does not match receipts")
    names: set[str] = set()
    for receipt in receipts:
        if not isinstance(receipt, dict):
            raise RuntimeError("next D0 materialization receipt must be an object")
        name = str(receipt.get("windowName") or "")
        if not name or name in names:
            raise RuntimeError("next D0 materialization receipt identity is invalid")
        names.add(name)
        if receipt.get("sourceCodeSha") != source_code_sha:
            raise RuntimeError("next D0 receipt source code SHA changed")
        dataset_ref = receipt.get("datasetRef")
        feature_sha = receipt.get("featureCsvSha256")
        if not isinstance(dataset_ref, str) or not isinstance(feature_sha, str):
            raise RuntimeError("next D0 receipt feature identity is invalid")
        feature_path = dataset_root / dataset_ref
        if not feature_path.is_file() or sha256_file(feature_path) != feature_sha:
            raise RuntimeError("next D0 receipt feature integrity check failed")
    return [dict(item) for item in receipts]


def _status_payload(
    *,
    source_code_sha: str,
    plan_window_names: tuple[str, ...],
    receipts: list[dict[str, Any]],
) -> dict[str, Any]:
    complete = len(receipts) == EXPECTED_WINDOW_COUNT
    completed_names = {str(item["windowName"]) for item in receipts}
    next_name = next((name for name in plan_window_names if name not in completed_names), None)
    bundle_sha = sha256_text(canonical_json(receipts)) if complete else None
    return {
        "schema": STATUS_SCHEMA,
        "requestId": REQUEST_ID,
        "authority": AUTHORITY,
        "campaignId": CAMPAIGN_ID,
        "datasetPlanSha256": EXPECTED_PLAN_SHA256,
        "catalogSha256": EXPECTED_CATALOG_SHA256,
        "phase": "COMPLETE" if complete else "IN_PROGRESS",
        "sourceCodeSha": source_code_sha,
        "expectedWindowCount": EXPECTED_WINDOW_COUNT,
        "completedWindowCount": len(receipts),
        "nextWindowName": next_name,
        "datasetBundleSha256": bundle_sha,
        "receipts": receipts,
        "performanceEvaluationAllowed": False,
        "freshConfirmationEvidence": False,
        "verificationAuthority": False,
        "d1Opened": False,
        "frozenOosOpened": False,
        "sf4DataAccessAllowed": False,
        "demoPromotionAllowed": False,
        "liveExecutionAllowed": False,
        "realExecutionAllowed": False,
    }


def run_next_d0_materialization_cycle(
    *,
    authorization_path: str | Path,
    plan_path: str | Path,
    inventory_path: str | Path,
    dataset_root: str | Path,
    status_path: str | Path,
    source_code_sha: str,
    build_window: BuildWindow = build_next_d0_window_feature_dataset,
) -> dict[str, Any]:
    authorization = load_next_d0_materialization_authorization(authorization_path)
    plan_file = Path(plan_path)
    if sha256_file(plan_file) != EXPECTED_PLAN_SHA256:
        raise RuntimeError("next D0 dataset plan SHA does not match authorization")
    plan = load_next_d0_dataset_plan(plan_file, inventory_path=inventory_path)
    if plan.campaign_id != CAMPAIGN_ID or plan.catalog_sha256 != EXPECTED_CATALOG_SHA256:
        raise RuntimeError("next D0 dataset plan identity does not match authorization")
    if len(plan.windows) != EXPECTED_WINDOW_COUNT:
        raise RuntimeError("next D0 dataset plan window count changed")
    if not source_code_sha.strip():
        raise ValueError("source_code_sha is required")

    root = Path(dataset_root)
    status_file = Path(status_path)
    existing = _load_status(status_file)
    receipts = (
        _validate_existing_status(
            existing,
            dataset_root=root,
            source_code_sha=source_code_sha,
        )
        if existing is not None
        else []
    )
    window_names = tuple(window.name for window in plan.windows)
    completed = {str(item["windowName"]) for item in receipts}
    if len(receipts) == EXPECTED_WINDOW_COUNT:
        payload = _status_payload(
            source_code_sha=source_code_sha,
            plan_window_names=window_names,
            receipts=receipts,
        )
        if existing != payload:
            raise RuntimeError("completed next D0 materialization receipt changed")
        return payload

    built = 0
    for window in plan.windows:
        if window.name in completed:
            continue
        manifest, manifest_path = build_window(
            window_name=window.name,
            dataset_root=root,
            plan_path=plan_file,
            inventory_path=inventory_path,
        )
        receipt = _receipt_from_manifest(
            manifest,
            manifest_path,
            dataset_root=root,
            source_code_sha=source_code_sha,
        )
        if receipt["windowName"] != window.name:
            raise RuntimeError("next D0 materializer returned the wrong frozen window")
        receipts.append(receipt)
        completed.add(window.name)
        built += 1
        if built >= authorization.max_windows_per_invocation:
            break

    payload = _status_payload(
        source_code_sha=source_code_sha,
        plan_window_names=window_names,
        receipts=receipts,
    )
    _atomic_write_json(status_file, payload)
    return payload
