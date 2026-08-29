from __future__ import annotations

import json
import os
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .m5_candidate_qualification import REPORT_SCHEMA as QUALIFICATION_REPORT_SCHEMA
from .m5_candidate_qualification_runtime import STATUS_SCHEMA as QUALIFICATION_STATUS_SCHEMA
from .m5_candidate_significance import (
    REPORT_SCHEMA,
    evaluate_candidate_significance,
    write_immutable_significance_report,
)
from .m5_corpus_materializer import DEFAULT_RESEARCH_ROOT
from .m5_multiwindow import REPORT_SCHEMA as MULTIWINDOW_REPORT_SCHEMA
from .m5_multiwindow_runtime import STATUS_SCHEMA as MULTIWINDOW_STATUS_SCHEMA

STATUS_SCHEMA = "m5_candidate_significance_runtime_status_v1"
DEFAULT_STATUS_PATH = DEFAULT_RESEARCH_ROOT / "m5-candidate-significance-latest.json"
MULTIWINDOW_STATUS_NAME = "m5-multiwindow-evaluation-latest.json"
QUALIFICATION_STATUS_NAME = "m5-robustness-qualification-latest.json"


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
        "significanceVerified": False,
        "significanceState": "UNKNOWN",
        "topSignificantCandidate": None,
        "topSignificantParameters": None,
        "developmentEvidenceOnly": True,
        "edgeClaimAllowed": False,
        "promotionAuthority": False,
        "frozenOosOpened": False,
        "m5FrozenOosOpened": False,
        "liveExecutionAllowed": False,
    }


def _resolve_report(
    status: dict[str, Any],
    *,
    expected_status_schema: str,
    expected_report_schema: str,
    evidence_root: Path,
    label: str,
) -> dict[str, Any]:
    checks = (
        status.get("schema") == expected_status_schema,
        status.get("phase") == "COMPLETE",
        status.get("complete") is True,
        status.get("safe") is True,
        status.get("edgeClaimAllowed") is False,
        status.get("promotionAuthority") is False,
        status.get("frozenOosOpened") is False,
        status.get("m5FrozenOosOpened") is False,
        status.get("liveExecutionAllowed") is False,
    )
    if not all(checks):
        raise RuntimeError(f"{label} status is not safely complete")
    report_raw = status.get("reportPath")
    if not isinstance(report_raw, str) or not report_raw.strip():
        raise RuntimeError(f"{label} status is missing reportPath")
    report_path = Path(report_raw).resolve()
    try:
        report_path.relative_to(evidence_root.resolve())
    except ValueError as exc:
        raise RuntimeError(f"{label} report escapes evidence root") from exc
    if not report_path.is_file():
        raise RuntimeError(f"{label} report is missing")
    report = _read_json(report_path, label=f"{label} report")
    if report.get("schema") != expected_report_schema:
        raise RuntimeError(f"{label} report schema mismatch")
    return report


def _load_inputs(
    *,
    research_root: Path,
    multiwindow_status_path: Path,
    qualification_status_path: Path,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any]]:
    evidence_root = (research_root / "evidence").resolve()
    multi_status = _read_json(multiwindow_status_path, label="M5 multi-window status")
    qualification_status = _read_json(
        qualification_status_path, label="M5 qualification status"
    )
    multi_report = _resolve_report(
        multi_status,
        expected_status_schema=MULTIWINDOW_STATUS_SCHEMA,
        expected_report_schema=MULTIWINDOW_REPORT_SCHEMA,
        evidence_root=evidence_root,
        label="M5 multi-window",
    )
    qualification_report = _resolve_report(
        qualification_status,
        expected_status_schema=QUALIFICATION_STATUS_SCHEMA,
        expected_report_schema=QUALIFICATION_REPORT_SCHEMA,
        evidence_root=evidence_root,
        label="M5 qualification",
    )
    if multi_status.get("rankingIsDevelopmentOnly") is not True:
        raise RuntimeError("M5 multi-window runtime ranking is not development-only")
    if qualification_status.get("developmentEvidenceOnly") is not True:
        raise RuntimeError("M5 qualification runtime evidence is not development-only")
    for key in ("evaluationId", "materializationId"):
        if multi_status.get(key) != qualification_status.get(key):
            raise RuntimeError(f"M5 significance runtime input mismatch: {key}")
    if multi_report.get("evaluationId") != qualification_report.get("evaluationId"):
        raise RuntimeError("M5 significance immutable evaluation identity mismatch")
    if multi_report.get("candidateSetSha256") != qualification_report.get("candidateSetSha256"):
        raise RuntimeError("M5 significance candidate-set identity mismatch")
    return multi_status, multi_report, qualification_status, qualification_report


