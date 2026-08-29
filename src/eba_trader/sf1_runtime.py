from __future__ import annotations

import json
import os
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .m5_corpus_materializer import DEFAULT_RESEARCH_ROOT
from .m5_multiwindow_runtime import DEFAULT_REPO_ROOT, _load_complete_corpus_status
from .research_evidence import canonical_json, sha256_text
from .sf1_strategy_factory import (
    REPORT_SCHEMA as DEVELOPMENT_REPORT_SCHEMA,
    SF1Candidate,
    evaluate_sf1_atr,
    load_sf1_candidates,
    write_immutable_sf1_report,
)
from .sf1_validation import (
    REPORT_SCHEMA as VALIDATION_REPORT_SCHEMA,
    validate_sf1_development,
    write_immutable_sf1_validation,
)

STATUS_SCHEMA = "sf1_runtime_status_v1"
DEFAULT_STATUS_PATH = DEFAULT_RESEARCH_ROOT / "sf1-development-latest.json"
DEFAULT_CANDIDATE_PATH = Path("config/sf1_candidate_set_v1.json")


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


def _read_json(path: Path, *, label: str) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"cannot read {label}") from exc
    if not isinstance(payload, dict):
        raise RuntimeError(f"{label} must be a JSON object")
    return payload


def _candidate_set_sha(candidates: tuple[SF1Candidate, ...]) -> str:
    return sha256_text(canonical_json([candidate.as_dict() for candidate in candidates]))


def _base_status(*, phase: str, status_path: Path) -> dict[str, Any]:
    return {
        "schema": STATUS_SCHEMA,
        "phase": phase,
        "updatedAt": _utc_now(),
        "statusPath": str(status_path),
        "complete": False,
        "safe": True,
        "candidateCount": None,
        "multipleTestingBudget": None,
        "windowCount": None,
        "validationState": "UNKNOWN",
        "verifiedCandidateCount": 0,
        "topVerifiedCandidate": None,
        "developmentEvidenceOnly": True,
        "edgeClaimAllowed": False,
        "promotionAuthority": False,
        "frozenOosOpened": False,
        "m5FrozenOosOpened": False,
        "liveExecutionAllowed": False,
    }


def _safe_report(report: dict[str, Any], *, schema: str) -> bool:
    return (
        report.get("schema") == schema
        and report.get("developmentEvidenceOnly") is True
        and report.get("edgeClaimAllowed") is False
        and report.get("promotionAuthority") is False
        and report.get("frozenOosOpened") is False
        and report.get("m5FrozenOosOpened") is False
        and report.get("liveExecutionAllowed") is False
    )


def _load_reusable_status(
    *,
    status_path: Path,
    materialization_id: str,
    candidate_set_sha: str,
    candidate_count: int,
    multiple_testing_budget: int,
) -> dict[str, Any] | None:
    if not status_path.is_file():
        return None
    payload = _read_json(status_path, label="SF1 runtime status")
    checks = (
        payload.get("schema") == STATUS_SCHEMA,
        payload.get("phase") == "COMPLETE",
        payload.get("complete") is True,
        payload.get("safe") is True,
        payload.get("materializationId") == materialization_id,
        payload.get("candidateSetSha256") == candidate_set_sha,
        payload.get("candidateCount") == candidate_count,
        payload.get("multipleTestingBudget") == multiple_testing_budget,
        payload.get("developmentEvidenceOnly") is True,
        payload.get("edgeClaimAllowed") is False,
        payload.get("promotionAuthority") is False,
        payload.get("frozenOosOpened") is False,
        payload.get("m5FrozenOosOpened") is False,
        payload.get("liveExecutionAllowed") is False,
    )
    if not all(checks):
        return None

    development_raw = payload.get("developmentReportPath")
    validation_raw = payload.get("validationReportPath")
    if not isinstance(development_raw, str) or not isinstance(validation_raw, str):
        return None
    development_path = Path(development_raw)
    validation_path = Path(validation_raw)
    if not development_path.is_file() or not validation_path.is_file():
        return None

    development = _read_json(development_path, label="SF1 development report")
    validation = _read_json(validation_path, label="SF1 validation report")
    if not _safe_report(development, schema=DEVELOPMENT_REPORT_SCHEMA):
        return None
    if not _safe_report(validation, schema=VALIDATION_REPORT_SCHEMA):
        return None
    report_checks = (
        development.get("evaluationId") == payload.get("developmentEvaluationId"),
        development.get("materializationId") == materialization_id,
        development.get("candidateSetSha256") == candidate_set_sha,
        development.get("candidateCount") == candidate_count,
        development.get("multipleTestingBudget") == multiple_testing_budget,
        validation.get("validationId") == payload.get("validationId"),
        validation.get("developmentEvaluationId") == development.get("evaluationId"),
        validation.get("candidateSetSha256") == candidate_set_sha,
        validation.get("candidateCount") == candidate_count,
        validation.get("multipleTestingBudget") == multiple_testing_budget,
        validation.get("validationState") == payload.get("validationState"),
        validation.get("verifiedCandidateCount") == payload.get("verifiedCandidateCount"),
        validation.get("topVerifiedCandidate") == payload.get("topVerifiedCandidate"),
    )
    return payload if all(report_checks) else None


