from __future__ import annotations

import json
import os
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .m5_corpus_materializer import (
    DEFAULT_NAMESPACE,
    DEFAULT_RESEARCH_ROOT,
    materialize_m5_development_corpus,
)
from .m5_study_policy import DEFAULT_M5_DEVELOPMENT_CORPUS

STATUS_SCHEMA = "m5_corpus_runtime_status_v1"
DEFAULT_STATUS_PATH = DEFAULT_RESEARCH_ROOT / "m5-corpus-materialization-latest.json"


def _utc_now() -> str:
    return datetime.now(tz=UTC).isoformat()


def _atomic_write(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    serialized = json.dumps(payload, sort_keys=True, indent=2) + "\n"
    with tempfile.NamedTemporaryFile(
        mode="w",
        encoding="utf-8",
        dir=path.parent,
        prefix=f".{path.name}.",
        delete=False,
    ) as handle:
        handle.write(serialized)
        temporary = Path(handle.name)
    temporary.chmod(0o640)
    temporary.replace(path)


def _base_status(*, phase: str, status_path: Path) -> dict[str, Any]:
    return {
        "schema": STATUS_SCHEMA,
        "phase": phase,
        "updatedAt": _utc_now(),
        "statusPath": str(status_path),
        "complete": False,
        "safe": True,
        "integrityVerified": False,
        "expectedWindowCount": len(DEFAULT_M5_DEVELOPMENT_CORPUS.windows),
        "windowCount": None,
        "orderflowSource": "archive",
        "allFeatureHashesPresent": False,
        "frozenOosOpened": False,
        "m5FrozenOosOpened": False,
        "liveExecutionAllowed": False,
        "edgeClaimAllowed": False,
        "promotionAuthority": False,
    }


def run_m5_corpus_materialization(
    *,
    research_root: Path = DEFAULT_RESEARCH_ROOT,
    status_path: Path | None = None,
) -> dict[str, Any]:
    research_root = research_root.resolve()
    status_path = (status_path or (research_root / DEFAULT_STATUS_PATH.name)).resolve()
    dataset_root = (research_root / "datasets").resolve()

    running = _base_status(phase="RUNNING", status_path=status_path)
    _atomic_write(status_path, running)

    try:
        materialization, manifest_path = materialize_m5_development_corpus(
            dataset_root=dataset_root,
            namespace=DEFAULT_NAMESPACE,
            price_bucket=1.0,
            orderflow_source="archive",
        )
        expected_count = len(DEFAULT_M5_DEVELOPMENT_CORPUS.windows)
        window_count = len(materialization.windows)
        if window_count != expected_count:
            raise RuntimeError(
                f"M5 corpus runtime expected {expected_count} windows, got {window_count}"
            )
        hashes = [window.feature_csv_sha256 for window in materialization.windows]
        hashes_present = all(
            isinstance(value, str) and len(value) == 64 for value in hashes
        )
        if not hashes_present:
            raise RuntimeError("M5 corpus runtime found missing feature CSV SHA-256 evidence")

        complete = {
            **_base_status(phase="COMPLETE", status_path=status_path),
            "materializationId": materialization.materialization_id,
            "policyId": materialization.policy_id,
            "corpusId": materialization.corpus_id,
            "manifestPath": str(manifest_path),
            "complete": True,
            "integrityVerified": True,
            "windowCount": window_count,
            "allFeatureHashesPresent": True,
        }
        _atomic_write(status_path, complete)
        return complete
    except Exception as exc:
        failed = {
            **_base_status(phase="FAILED", status_path=status_path),
            "errorType": type(exc).__name__,
            "errorSummary": str(exc)[:240],
        }
        _atomic_write(status_path, failed)
        raise


def main() -> int:
    research_root = Path(os.environ.get("EBA_RESEARCH_ROOT", str(DEFAULT_RESEARCH_ROOT)))
    status_path = Path(
        os.environ.get(
            "EBA_M5_CORPUS_STATUS",
            str(research_root / DEFAULT_STATUS_PATH.name),
        )
    )
    try:
        payload = run_m5_corpus_materialization(
            research_root=research_root,
            status_path=status_path,
        )
    except Exception:
        try:
            payload = json.loads(status_path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            payload = {"schema": STATUS_SCHEMA, "phase": "FAILED", "safe": True}
        print(json.dumps(payload, sort_keys=True, separators=(",", ":")))
        return 1
    print(json.dumps(payload, sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
