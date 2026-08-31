from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from .sf2_dashboard import (
    _evidence_path,
    _read_object,
    _safe_contract,
    _safe_ranking,
    _safe_validation_rows,
    _unavailable,
)

DEFAULT_SF3_STATUS_PATH = Path("/var/lib/eba-trader/research/sf3-development-latest.json")
DEFAULT_EVIDENCE_ROOT = Path("/var/lib/eba-trader/research/evidence")
STATUS_SCHEMA = "sf3_runtime_status_v1"
DEVELOPMENT_SCHEMA = "sf3_development_report_v1"
VALIDATION_SCHEMA = "sf3_validation_report_v1"


def read_sf3_summary(
    *,
    status_path: str | Path | None = None,
    evidence_root: str | Path | None = None,
) -> dict[str, Any]:
    configured_status = (
        status_path
        or os.getenv("EBA_SF3_STATUS", "").strip()
        or DEFAULT_SF3_STATUS_PATH
    )
    configured_evidence = (
        evidence_root
        or os.getenv("EBA_RESEARCH_EVIDENCE_DIR", "").strip()
        or DEFAULT_EVIDENCE_ROOT
    )
    status = _read_object(Path(configured_status))
    if status is None:
        return _unavailable("status_unavailable")
    if (
        status.get("schema") != STATUS_SCHEMA
        or status.get("phase") != "COMPLETE"
        or status.get("complete") is not True
        or status.get("safe") is not True
        or not _safe_contract(status)
    ):
        return _unavailable("status_safety_rejected")
    if (
        status.get("candidateCount") != 24
        or status.get("multipleTestingBudget") != 48
        or status.get("windowCount") != 12
    ):
        return _unavailable("status_contract_rejected")

    try:
        root = Path(configured_evidence).resolve()
    except (OSError, RuntimeError):
        return _unavailable("evidence_root_rejected")
    development_path = _evidence_path(root, status.get("developmentReportPath"))
    validation_path = _evidence_path(root, status.get("validationReportPath"))
    if development_path is None or validation_path is None:
        return _unavailable("report_path_rejected")

    development = _read_object(development_path)
    validation = _read_object(validation_path)
    if development is None or validation is None:
        return _unavailable("report_invalid")
    if development.get("schema") != DEVELOPMENT_SCHEMA:
        return _unavailable("development_schema_rejected")
    if validation.get("schema") != VALIDATION_SCHEMA:
        return _unavailable("validation_schema_rejected")
    if not _safe_contract(development) or not _safe_contract(validation):
        return _unavailable("report_safety_rejected")

    identity_checks = (
        development.get("evaluationId") == status.get("developmentEvaluationId"),
        development.get("protocolId") == status.get("protocolId"),
        development.get("materializationId") == status.get("materializationId"),
        development.get("candidateSetSha256") == status.get("candidateSetSha256"),
        development.get("candidateCount") == 24,
        development.get("multipleTestingBudget") == 48,
        development.get("windowCount") == 12,
        validation.get("validationId") == status.get("validationId"),
        validation.get("developmentEvaluationId") == development.get("evaluationId"),
        validation.get("protocolId") == development.get("protocolId"),
        validation.get("materializationId") == development.get("materializationId"),
        validation.get("candidateSetSha256") == development.get("candidateSetSha256"),
        validation.get("candidateCount") == 24,
        validation.get("multipleTestingBudget") == 48,
        validation.get("windowCount") == 12,
        validation.get("validationState") == status.get("validationState"),
        validation.get("verifiedCandidateCount") == status.get("verifiedCandidateCount"),
        validation.get("topVerifiedCandidate") == status.get("topVerifiedCandidate"),
    )
    if not all(identity_checks):
        return _unavailable("report_identity_rejected")

    ranking = _safe_ranking(development.get("developmentRanking"))
    validation_rows = _safe_validation_rows(validation.get("candidateValidation"))
    return {
        "available": True,
        "schema": STATUS_SCHEMA,
        "phase": "COMPLETE",
        "protocolId": status.get("protocolId"),
        "candidateCount": 24,
        "multipleTestingBudget": 48,
        "windowCount": 12,
        "validationState": status.get("validationState"),
        "verifiedCandidateCount": status.get("verifiedCandidateCount"),
        "topVerifiedCandidate": status.get("topVerifiedCandidate"),
        "topDevelopmentCandidate": ranking[0].get("candidateId") if ranking else None,
        "topDevelopmentAggregate": ranking[0].get("aggregate") if ranking else {},
        "developmentRanking": ranking,
        "candidateValidation": validation_rows,
        "developmentEvidenceOnly": True,
        "edgeClaimAllowed": False,
        "promotionAuthority": False,
        "frozenOosOpened": False,
        "m5FrozenOosOpened": False,
        "liveExecutionAllowed": False,
    }
