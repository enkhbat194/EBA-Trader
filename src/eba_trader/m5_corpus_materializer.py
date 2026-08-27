from __future__ import annotations

import argparse
import json
import os
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .m5_dataset_workflow import (
    ORDERFLOW_SOURCES,
    WORKFLOW_SCHEMA,
    M5FeatureBuildManifest,
    build_usdm_orderflow_feature_dataset,
)
from .m5_study_policy import (
    DEFAULT_M5_DEVELOPMENT_CORPUS,
    DEFAULT_M5_STUDY_POLICY,
    M5DevelopmentCorpusSpec,
    M5StudyWindow,
)
from .orderflow_acquisition import USDM_AGG_TRADES_URL
from .orderflow_archive import USDM_DAILY_AGG_TRADES_ROOT
from .research_evidence import canonical_json, sha256_file, sha256_text

CORPUS_MATERIALIZATION_SCHEMA = "m5_development_corpus_materialization_v1"
CORPUS_WINDOW_RECEIPT_SCHEMA = "m5_development_corpus_window_v1"
DEFAULT_NAMESPACE = "m5_orderflow_dev"
DEFAULT_RESEARCH_ROOT = Path("/var/lib/eba-trader/research")

WindowBuilder = Callable[..., tuple[M5FeatureBuildManifest, Path]]


def _json_object(path: Path, *, label: str) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"cannot read {label}") from exc
    if not isinstance(payload, dict):
        raise ValueError(f"{label} must be a JSON object")
    return payload


def _safe_namespace(namespace: str) -> str:
    normalized = namespace.strip()
    path = Path(normalized)
    if not normalized or path.is_absolute() or ".." in path.parts:
        raise ValueError("namespace must be a safe relative path")
    return normalized


def _resolve_under(root: Path, value: str | Path, *, label: str) -> Path:
    root = root.resolve()
    candidate = Path(value)
    candidate = candidate.resolve() if candidate.is_absolute() else (root / candidate).resolve()
    try:
        candidate.relative_to(root)
    except ValueError as exc:
        raise ValueError(f"{label} escapes the configured dataset root") from exc
    return candidate


def _relative_under(root: Path, value: str | Path, *, label: str) -> str:
    candidate = _resolve_under(root, value, label=label)
    return str(candidate.relative_to(root.resolve()))


def _source_endpoint(orderflow_source: str) -> str:
    if orderflow_source == "rest":
        return USDM_AGG_TRADES_URL
    if orderflow_source == "archive":
        return USDM_DAILY_AGG_TRADES_ROOT
    raise ValueError(f"unsupported order-flow source: {orderflow_source}")


@dataclass(frozen=True, slots=True)
class M5CorpusWindowReceipt:
    materialization_id: str
    policy_id: str
    corpus_id: str
    window_name: str
    start_ms: int
    end_ms: int
    orderflow_source: str
    workflow_id: str
    workflow_manifest_ref: str
    feature_dataset_id: str
    dataset_ref: str
    feature_csv_sha256: str

    def as_dict(self) -> dict[str, object]:
        return {
            "schema": CORPUS_WINDOW_RECEIPT_SCHEMA,
            "materialization_id": self.materialization_id,
            "policy_id": self.policy_id,
            "corpus_id": self.corpus_id,
            "window_name": self.window_name,
            "start_ms": self.start_ms,
            "end_ms": self.end_ms,
            "orderflow_source": self.orderflow_source,
            "workflow_id": self.workflow_id,
            "workflow_manifest_ref": self.workflow_manifest_ref,
            "feature_dataset_id": self.feature_dataset_id,
            "dataset_ref": self.dataset_ref,
            "feature_csv_sha256": self.feature_csv_sha256,
        }


@dataclass(frozen=True, slots=True)
class M5DevelopmentCorpusMaterialization:
    materialization_id: str
    policy_id: str
    corpus_id: str
    symbol: str
    venue: str
    interval: str
    price_bucket: float
    namespace: str
    orderflow_source: str
    windows: tuple[M5CorpusWindowReceipt, ...]

    def as_dict(self) -> dict[str, object]:
        return {
            "schema": CORPUS_MATERIALIZATION_SCHEMA,
            "materialization_id": self.materialization_id,
            "policy_id": self.policy_id,
            "corpus_id": self.corpus_id,
            "symbol": self.symbol,
            "venue": self.venue,
            "interval": self.interval,
            "price_bucket": self.price_bucket,
            "namespace": self.namespace,
            "orderflow_source": self.orderflow_source,
            "window_count": len(self.windows),
            "windows": [window.as_dict() for window in self.windows],
            "frozen_oos_opened": False,
            "m5_frozen_oos_opened": False,
            "live_execution_allowed": False,
        }