def run_sf1_development(
    *,
    research_root: Path = DEFAULT_RESEARCH_ROOT,
    repo_root: Path = DEFAULT_REPO_ROOT,
    status_path: Path | None = None,
) -> dict[str, Any]:
    research_root = research_root.resolve()
    repo_root = repo_root.resolve()
    chosen_status = (status_path or (research_root / DEFAULT_STATUS_PATH.name)).resolve()
    dataset_root = (research_root / "datasets").resolve()
    evidence_root = (research_root / "evidence").resolve()
    candidate_path = repo_root / DEFAULT_CANDIDATE_PATH

    try:
        corpus = _load_complete_corpus_status(research_root)
        budget, warmup_bars, candidates = load_sf1_candidates(candidate_path)
        candidate_set_sha = _candidate_set_sha(candidates)
        materialization_id = str(corpus.get("materializationId") or "")
        if not materialization_id:
            raise RuntimeError("M5 corpus runtime status is missing materializationId")

        reusable = _load_reusable_status(
            status_path=chosen_status,
            materialization_id=materialization_id,
            candidate_set_sha=candidate_set_sha,
            candidate_count=len(candidates),
            multiple_testing_budget=budget,
        )
        if reusable is not None:
            return reusable

        _atomic_write(
            chosen_status,
            {
                **_base_status(phase="RUNNING", status_path=chosen_status),
                "materializationId": materialization_id,
                "candidateSetSha256": candidate_set_sha,
                "candidateCount": len(candidates),
                "multipleTestingBudget": budget,
                "warmupBars": warmup_bars,
            },
        )

        development = evaluate_sf1_atr(
            manifest_path=str(corpus["manifestPath"]),
            dataset_root=dataset_root,
            candidate_set_path=candidate_path,
        )
        development_checks = (
            development.get("schema") == DEVELOPMENT_REPORT_SCHEMA,
            development.get("materializationId") == materialization_id,
            development.get("candidateSetSha256") == candidate_set_sha,
            development.get("candidateCount") == len(candidates),
            development.get("multipleTestingBudget") == budget,
            development.get("warmupBars") == warmup_bars,
            _safe_report(development, schema=DEVELOPMENT_REPORT_SCHEMA),
        )
        if not all(development_checks):
            raise RuntimeError("SF1 development report identity or safety mismatch")

        evaluation_id = str(development.get("evaluationId") or "")
        if not evaluation_id:
            raise RuntimeError("SF1 development report is missing evaluationId")
        development_path = evidence_root / f"sf1-development-{evaluation_id}.json"
        write_immutable_sf1_report(development_path, development)

        validation = validate_sf1_development(development)
        validation_checks = (
            validation.get("schema") == VALIDATION_REPORT_SCHEMA,
            validation.get("developmentEvaluationId") == evaluation_id,
            validation.get("candidateSetSha256") == candidate_set_sha,
            validation.get("candidateCount") == len(candidates),
            validation.get("multipleTestingBudget") == budget,
            _safe_report(validation, schema=VALIDATION_REPORT_SCHEMA),
        )
        if not all(validation_checks):
            raise RuntimeError("SF1 validation report identity or safety mismatch")

        validation_id = str(validation.get("validationId") or "")
        if not validation_id:
            raise RuntimeError("SF1 validation report is missing validationId")
        validation_path = evidence_root / f"sf1-validation-{validation_id}.json"
        write_immutable_sf1_validation(validation_path, validation)

        complete = {
            **_base_status(phase="COMPLETE", status_path=chosen_status),
            "complete": True,
            "materializationId": materialization_id,
            "candidateSetSha256": candidate_set_sha,
            "candidateCount": len(candidates),
            "multipleTestingBudget": budget,
            "warmupBars": warmup_bars,
            "windowCount": development.get("windowCount"),
            "developmentEvaluationId": evaluation_id,
            "developmentReportPath": str(development_path),
            "validationId": validation_id,
            "validationReportPath": str(validation_path),
            "validationState": validation.get("validationState"),
            "verifiedCandidateCount": validation.get("verifiedCandidateCount"),
            "topVerifiedCandidate": validation.get("topVerifiedCandidate"),
        }
        _atomic_write(chosen_status, complete)
        return complete
    except Exception as exc:
        failed = {
            **_base_status(phase="FAILED", status_path=chosen_status),
            "errorType": type(exc).__name__,
            "errorSummary": str(exc)[:240],
        }
        _atomic_write(chosen_status, failed)
        raise


def main() -> int:
    research_root = Path(os.environ.get("EBA_RESEARCH_ROOT", str(DEFAULT_RESEARCH_ROOT)))
    repo_root = Path(os.environ.get("EBA_REPO_DIR", str(DEFAULT_REPO_ROOT)))
    status_path = Path(
        os.environ.get(
            "EBA_SF1_STATUS",
            str(research_root / DEFAULT_STATUS_PATH.name),
        )
    )
    try:
        payload = run_sf1_development(
            research_root=research_root,
            repo_root=repo_root,
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