def _reusable_status(
    *,
    status_path: Path,
    evaluation_id: str,
    qualification_id: str,
    evidence_root: Path,
) -> dict[str, Any] | None:
    if not status_path.is_file():
        return None
    payload = _read_json(status_path, label="M5 significance status")
    checks = (
        payload.get("schema") == STATUS_SCHEMA,
        payload.get("phase") == "COMPLETE",
        payload.get("complete") is True,
        payload.get("safe") is True,
        payload.get("evaluationId") == evaluation_id,
        payload.get("qualificationId") == qualification_id,
        payload.get("developmentEvidenceOnly") is True,
        payload.get("edgeClaimAllowed") is False,
        payload.get("promotionAuthority") is False,
        payload.get("frozenOosOpened") is False,
        payload.get("m5FrozenOosOpened") is False,
        payload.get("liveExecutionAllowed") is False,
    )
    if not all(checks):
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
    report = _read_json(report_path, label="M5 significance report")
    if (
        report.get("schema") != REPORT_SCHEMA
        or report.get("significanceId") != payload.get("significanceId")
        or report.get("evaluationId") != evaluation_id
        or report.get("qualificationId") != qualification_id
        or report.get("developmentEvidenceOnly") is not True
        or report.get("edgeClaimAllowed") is not False
        or report.get("promotionAuthority") is not False
        or report.get("frozenOosOpened") is not False
        or report.get("m5FrozenOosOpened") is not False
        or report.get("liveExecutionAllowed") is not False
    ):
        return None
    return payload


def run_candidate_significance(
    *,
    research_root: Path = DEFAULT_RESEARCH_ROOT,
    multiwindow_status_path: Path | None = None,
    qualification_status_path: Path | None = None,
    status_path: Path | None = None,
) -> dict[str, Any]:
    research_root = research_root.resolve()
    evidence_root = (research_root / "evidence").resolve()
    chosen_multiwindow = (
        multiwindow_status_path or (research_root / MULTIWINDOW_STATUS_NAME)
    ).resolve()
    chosen_qualification = (
        qualification_status_path or (research_root / QUALIFICATION_STATUS_NAME)
    ).resolve()
    chosen_status = (status_path or (research_root / DEFAULT_STATUS_PATH.name)).resolve()

    try:
        multi_status, multi_report, qualification_status, qualification_report = _load_inputs(
            research_root=research_root,
            multiwindow_status_path=chosen_multiwindow,
            qualification_status_path=chosen_qualification,
        )
        evaluation_id = str(multi_status.get("evaluationId") or "")
        qualification_id = str(qualification_status.get("qualificationId") or "")
        if not evaluation_id or not qualification_id:
            raise RuntimeError("M5 significance runtime input identity is incomplete")

        reusable = _reusable_status(
            status_path=chosen_status,
            evaluation_id=evaluation_id,
            qualification_id=qualification_id,
            evidence_root=evidence_root,
        )
        if reusable is not None:
            return reusable

        _atomic_write(
            chosen_status,
            {
                **_base_status(phase="RUNNING", status_path=chosen_status),
                "evaluationId": evaluation_id,
                "qualificationId": qualification_id,
                "materializationId": multi_status.get("materializationId"),
            },
        )
        report = evaluate_candidate_significance(multi_report, qualification_report)
        significance_id = str(report["significanceId"])
        report_path = evidence_root / f"m5-candidate-significance-{significance_id}.json"
        write_immutable_significance_report(report_path, report)
        verified = report.get("significantCandidateCount", 0) > 0
        complete = {
            **_base_status(phase="COMPLETE", status_path=chosen_status),
            "complete": True,
            "evaluationId": evaluation_id,
            "qualificationId": qualification_id,
            "materializationId": multi_status.get("materializationId"),
            "significanceId": significance_id,
            "reportPath": str(report_path),
            "candidateCount": report.get("candidateCount"),
            "eligibleCandidateCount": report.get("eligibleCandidateCount"),
            "testedCandidateCount": report.get("testedCandidateCount"),
            "significantCandidateCount": report.get("significantCandidateCount"),
            "topSignificantCandidate": report.get("topSignificantCandidate"),
            "topSignificantParameters": report.get("topSignificantParameters"),
            "significanceState": report.get("significanceState"),
            "significanceVerified": verified,
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
            str(research_root / MULTIWINDOW_STATUS_NAME),
        )
    )
    qualification_status = Path(
        os.environ.get(
            "EBA_M5_QUALIFICATION_STATUS",
            str(research_root / QUALIFICATION_STATUS_NAME),
        )
    )
    status_path = Path(
        os.environ.get(
            "EBA_M5_SIGNIFICANCE_STATUS",
            str(research_root / DEFAULT_STATUS_PATH.name),
        )
    )
    try:
        payload = run_candidate_significance(
            research_root=research_root,
            multiwindow_status_path=multiwindow_status,
            qualification_status_path=qualification_status,
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