def _materialization_id(
    *,
    corpus: M5DevelopmentCorpusSpec,
    price_bucket: float,
    namespace: str,
    orderflow_source: str,
) -> str:
    identity = {
        "schema": CORPUS_MATERIALIZATION_SCHEMA,
        "policy_id": corpus.policy_id,
        "corpus_id": corpus.corpus_id,
        "symbol": DEFAULT_M5_STUDY_POLICY.symbol,
        "venue": DEFAULT_M5_STUDY_POLICY.venue,
        "interval": DEFAULT_M5_STUDY_POLICY.interval,
        "price_bucket": price_bucket,
        "namespace": namespace,
        "orderflow_source": orderflow_source,
        "workflow_schema": WORKFLOW_SCHEMA,
    }
    return f"m5corpusmat_{sha256_text(canonical_json(identity))[:24]}"


def _receipt_from_payload(payload: dict[str, Any]) -> M5CorpusWindowReceipt:
    required = {
        "schema",
        "materialization_id",
        "policy_id",
        "corpus_id",
        "window_name",
        "start_ms",
        "end_ms",
        "orderflow_source",
        "workflow_id",
        "workflow_manifest_ref",
        "feature_dataset_id",
        "dataset_ref",
        "feature_csv_sha256",
    }
    if set(payload) != required or payload.get("schema") != CORPUS_WINDOW_RECEIPT_SCHEMA:
        raise ValueError("invalid M5 corpus window receipt")
    start_ms = payload["start_ms"]
    end_ms = payload["end_ms"]
    if isinstance(start_ms, bool) or not isinstance(start_ms, int):
        raise ValueError("M5 corpus receipt start_ms must be an integer")
    if isinstance(end_ms, bool) or not isinstance(end_ms, int) or end_ms <= start_ms:
        raise ValueError("M5 corpus receipt end_ms must be greater than start_ms")
    return M5CorpusWindowReceipt(
        materialization_id=str(payload["materialization_id"]),
        policy_id=str(payload["policy_id"]),
        corpus_id=str(payload["corpus_id"]),
        window_name=str(payload["window_name"]),
        start_ms=start_ms,
        end_ms=end_ms,
        orderflow_source=str(payload["orderflow_source"]),
        workflow_id=str(payload["workflow_id"]),
        workflow_manifest_ref=str(payload["workflow_manifest_ref"]),
        feature_dataset_id=str(payload["feature_dataset_id"]),
        dataset_ref=str(payload["dataset_ref"]),
        feature_csv_sha256=str(payload["feature_csv_sha256"]),
    )


def _validate_workflow_reference(
    receipt: M5CorpusWindowReceipt,
    *,
    window: M5StudyWindow,
    dataset_root: Path,
    price_bucket: float,
) -> None:
    workflow_path = _resolve_under(
        dataset_root,
        receipt.workflow_manifest_ref,
        label="workflow_manifest_ref",
    )
    if not workflow_path.is_file():
        raise RuntimeError("M5 corpus workflow manifest is missing")
    workflow = _json_object(workflow_path, label="M5 corpus workflow manifest")
    expected = {
        "schema": WORKFLOW_SCHEMA,
        "study_policy_id": receipt.policy_id,
        "study_phase": "development",
        "symbol": DEFAULT_M5_STUDY_POLICY.symbol,
        "venue": DEFAULT_M5_STUDY_POLICY.venue,
        "interval": DEFAULT_M5_STUDY_POLICY.interval,
        "start_ms": window.start_ms,
        "end_ms": window.end_ms,
        "price_bucket": price_bucket,
        "workflow_id": receipt.workflow_id,
        "feature_dataset_id": receipt.feature_dataset_id,
        "dataset_ref": receipt.dataset_ref,
        "feature_csv_sha256": receipt.feature_csv_sha256,
    }
    for key, value in expected.items():
        if workflow.get(key) != value:
            raise RuntimeError(f"M5 corpus workflow mismatch: {key}")

    acquisition_path = workflow.get("orderflow_acquisition_path")
    if not isinstance(acquisition_path, str) or not acquisition_path.strip():
        raise RuntimeError("M5 corpus workflow lacks order-flow acquisition provenance")
    acquisition = _json_object(
        _resolve_under(dataset_root, acquisition_path, label="orderflow_acquisition_path"),
        label="M5 corpus order-flow acquisition",
    )
    if acquisition.get("endpoint") != _source_endpoint(receipt.orderflow_source):
        raise RuntimeError("M5 corpus order-flow source provenance mismatch")

    dataset_path = _resolve_under(dataset_root, receipt.dataset_ref, label="dataset_ref")
    if not dataset_path.is_file():
        raise RuntimeError("M5 corpus feature CSV is missing")
    if sha256_file(dataset_path) != receipt.feature_csv_sha256:
        raise RuntimeError("M5 corpus feature CSV integrity mismatch")


