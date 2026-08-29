from __future__ import annotations

import json
import os
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .m5_candidate_qualification import (
    REPORT_SCHEMA,
    evaluate_candidate_qualification,
    write_immutable_qualification_report,
)
from .m5_corpus_materializer import DEFAULT_RESEARCH_ROOT
from .m5_multiwindow import REPORT_SCHEMA as MULTIWINDOW_REPORT_SCHEMA
from .m5_multiwindow_runtime import STATUS_SCHEMA as MULTIWINDOW_STATUS_SCHEMA

STATUS_SCHEMA = "m5_robustness_qualification_runtime_status_v1"
DEFAULT_STATUS_PATH = DEFAULT_RESEARCH_ROOT / "m5-robustness-qualification-latest.json"
DEFAULT_MULTIWINDOW_STATUS_PATH = DEFAULT_RESEARCH_ROOT / "m5-multiwindow-evaluation-latest.json"


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
        "qualificationState": "UNKNOWN",
        "eligibleCandidateCount": 0,
        "topEligibleCandidate": None,
        "topEligibleParameters": None,
        "developmentEvidenceOnly": True,
        "edgeClaimAllowed": False,
        "promotionAuthority": False,
        "frozenOosOpened": False,
        "m5FrozenOosOpened": False,
        "liveExecutionAllowed": False,
    }


