from __future__ import annotations

import json
import os
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .m5_corpus_materializer import DEFAULT_RESEARCH_ROOT, materialize_m5_development_corpus
from .m5_multiwindow_runtime import DEFAULT_REPO_ROOT
from .sf2_development import (
    DEVELOPMENT_REPORT_SCHEMA,
    ORDERFLOW_SOURCE,
    PRICE_BUCKET,
    SF2_NAMESPACE,
    VALIDATION_REPORT_SCHEMA,
    candidate_set_sha256,
    evaluate_sf2_development,
    validate_sf2_development,
    write_immutable_report,
)
from .sf2_protocol import load_sf2_protocol

STATUS_SCHEMA = "sf2_runtime_status_v1"
DEFAULT_STATUS_PATH = DEFAULT_RESEARCH_ROOT / "sf2-development-latest.json"
DEFAULT_PROTOCOL_PATH = Path("config/sf2_research_protocol_v1.json")


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


def _read_object(path: Path, *, label: str) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"cannot read {label}") from exc
    if not isinstance(payload, dict):
        raise RuntimeError(f"{label} must be a JSON object")
    return payload


def _base_status(*, phase: str, status_path: Path) -> dict[str, Any]:
    return {
        "schema": STATUS_SCHEMA,
        "phase": phase,
        "updatedAt": _utc_now(),
        "statusPath": str(status_path),
        "complete": False,
        "safe": True,
        "protocolId": None,
        "materializationId": None,
        "candidateSetSha256": None,
        "candidateCount": 24,
        "multipleTestingBudget": 48,
        "windowCount": 12,
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


def _safe_contract(payload: dict[str, Any], *, schema: str) -> bool:
    return (
        payload.get("schema") == schema
        and payload.get("developmentEvidenceOnly") is True
        and payload.get("edgeClaimAllowed") is False
        and payload.get("promotionAuthority") is False
        and payload.get("frozenOosOpened") is False
        and payload.get("m5FrozenOosOpened") is False
        and payload.get("liveExecutionAllowed") is False
    )


def _load_reusable_status(
    *,
    status_path: Path,
    protocol_id: str,
    materialization_id: str,
    candidate_sha: str,
) -> dict[str, Any] | None:
    if not status_path.is_file():
        return None
    try:
        payload = _read_object(status_path, label="SF2 runtime status")
    except RuntimeError:
        return None
    checks = (
        payload.get("schema") == STATUS_SCHEMA,
        payload.get("phase") == "COMPLETE",
        payload.get("complete") is True,
        payload.get("safe") is True,
        payload.get("protocolId") == protocol_id,
        payload.get("materializationId") == materialization_id,
        payload.get("candidateSetSha256") == candidate_sha,
        payload.get("candidateCount") == 24,
        payload.get("multipleTestingBudget") == 48,
        payload.get("windowCount") == 12,
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
    try:
        development = _read_object(development_path, label="SF2 development report")
        validation = _read_object(validation_path, label="SF2 validation report")
    except RuntimeError:
        return None
    report_checks = (
        _safe_contract(development, schema=DEVELOPMENT_REPORT_SCHEMA),
        _safe_contract(validation, schema=VALIDATION_REPORT_SCHEMA),
        development.get("evaluationId") == payload.get("developmentEvaluationId"),
        development.get("protocolId") == protocol_id,
        development.get("materializationId") == materialization_id,
        development.get("candidateSetSha256") == candidate_sha,
        validation.get("validationId") == payload.get("validationId"),
        validation.get("developmentEvaluationId") == development.get("evaluationId"),
        validation.get("protocolId") == protocol_id,
        validation.get("candidateSetSha256") == candidate_sha,
        validation.get("validationState") == payload.get("validationState"),
        validation.get("verifiedCandidateCount") == payload.get("verifiedCandidateCount"),
        validation.get("topVerifiedCandidate") == payload.get("topVerifiedCandidate"),
    )
    return payload if all(report_checks) else None


def run_sf2_development(
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
    protocol_path = repo_root / DEFAULT_PROTOCOL_PATH

    protocol = load_sf2_protocol(protocol_path)
    candidate_sha = candidate_set_sha256(protocol)
    _atomic_write(
        chosen_status,
        {
            **_base_status(phase="RUNNING", status_path=chosen_status),
            "protocolId": protocol.protocol_id,
            "candidateSetSha256": candidate_sha,
        },
    )

    try:
        materialization, manifest_path = materialize_m5_development_corpus(
            dataset_root=dataset_root,
            namespace=SF2_NAMESPACE,
            price_bucket=PRICE_BUCKET,
            orderflow_source=ORDERFLOW_SOURCE,
            corpus=protocol.corpus,
        )
        if materialization.corpus_id != protocol.corpus.corpus_id:
            raise RuntimeError("SF2 materialization corpus identity mismatch")
        if len(materialization.windows) != len(protocol.corpus.windows):
            raise RuntimeError("SF2 materialization window count mismatch")
        if any(
            not isinstance(window.feature_csv_sha256, str)
            or len(window.feature_csv_sha256) != 64
            for window in materialization.windows
        ):
            raise RuntimeError("SF2 materialization lacks feature integrity hashes")
        materialization_id = materialization.materialization_id

        reusable = _load_reusable_status(
            status_path=chosen_status,
            protocol_id=protocol.protocol_id,
            materialization_id=materialization_id,
            candidate_sha=candidate_sha,
        )
        if reusable is not None:
            return reusable

        _atomic_write(
            chosen_status,
            {
                **_base_status(phase="EVALUATING", status_path=chosen_status),
                "protocolId": protocol.protocol_id,
                "materializationId": materialization_id,
                "candidateSetSha256": candidate_sha,
                "materializationManifestPath": str(manifest_path),
            },
        )

        development = evaluate_sf2_development(
            manifest_path=manifest_path,
            dataset_root=dataset_root,
            protocol_path=protocol_path,
        )
        development_checks = (
            _safe_contract(development, schema=DEVELOPMENT_REPORT_SCHEMA),
            development.get("protocolId") == protocol.protocol_id,
            development.get("materializationId") == materialization_id,
            development.get("candidateSetSha256") == candidate_sha,
            development.get("candidateCount") == len(protocol.candidates),
            development.get("multipleTestingBudget") == protocol.planned_candidate_budget,
            development.get("windowCount") == len(protocol.corpus.windows),
        )
        if not all(development_checks):
            raise RuntimeError("SF2 development report identity or safety mismatch")
        evaluation_id = str(development.get("evaluationId") or "")
        if not evaluation_id:
            raise RuntimeError("SF2 development report is missing evaluationId")
        development_path = evidence_root / f"sf2-development-{evaluation_id}.json"
        write_immutable_report(development_path, development)

        validation = validate_sf2_development(development, protocol_path=protocol_path)
        validation_checks = (
            _safe_contract(validation, schema=VALIDATION_REPORT_SCHEMA),
            validation.get("protocolId") == protocol.protocol_id,
            validation.get("developmentEvaluationId") == evaluation_id,
            validation.get("materializationId") == materialization_id,
            validation.get("candidateSetSha256") == candidate_sha,
            validation.get("candidateCount") == len(protocol.candidates),
            validation.get("multipleTestingBudget") == protocol.planned_candidate_budget,
            validation.get("windowCount") == len(protocol.corpus.windows),
        )
        if not all(validation_checks):
            raise RuntimeError("SF2 validation report identity or safety mismatch")
        validation_id = str(validation.get("validationId") or "")
        if not validation_id:
            raise RuntimeError("SF2 validation report is missing validationId")
        validation_path = evidence_root / f"sf2-validation-{validation_id}.json"
        write_immutable_report(validation_path, validation)

        complete = {
            **_base_status(phase="COMPLETE", status_path=chosen_status),
            "complete": True,
            "protocolId": protocol.protocol_id,
            "materializationId": materialization_id,
            "materializationManifestPath": str(manifest_path),
            "candidateSetSha256": candidate_sha,
            "developmentEvaluationId": evaluation_id,
            "developmentReportPath": str(development_path),
            "validationId": validation_id,
            "validationReportPath": str(validation_path),
            "validationState": validation.get("validationState"),
            "verifiedCandidateCount": validation.get("verifiedCandidateCount"),
            "topVerifiedCandidate": validation.get("topVerifiedCandidate"),
            "topDevelopmentCandidate": development.get("topDevelopmentCandidate"),
        }
        _atomic_write(chosen_status, complete)
        return complete
    except Exception as exc:
        failed = {
            **_base_status(phase="FAILED", status_path=chosen_status),
            "protocolId": protocol.protocol_id,
            "candidateSetSha256": candidate_sha,
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
            "EBA_SF2_STATUS",
            str(research_root / DEFAULT_STATUS_PATH.name),
        )
    )
    try:
        payload = run_sf2_development(
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