def _validate_receipt(
    receipt: M5CorpusWindowReceipt,
    *,
    materialization_id: str,
    corpus: M5DevelopmentCorpusSpec,
    window: M5StudyWindow,
    dataset_root: Path,
    price_bucket: float,
    orderflow_source: str,
) -> None:
    if receipt.materialization_id != materialization_id:
        raise RuntimeError("M5 corpus receipt materialization ID mismatch")
    if receipt.policy_id != corpus.policy_id or receipt.corpus_id != corpus.corpus_id:
        raise RuntimeError("M5 corpus receipt policy/corpus identity mismatch")
    if receipt.window_name != window.name:
        raise RuntimeError("M5 corpus receipt window name mismatch")
    if receipt.start_ms != window.start_ms or receipt.end_ms != window.end_ms:
        raise RuntimeError("M5 corpus receipt window range mismatch")
    if receipt.orderflow_source != orderflow_source:
        raise RuntimeError("M5 corpus receipt order-flow source mismatch")
    _validate_workflow_reference(
        receipt,
        window=window,
        dataset_root=dataset_root,
        price_bucket=price_bucket,
    )


def _write_immutable(path: Path, payload: dict[str, object], *, label: str) -> None:
    text = canonical_json(payload)
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        if path.read_text(encoding="utf-8") != text:
            raise RuntimeError(f"immutable {label} collision")
        return
    path.write_text(text, encoding="utf-8")


def _receipt_from_build(
    *,
    materialization_id: str,
    corpus: M5DevelopmentCorpusSpec,
    window: M5StudyWindow,
    manifest: M5FeatureBuildManifest,
    workflow_path: Path,
    dataset_root: Path,
    price_bucket: float,
    orderflow_source: str,
) -> M5CorpusWindowReceipt:
    if manifest.schema != WORKFLOW_SCHEMA:
        raise RuntimeError("M5 corpus builder returned unsupported workflow schema")
    if manifest.study_policy_id != corpus.policy_id or manifest.study_phase != "development":
        raise RuntimeError("M5 corpus builder returned wrong study policy/phase")
    if manifest.symbol != DEFAULT_M5_STUDY_POLICY.symbol:
        raise RuntimeError("M5 corpus builder returned wrong symbol")
    if manifest.venue != DEFAULT_M5_STUDY_POLICY.venue:
        raise RuntimeError("M5 corpus builder returned wrong venue")
    if manifest.interval != DEFAULT_M5_STUDY_POLICY.interval:
        raise RuntimeError("M5 corpus builder returned wrong interval")
    if manifest.start_ms != window.start_ms or manifest.end_ms != window.end_ms:
        raise RuntimeError("M5 corpus builder returned wrong window")
    if manifest.price_bucket != price_bucket:
        raise RuntimeError("M5 corpus builder returned wrong price bucket")

    receipt = M5CorpusWindowReceipt(
        materialization_id=materialization_id,
        policy_id=corpus.policy_id,
        corpus_id=corpus.corpus_id,
        window_name=window.name,
        start_ms=window.start_ms,
        end_ms=window.end_ms,
        orderflow_source=orderflow_source,
        workflow_id=manifest.workflow_id,
        workflow_manifest_ref=_relative_under(
            dataset_root,
            workflow_path,
            label="workflow manifest path",
        ),
        feature_dataset_id=manifest.feature_dataset_id,
        dataset_ref=manifest.dataset_ref,
        feature_csv_sha256=manifest.feature_csv_sha256,
    )
    _validate_receipt(
        receipt,
        materialization_id=materialization_id,
        corpus=corpus,
        window=window,
        dataset_root=dataset_root,
        price_bucket=price_bucket,
        orderflow_source=orderflow_source,
    )
    return receipt