def _load_complete_multiwindow_status(path: Path, *, evidence_root: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    status = _read_json(path, label="M5 multi-window runtime status")
    checks = (
        status.get("schema") == MULTIWINDOW_STATUS_SCHEMA,
        status.get("phase") == "COMPLETE",
        status.get("complete") is True,
        status.get("safe") is True,
        status.get("rankingIsDevelopmentOnly") is True,
        status.get("edgeClaimAllowed") is False,
        status.get("promotionAuthority") is False,
        status.get("frozenOosOpened") is False,
        status.get("m5FrozenOosOpened") is False,
        status.get("liveExecutionAllowed") is False,
    )
    if not all(checks):
        raise RuntimeError("M5 multi-window evaluation is not safely complete")

    report_raw = status.get("reportPath")
    if not isinstance(report_raw, str) or not report_raw.strip():
        raise RuntimeError("M5 multi-window status is missing reportPath")
    report_path = Path(report_raw).resolve()
    try:
        report_path.relative_to(evidence_root.resolve())
    except ValueError as exc:
        raise RuntimeError("M5 multi-window report escapes evidence root") from exc
    if not report_path.is_file():
        raise RuntimeError("M5 multi-window report is missing")
    report = _read_json(report_path, label="M5 multi-window report")
    report_checks = (
        report.get("schema") == MULTIWINDOW_REPORT_SCHEMA,
        report.get("evaluationId") == status.get("evaluationId"),
        report.get("materializationId") == status.get("materializationId"),
        report.get("candidateSetSha256") == status.get("candidateSetSha256"),
        report.get("rankingIsDevelopmentOnly") is True,
        report.get("edgeClaimAllowed") is False,
        report.get("promotionAuthority") is False,
        report.get("frozenOosOpened") is False,
        report.get("m5FrozenOosOpened") is False,
        report.get("liveExecutionAllowed") is False,
    )
    if not all(report_checks):
        raise RuntimeError("M5 multi-window immutable report is unsafe or mismatched")
    return status, report


def _reusable_status(
    *,
    status_path: Path,
    evaluation_id: str,
    evidence_root: Path,
) -> dict[str, Any] | None:
    if not status_path.is_file():
        return None
    payload = _read_json(status_path, label="M5 qualification runtime status")
    if (
        payload.get("schema") != STATUS_SCHEMA
        or payload.get("phase") != "COMPLETE"
        or payload.get("complete") is not True
        or payload.get("safe") is not True
        or payload.get("evaluationId") != evaluation_id
        or payload.get("developmentEvidenceOnly") is not True
        or payload.get("edgeClaimAllowed") is not False
        or payload.get("promotionAuthority") is not False
        or payload.get("frozenOosOpened") is not False
        or payload.get("m5FrozenOosOpened") is not False
        or payload.get("liveExecutionAllowed") is not False
    ):
        return None
    report_raw = payload.get("reportPath")
    if not isinstance(report_raw, str) or not report_raw.strip():
        return None
    report_path = Path(report_raw).resolve()
    try:
        report_path.relative_to(evidence_root.resolve())
    except ValueError:
        return None
    if not report_path.is_file():
        return None
    report = _read_json(report_path, label="M5 qualification report")
    if (
        report.get("schema") != REPORT_SCHEMA
        or report.get("qualificationId") != payload.get("qualificationId")
        or report.get("evaluationId") != evaluation_id
        or report.get("developmentEvidenceOnly") is not True
        or report.get("edgeClaimAllowed") is not False
        or report.get("promotionAuthority") is not False
        or report.get("frozenOosOpened") is not False
        or report.get("m5FrozenOosOpened") is not False
        or report.get("liveExecutionAllowed") is not False
    ):
        return None
    return payload


def run_candidate_qualification(
    *,
    research_root: Path = DEFAULT_RESEARCH_ROOT,
    multiwindow_status_path: Path | None = None,
    status_path: Path | None = None,
) -> dict[str, Any]:
    research_root = research_root.resolve()
    evidence_root = (research_root / "evidence").resolve()
    chosen_multiwindow = (
        multiwindow_status_path or (research_root / DEFAULT_MULTIWINDOW_STATUS_PATH.name)
    ).resolve()
    chosen_status = (status_path or (research_root / DEFAULT_STATUS_PATH.name)).resolve()

    try:
        multi_status, multi_report = _load_complete_multiwindow_status(
            chosen_multiwindow,
            evidence_root=evidence_root,
        )
        evaluation_id = str(multi_status.get("evaluationId") or "")
        if not evaluation_id:
            raise RuntimeError("M5 multi-window status is missing evaluationId")

        reusable = _reusable_status(
            status_path=chosen_status,
            evaluation_id=evaluation_id,
            evidence_root=evidence_root,
        )
        if reusable is not None:
            return reusable

        _atomic_write(
            chosen_status,
            {
                **_base_status(phase="RUNNING", status_path=chosen_status),
                "evaluationId": evaluation_id,
                "materializationId": multi_status.get("materializationId"),
            },
        )
        report = evaluate_candidate_qualification(multi_report)
        qualification_id = str(report["qualificationId"])
        report_path = evidence_root / f"m5-robustness-qualification-{qualification_id}.json"
        write_immutable_qualification_report(report_path, report)

        complete = {
            **_base_status(phase="COMPLETE", status_path=chosen_status),
            "complete": True,
            "evaluationId": evaluation_id,
            "materializationId": multi_status.get("materializationId"),
            "qualificationId": qualification_id,
            "reportPath": str(report_path),
            "candidateCount": report.get("candidateCount"),
            "eligibleCandidateCount": report.get("eligibleCandidateCount"),
            "topEligibleCandidate": report.get("topEligibleCandidate"),
            "topEligibleParameters": report.get("topEligibleParameters"),
            "qualificationState": report.get("qualificationState"),
            "policy": report.get("policy"),
        }
        _atomic_write(chosen_status, complete)
        return complete
    except Exception as exc:
        failed = {
            **_base_status(phase="FAILED", status_path=chosen_status),
            "safe": False,
            "errorType": type(exc).__name__,
            "errorSummary": str(exc)[:240],
        }
        _atomic_write(chosen_status, failed)
        raise


def main() -> int:
    research_root = Path(os.environ.get("EBA_RESEARCH_ROOT", str(DEFAULT_RESEARCH_ROOT)))
    multiwindow_status = Path(
        os.environ.get(
            "EBA_M5_MULTIWINDOW_STATUS",
            str(research_root / DEFAULT_MULTIWINDOW_STATUS_PATH.name),
        )
    )
    status_path = Path(
        os.environ.get(
            "EBA_M5_QUALIFICATION_STATUS",
            str(research_root / DEFAULT_STATUS_PATH.name),
        )
    )
    try:
        payload = run_candidate_qualification(
            research_root=research_root,
            multiwindow_status_path=multiwindow_status,
            status_path=status_path,
        )
    except Exception:
        try:
            payload = json.loads(status_path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            payload = {"schema": STATUS_SCHEMA, "phase": "FAILED", "safe": False}
        print(json.dumps(payload, sort_keys=True, separators=(",", ":")))
        return 1
    print(json.dumps(payload, sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
