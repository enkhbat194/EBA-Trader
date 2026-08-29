from __future__ import annotations

import json
import os
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .m5_candidate_activity import (
    diagnose_candidate_activity,
    write_immutable_activity_report,
)
from .m5_corpus_materializer import DEFAULT_RESEARCH_ROOT
from .m5_multiwindow_runtime import STATUS_SCHEMA as MULTIWINDOW_STATUS_SCHEMA

STATUS_SCHEMA = "m5_candidate_activity_runtime_status_v1"
DEFAULT_STATUS_PATH = DEFAULT_RESEARCH_ROOT / "m5-candidate-activity-latest.json"
MULTIWINDOW_STATUS_NAME = "m5-multiwindow-evaluation-latest.json"


def _utc_now() -> str:
    return datetime.now(tz=UTC).isoformat()


def _read_json(path: Path, *, label: str) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"cannot read {label}") from exc
    if not isinstance(payload, dict):
        raise RuntimeError(f"{label} must be a JSON object")
    return payload


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
        "developmentEvidenceOnly": True,
        "edgeClaimAllowed": False,
        "promotionAuthority": False,
        "frozenOosOpened": False,
        "m5FrozenOosOpened": False,
        "liveExecutionAllowed": False,
    }


def _load_multiwindow_status(research_root: Path) -> dict[str, Any]:
    payload = _read_json(
        research_root / MULTIWINDOW_STATUS_NAME,
        label="M5 multi-window runtime status",
    )
    checks = {
        "schema": payload.get("schema") == MULTIWINDOW_STATUS_SCHEMA,
        "phase": payload.get("phase") == "COMPLETE",
        "complete": payload.get("complete") is True,
        "safe": payload.get("safe") is True,
        "development": payload.get("rankingIsDevelopmentOnly") is True,
        "edge": payload.get("edgeClaimAllowed") is False,
        "promotion": payload.get("promotionAuthority") is False,
        "legacy_oos": payload.get("frozenOosOpened") is False,
        "m5_oos": payload.get("m5FrozenOosOpened") is False,
        "live": payload.get("liveExecutionAllowed") is False,
    }
    failed = [name for name, passed in checks.items() if not passed]
    if failed:
        raise RuntimeError(
            "M5 multi-window status is not safe for diagnostics: " + ", ".join(failed)
        )
    return payload


def run_candidate_activity_diagnostics(
    *,
    research_root: Path = DEFAULT_RESEARCH_ROOT,
    status_path: Path | None = None,
    candidate_id: str | None = None,
) -> dict[str, Any]:
    research_root = research_root.resolve()
    status_path = (status_path or (research_root / DEFAULT_STATUS_PATH.name)).resolve()
    evidence_root = (research_root / "evidence").resolve()

    try:
        multiwindow_status = _load_multiwindow_status(research_root)
        selected_id = (
            candidate_id or str(multiwindow_status.get("topDevelopmentCandidate") or "")
        ).strip()
        if not selected_id:
            raise RuntimeError("M5 multi-window status has no diagnostic candidate")
        report_raw = multiwindow_status.get("reportPath")
        if not isinstance(report_raw, str) or not report_raw.strip():
            raise RuntimeError("M5 multi-window status is missing reportPath")
        report_path = Path(report_raw).resolve()
        try:
            report_path.relative_to(evidence_root)
        except ValueError as exc:
            raise RuntimeError("M5 multi-window report escapes the evidence root") from exc
        multiwindow_report = _read_json(report_path, label="M5 multi-window report")

        diagnostic = diagnose_candidate_activity(
            multiwindow_report,
            candidate_id=selected_id,
        )
        diagnostic_id = str(diagnostic["diagnosticId"])
        immutable_path = evidence_root / f"m5-candidate-activity-{diagnostic_id}.json"
        write_immutable_activity_report(immutable_path, diagnostic)

        complete = {
            **_base_status(phase="COMPLETE", status_path=status_path),
            "complete": True,
            "evaluationId": diagnostic.get("evaluationId"),
            "materializationId": diagnostic.get("materializationId"),
            "diagnosticId": diagnostic_id,
            "reportPath": str(immutable_path),
            "candidateId": selected_id,
            "candidateParameters": diagnostic.get("candidateParameters"),
            "windowCount": diagnostic.get("windowCount"),
            "activeTradeWindows": diagnostic.get("activeTradeWindows"),
            "activeWindowCount": diagnostic.get("activeWindowCount"),
            "zeroTradeWindowCount": diagnostic.get("zeroTradeWindowCount"),
            "baselineTradeCount": diagnostic.get("baselineTradeCount"),
            "candidateTradeCount": diagnostic.get("candidateTradeCount"),
            "candidateTradeRetentionVsBaseline": diagnostic.get(
                "candidateTradeRetentionVsBaseline"
            ),
            "sampleSufficientForRobustness": diagnostic.get(
                "sampleSufficientForRobustness"
            ),
            "structuralRole": diagnostic.get("structuralRole"),
            "independentSignalGenerator": False,
            "diagnosticState": diagnostic.get("diagnosticState"),
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
            "EBA_M5_ACTIVITY_STATUS",
            str(research_root / DEFAULT_STATUS_PATH.name),
        )
    )
    candidate_id = os.environ.get("EBA_M5_ACTIVITY_CANDIDATE")
    try:
        payload = run_candidate_activity_diagnostics(
            research_root=research_root,
            status_path=status_path,
            candidate_id=candidate_id,
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