def _load_completed_materialization(
    path: Path,
    *,
    materialization_id: str,
    corpus: M5DevelopmentCorpusSpec,
    dataset_root: Path,
    price_bucket: float,
    namespace: str,
    orderflow_source: str,
) -> M5DevelopmentCorpusMaterialization:
    payload = _json_object(path, label="M5 corpus materialization")
    required = {
        "schema",
        "materialization_id",
        "policy_id",
        "corpus_id",
        "symbol",
        "venue",
        "interval",
        "price_bucket",
        "namespace",
        "orderflow_source",
        "window_count",
        "windows",
        "frozen_oos_opened",
        "m5_frozen_oos_opened",
        "live_execution_allowed",
    }
    if set(payload) != required or payload.get("schema") != CORPUS_MATERIALIZATION_SCHEMA:
        raise ValueError("invalid M5 corpus materialization manifest")
    if payload.get("materialization_id") != materialization_id:
        raise RuntimeError("M5 corpus materialization ID mismatch")
    if payload.get("policy_id") != corpus.policy_id or payload.get("corpus_id") != corpus.corpus_id:
        raise RuntimeError("M5 corpus materialization policy/corpus mismatch")
    if payload.get("symbol") != DEFAULT_M5_STUDY_POLICY.symbol:
        raise RuntimeError("M5 corpus materialization symbol mismatch")
    if payload.get("venue") != DEFAULT_M5_STUDY_POLICY.venue:
        raise RuntimeError("M5 corpus materialization venue mismatch")
    if payload.get("interval") != DEFAULT_M5_STUDY_POLICY.interval:
        raise RuntimeError("M5 corpus materialization interval mismatch")
    if payload.get("price_bucket") != price_bucket:
        raise RuntimeError("M5 corpus materialization price bucket mismatch")
    if payload.get("namespace") != namespace or payload.get("orderflow_source") != orderflow_source:
        raise RuntimeError("M5 corpus materialization config mismatch")
    if payload.get("window_count") != len(corpus.windows):
        raise RuntimeError("M5 corpus materialization window count mismatch")
    if payload.get("frozen_oos_opened") is not False:
        raise RuntimeError("M5 corpus materialization must keep legacy frozen OOS closed")
    if payload.get("m5_frozen_oos_opened") is not False:
        raise RuntimeError("M5 corpus materialization must keep M5 frozen OOS closed")
    if payload.get("live_execution_allowed") is not False:
        raise RuntimeError("M5 corpus materialization cannot enable live execution")

    raw_windows = payload.get("windows")
    if not isinstance(raw_windows, list) or len(raw_windows) != len(corpus.windows):
        raise RuntimeError("M5 corpus materialization windows are incomplete")
    receipts = tuple(_receipt_from_payload(item) for item in raw_windows if isinstance(item, dict))
    if len(receipts) != len(raw_windows):
        raise ValueError("M5 corpus materialization contains invalid window entries")
    for receipt, window in zip(receipts, corpus.windows, strict=True):
        _validate_receipt(
            receipt,
            materialization_id=materialization_id,
            corpus=corpus,
            window=window,
            dataset_root=dataset_root,
            price_bucket=price_bucket,
            orderflow_source=orderflow_source,
        )
    return M5DevelopmentCorpusMaterialization(
        materialization_id=materialization_id,
        policy_id=corpus.policy_id,
        corpus_id=corpus.corpus_id,
        symbol=DEFAULT_M5_STUDY_POLICY.symbol,
        venue=DEFAULT_M5_STUDY_POLICY.venue,
        interval=DEFAULT_M5_STUDY_POLICY.interval,
        price_bucket=price_bucket,
        namespace=namespace,
        orderflow_source=orderflow_source,
        windows=receipts,
    )


