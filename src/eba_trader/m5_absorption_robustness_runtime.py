from __future__ import annotations

import json
import os
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .m5_absorption_robustness import (
    REPORT_SCHEMA,
    evaluate_absorption_robustness,
    write_immutable_robustness_report,
)
from .m5_corpus_materializer import DEFAULT_RESEARCH_ROOT
from .m5_multiwindow_runtime import _load_complete_corpus_status

STATUS_SCHEMA = "m5_absorption_robustness_runtime_status_v1"
DEFAULT_STATUS_PATH = DEFAULT_RESEARCH_ROOT / "m5-absorption-robustness-latest.json"


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
        "candidateId": "absorption_020",
        "scenarioCount": 9,
        "robustnessVerified": False,
        "developmentEvidenceOnly": True,
        "edgeClaimAllowed": False,
        "promotionAuthority": False,
        "frozenOosOpened": False,
        "m5FrozenOosOpened": False,
        "liveExecutionAllowed": False,
    }


def _read_json(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise RuntimeError("cannot read robustness status/report") from exc
    if not isinstance(payload, dict):
        raise RuntimeError("robustness status/report must be an object")
    return payload


def _reusable_status(
    *,
    status_path: Path,
    materialization_id: str,
) -> dict[str, Any] | None:
    if not status_path.is_file():
        return None
    payload = _read_json(status_path)
    if (
        payload.get("schema") != STATUS_SCHEMA
        or payload.get("phase") != "COMPLETE"
        or payload.get("complete") is not True
        or payload.get("safe") is not True
        or payload.get("materializationId") != materialization_id
        or payload.get("developmentEvidenceOnly") is not True
        or payload.get("edgeClaimAllowed") is not False
        or payload.get("promotionAuthority") is not False
        or payload.get("frozenOosOpened") is not False
        or payload.get("m5FrozenOosOpened") is not False
        or payload.get("liveExecutionAllowed") is not False
    ):
        return None
    report_path = payload.get("reportPath")
    if not isinstance(report_path, str) or not Path(report_path).is_file():
        return None
    report = _read_json(Path(report_path))
    if (
        report.get("schema") != REPORT_SCHEMA
        or report.get("robustnessId") != payload.get("robustnessId")
        or report.get("materializationId") != materialization_id
        or report.get("edgeClaimAllowed") is not False
        or report.get("promotionAuthority") is not False
        or report.get("frozenOosOpened") is not False
        or report.get("m5FrozenOosOpened") is not False
        or report.get("liveExecutionAllowed") is not False
    ):
        return None
    return payload


def run_absorption_robustness(
    *,
    research_root: Path = DEFAULT_RESEARCH_ROOT,
    status_path: Path | None = None,
) -> dict[str, Any]:
    research_root = research_root.resolve()
    status_path = (status_path or (research_root / DEFAULT_STATUS_PATH.name)).resolve()
    dataset_root = (research_root / "datasets").resolve()
    evidence_root = (research_root / "evidence").resolve()

    try:
        corpus = _load_complete_corpus_status(research_root)
        materialization_id = str(corpus.get("materializationId") or "")
        manifest_path = str(corpus.get("manifestPath") or "")
        if not materialization_id or not manifest_path:
            raise RuntimeError("complete corpus status is missing identity or manifest")

        reusable = _reusable_status(
            status_path=status_path,
            materialization_id=materialization_id,
        )
        if reusable is not None:
            return reusable

        _atomic_write(
            status_path,
            {
                **_base_status(phase="RUNNING", status_path=status_path),
                "materializationId": materialization_id,
            },
        )
        report = evaluate_absorption_robustness(
            materialization_manifest=manifest_path,
            dataset_root=dataset_root,
            materialization_id=materialization_id,
        )
        robustness_id = str(report["robustnessId"])
        report_path = evidence_root / f"m5-absorption-robustness-{robustness_id}.json"
        write_immutable_robustness_report(report_path, report)
        checks = report.get("checks")
        if not isinstance(checks, dict):
            raise RuntimeError("robustness report checks are missing")

        complete = {
            **_base_status(phase="COMPLETE", status_path=status_path),
            "materializationId": materialization_id,
            "robustnessId": robustness_id,
            "reportPath": str(report_path),
            "complete": True,
            "robustnessVerified": report.get("robustnessVerified") is True,
            "checks": checks,
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
            "EBA_M5_ROBUSTNESS_STATUS",
            str(research_root / DEFAULT_STATUS_PATH.name),
        )
    )
    try:
        payload = run_absorption_robustness(
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
