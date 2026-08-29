from __future__ import annotations

import json
import math
import os
from pathlib import Path
from typing import Any

DEFAULT_SF1_STATUS_PATH = Path("/var/lib/eba-trader/research/sf1-development-latest.json")
DEFAULT_EVIDENCE_ROOT = Path("/var/lib/eba-trader/research/evidence")
STATUS_SCHEMA = "sf1_runtime_status_v1"
DEVELOPMENT_SCHEMA = "sf1_development_report_v1"
VALIDATION_SCHEMA = "sf1_validation_report_v1"
_BLOCKED_KEY_PARTS = (
    "apikey",
    "apisecret",
    "authorization",
    "credential",
    "keyfile",
    "password",
    "path",
    "secret",
    "signature",
    "token",
    "evidenceref",
    "datasetref",
)


def _unavailable(reason: str) -> dict[str, Any]:
    return {
        "available": False,
        "reason": reason,
        "developmentEvidenceOnly": True,
        "edgeClaimAllowed": False,
        "promotionAuthority": False,
        "frozenOosOpened": False,
        "m5FrozenOosOpened": False,
        "liveExecutionAllowed": False,
    }


def _read_object(path: Path) -> dict[str, Any] | None:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return payload if isinstance(payload, dict) else None


def _safe_scalar_map(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        return {}
    result: dict[str, Any] = {}
    for raw_key, item in value.items():
        key = str(raw_key)
        normalized = key.replace("_", "").replace("-", "").lower()
        if any(part in normalized for part in _BLOCKED_KEY_PARTS):
            continue
        if isinstance(item, bool) or isinstance(item, int):
            result[key] = item
        elif isinstance(item, float) and math.isfinite(item):
            result[key] = item
        elif isinstance(item, str) and len(item) <= 128:
            result[key] = item
    return result


def _safe_contract(payload: dict[str, Any]) -> bool:
    return (
        payload.get("developmentEvidenceOnly") is True
        and payload.get("edgeClaimAllowed") is False
        and payload.get("promotionAuthority") is False
        and payload.get("frozenOosOpened") is False
        and payload.get("m5FrozenOosOpened") is False
        and payload.get("liveExecutionAllowed") is False
    )


def _evidence_path(root: Path, raw: Any) -> Path | None:
    if not isinstance(raw, str) or not raw.strip():
        return None
    try:
        path = Path(raw).resolve()
        path.relative_to(root)
    except (OSError, RuntimeError, ValueError):
        return None
    if path.suffix != ".json" or not path.is_file():
        return None
    return path


def _safe_ranking(rows: Any) -> list[dict[str, Any]]:
    if not isinstance(rows, list):
        return []
    result: list[dict[str, Any]] = []
    for row in rows[:12]:
        if not isinstance(row, dict):
            continue
        result.append(
            {
                "developmentPriorityRank": row.get("developmentPriorityRank"),
                "candidateId": row.get("candidateId"),
                "family": row.get("family"),
                "parameters": _safe_scalar_map(row.get("parameters")),
                "aggregate": _safe_scalar_map(row.get("aggregate")),
            }
        )
    return result


def _safe_validation_rows(rows: Any) -> list[dict[str, Any]]:
    if not isinstance(rows, list):
        return []
    result: list[dict[str, Any]] = []
    for row in rows[:12]:
        if not isinstance(row, dict):
            continue
        failed_raw = row.get("failedChecks")
        failed = (
            [str(item)[:80] for item in failed_raw if isinstance(item, str)][:8]
            if isinstance(failed_raw, list)
            else []
        )
        result.append(
            {
                "candidateId": row.get("candidateId"),
                "family": row.get("family"),
                "parameters": _safe_scalar_map(row.get("parameters")),
                "qualified": row.get("qualified") is True,
                "verifiedForRobustness": row.get("verifiedForRobustness") is True,
                "failedChecks": failed,
                "checks": _safe_scalar_map(row.get("checks")),
                "windowCount": row.get("windowCount"),
                "positiveDeltaWindowCount": row.get("positiveDeltaWindowCount"),
                "observedMeanReturnDeltaVsBaseline": row.get(
                    "observedMeanReturnDeltaVsBaseline"
                ),
                "rawPValue": row.get("rawPValue"),
                "adjustedPValue": row.get("adjustedPValue"),
                "multipleTestingBudget": row.get("multipleTestingBudget"),
                "permutationCount": row.get("permutationCount"),
            }
        )
    return result


def read_sf1_summary(
    *,
    status_path: str | Path | None = None,
    evidence_root: str | Path | None = None,
) -> dict[str, Any]:
    configured_status = (
        status_path
        or os.getenv("EBA_SF1_STATUS", "").strip()
        or DEFAULT_SF1_STATUS_PATH
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
        development.get("materializationId") == status.get("materializationId"),
        development.get("candidateSetSha256") == status.get("candidateSetSha256"),
        validation.get("validationId") == status.get("validationId"),
        validation.get("developmentEvaluationId") == development.get("evaluationId"),
        validation.get("candidateSetSha256") == development.get("candidateSetSha256"),
        validation.get("candidateCount") == development.get("candidateCount"),
        validation.get("multipleTestingBudget") == development.get("multipleTestingBudget"),
    )
    if not all(identity_checks):
        return _unavailable("report_identity_rejected")

    ranking = _safe_ranking(development.get("developmentRanking"))
    validation_rows = _safe_validation_rows(validation.get("candidateValidation"))
    return {
        "available": True,
        "schema": STATUS_SCHEMA,
        "phase": "COMPLETE",
        "candidateCount": status.get("candidateCount"),
        "multipleTestingBudget": status.get("multipleTestingBudget"),
        "warmupBars": status.get("warmupBars"),
        "windowCount": status.get("windowCount"),
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