def materialize_m5_development_corpus(
    *,
    dataset_root: str | Path,
    price_bucket: float = 1.0,
    namespace: str = DEFAULT_NAMESPACE,
    orderflow_source: str = "archive",
    corpus: M5DevelopmentCorpusSpec = DEFAULT_M5_DEVELOPMENT_CORPUS,
    build_window: WindowBuilder = build_usdm_orderflow_feature_dataset,
) -> tuple[M5DevelopmentCorpusMaterialization, Path]:
    if not isinstance(price_bucket, (int, float)) or isinstance(price_bucket, bool):
        raise ValueError("price_bucket must be numeric")
    price_bucket = float(price_bucket)
    if price_bucket <= 0.0:
        raise ValueError("price_bucket must be positive")
    namespace = _safe_namespace(namespace)
    orderflow_source = orderflow_source.strip().lower()
    if orderflow_source not in ORDERFLOW_SOURCES:
        raise ValueError(f"unsupported order-flow source: {orderflow_source}")
    if corpus.policy_id != DEFAULT_M5_STUDY_POLICY.policy_id:
        raise ValueError("M5 corpus materializer requires the sealed study policy")

    dataset_root_path = Path(dataset_root)
    materialization_id = _materialization_id(
        corpus=corpus,
        price_bucket=price_bucket,
        namespace=namespace,
        orderflow_source=orderflow_source,
    )
    corpus_root = dataset_root_path / namespace / "corpus"
    final_path = corpus_root / f"{materialization_id}.manifest.json"
    if final_path.exists():
        return (
            _load_completed_materialization(
                final_path,
                materialization_id=materialization_id,
                corpus=corpus,
                dataset_root=dataset_root_path,
                price_bucket=price_bucket,
                namespace=namespace,
                orderflow_source=orderflow_source,
            ),
            final_path,
        )

    checkpoint_root = corpus_root / "checkpoints" / materialization_id
    receipts: list[M5CorpusWindowReceipt] = []
    for window in corpus.windows:
        checkpoint = checkpoint_root / f"{window.name}.json"
        if checkpoint.exists():
            receipt = _receipt_from_payload(
                _json_object(checkpoint, label=f"M5 corpus checkpoint {window.name}")
            )
            _validate_receipt(
                receipt,
                materialization_id=materialization_id,
                corpus=corpus,
                window=window,
                dataset_root=dataset_root_path,
                price_bucket=price_bucket,
                orderflow_source=orderflow_source,
            )
        else:
            manifest, workflow_path = build_window(
                symbol=DEFAULT_M5_STUDY_POLICY.symbol,
                interval=DEFAULT_M5_STUDY_POLICY.interval,
                start_ms=window.start_ms,
                end_ms=window.end_ms,
                price_bucket=price_bucket,
                dataset_root=dataset_root_path,
                namespace=namespace,
                orderflow_source=orderflow_source,
            )
            receipt = _receipt_from_build(
                materialization_id=materialization_id,
                corpus=corpus,
                window=window,
                manifest=manifest,
                workflow_path=workflow_path,
                dataset_root=dataset_root_path,
                price_bucket=price_bucket,
                orderflow_source=orderflow_source,
            )
            _write_immutable(
                checkpoint,
                receipt.as_dict(),
                label=f"M5 corpus checkpoint {window.name}",
            )
        receipts.append(receipt)

    materialization = M5DevelopmentCorpusMaterialization(
        materialization_id=materialization_id,
        policy_id=corpus.policy_id,
        corpus_id=corpus.corpus_id,
        symbol=DEFAULT_M5_STUDY_POLICY.symbol,
        venue=DEFAULT_M5_STUDY_POLICY.venue,
        interval=DEFAULT_M5_STUDY_POLICY.interval,
        price_bucket=price_bucket,
        namespace=namespace,
        orderflow_source=orderflow_source,
        windows=tuple(receipts),
    )
    _write_immutable(
        final_path,
        materialization.as_dict(),
        label="M5 corpus materialization manifest",
    )
    return materialization, final_path


def m5_materialize_development_corpus_cli() -> None:
    research_root = Path(os.environ.get("EBA_RESEARCH_ROOT", str(DEFAULT_RESEARCH_ROOT)))
    default_dataset_root = os.environ.get(
        "EBA_RESEARCH_DATASET_ROOT",
        str(research_root / "datasets"),
    )
    parser = argparse.ArgumentParser(
        description="Materialize the sealed pre-registered M5 development corpus"
    )
    parser.add_argument("--dataset-root", default=default_dataset_root)
    parser.add_argument("--namespace", default=DEFAULT_NAMESPACE)
    parser.add_argument("--price-bucket", type=float, default=1.0)
    parser.add_argument("--orderflow-source", choices=ORDERFLOW_SOURCES, default="archive")
    args = parser.parse_args()

    materialization, path = materialize_m5_development_corpus(
        dataset_root=args.dataset_root,
        namespace=args.namespace,
        price_bucket=args.price_bucket,
        orderflow_source=args.orderflow_source,
    )
    print(
        json.dumps(
            {
                "materialization_id": materialization.materialization_id,
                "policy_id": materialization.policy_id,
                "corpus_id": materialization.corpus_id,
                "window_count": len(materialization.windows),
                "manifest": str(path),
                "orderflow_source": materialization.orderflow_source,
                "frozen_oos_opened": False,
                "m5_frozen_oos_opened": False,
                "live_execution_allowed": False,
            },
            sort_keys=True,
        )
    )
