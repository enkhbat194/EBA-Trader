from __future__ import annotations

import json
import math
import os
from pathlib import Path
from typing import Any

from .strategy_factory_v2_authorized import STATUS_SCHEMA
from .strategy_factory_v2_postmortem import POSTMORTEM_SCHEMA

DEFAULT_STATUS_PATH = Path("/var/lib/eba-trader/research/sfv2-d0-pilot-status.json")
DEFAULT_POSTMORTEM_PATH = Path(
    "/var/lib/eba-trader/research/sfv2-d0-failure-postmortem.json"
)
_MAX_TOP_CANDIDATES = 10
_MAX_POSTMORTEM_FAMILIES = 16


def _unavailable(reason: str) -> dict[str, Any]:
    return {
        "available": False,
        "reason": reason,
        "authority": "DISCOVERY_ONLY",
        "freshConfirmationEvidence": False,
        "verificationAuthority": False,
        "d1Opened": False,
        "frozenOosOpened": False,
        "liveExecutionAllowed": False,
        "realExecutionAllowed": False,
    }


def _postmortem_unavailable(reason: str) -> dict[str, Any]:
    return {
        "available": False,
        "reason": reason,
        "authority": "DISCOVERY_DIAGNOSTIC_ONLY",
        "freshConfirmationEvidence": False,
        "verificationAuthority": False,
        "d1Opened": False,
        "frozenOosOpened": False,
        "liveExecutionAllowed": False,
        "realExecutionAllowed": False,
    }


def _safe_number(value: Any) -> int | float | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, float) and math.isfinite(value):
        return value
    return None


def _safe_small_map(value: Any) -> dict[str, int | float | str | None]:
    if not isinstance(value, dict):
        return {}
    result: dict[str, int | float | str | None] = {}
    for raw_key, raw_value in value.items():
        key = str(raw_key)[:128]
        if isinstance(raw_value, str):
            result[key] = raw_value[:256]
        elif raw_value is None:
            result[key] = None
        else:
            result[key] = _safe_number(raw_value)
    return result


def _safe_candidate(value: Any) -> dict[str, Any] | None:
    if not isinstance(value, dict):
        return None
    candidate_id = value.get("candidateId")
    family_id = value.get("familyId")
    if not isinstance(candidate_id, str) or not candidate_id or len(candidate_id) > 128:
        return None
    if not isinstance(family_id, str) or not family_id or len(family_id) > 128:
        return None
    return {
        "candidateId": candidate_id,
        "familyId": family_id,
        "complete": value.get("complete") is True,
        "rejected": value.get("rejected") is True,
        "eligibleForD0Survivor": value.get("eligibleForD0Survivor") is True,
        "selectedD0Survivor": value.get("selectedD0Survivor") is True,
        "meanTotalReturn": _safe_number(value.get("meanTotalReturn")),
        "meanExpectancy": _safe_number(value.get("meanExpectancy")),
        "totalTradeCount": _safe_number(value.get("totalTradeCount")),
        "meanBenchmarkRelativeReturn": _safe_number(
            value.get("meanBenchmarkRelativeReturn")
        ),
        "meanMaxDrawdown": _safe_number(value.get("meanMaxDrawdown")),
        "meanTotalCost": _safe_number(value.get("meanTotalCost")),
        "meanExposure": _safe_number(value.get("meanExposure")),
        "meanTurnover": _safe_number(value.get("meanTurnover")),
    }


def _safe_postmortem_family(value: Any) -> dict[str, Any] | None:
    if not isinstance(value, dict):
        return None
    family_id = value.get("familyId")
    diagnosis = value.get("primaryDiagnosis")
    if not isinstance(family_id, str) or not family_id or len(family_id) > 128:
        return None
    if not isinstance(diagnosis, str) or len(diagnosis) > 128:
        return None
    best = value.get("bestCandidate")
    safe_best: dict[str, Any] | None = None
    if isinstance(best, dict):
        candidate_id = best.get("candidateId")
        if isinstance(candidate_id, str) and candidate_id and len(candidate_id) <= 128:
            safe_best = {
                "candidateId": candidate_id,
                "meanNetReturn": _safe_number(best.get("meanNetReturn")),
                "meanExpectancy": _safe_number(best.get("meanExpectancy")),
                "totalTradeCount": _safe_number(best.get("totalTradeCount")),
                "meanBenchmarkDelta": _safe_number(best.get("meanBenchmarkDelta")),
                "costRecoveredReturnProxy": _safe_number(
                    best.get("costRecoveredReturnProxy")
                ),
                "feeBurdenReturnProxy": _safe_number(best.get("feeBurdenReturnProxy")),
                "slippageBurdenReturnProxy": _safe_number(
                    best.get("slippageBurdenReturnProxy")
                ),
                "failureFlags": [
                    str(item)[:128]
                    for item in best.get("failureFlags", [])
                    if isinstance(item, str)
                ][:16],
            }
    delay = value.get("oneBarDelayDiagnostic")
    safe_delay = _safe_small_map(delay)
    return {
        "familyId": family_id,
        "primaryDiagnosis": diagnosis,
        "candidateCount": _safe_number(value.get("candidateCount")),
        "completeNonRejectedCandidateCount": _safe_number(
            value.get("completeNonRejectedCandidateCount")
        ),
        "rejectedOrIncompleteCandidateCount": _safe_number(
            value.get("rejectedOrIncompleteCandidateCount")
        ),
        "adequateActivityCandidateCount": _safe_number(
            value.get("adequateActivityCandidateCount")
        ),
        "positiveNetCandidateCount": _safe_number(value.get("positiveNetCandidateCount")),
        "costSensitiveProxyCandidateCount": _safe_number(
            value.get("costSensitiveProxyCandidateCount")
        ),
        "totalTradeCount": _safe_number(value.get("totalTradeCount")),
        "medianCandidateTradeCount": _safe_number(value.get("medianCandidateTradeCount")),
        "meanCandidateNetReturn": _safe_number(value.get("meanCandidateNetReturn")),
        "meanCandidateExpectancy": _safe_number(value.get("meanCandidateExpectancy")),
        "meanCandidateBenchmarkDelta": _safe_number(
            value.get("meanCandidateBenchmarkDelta")
        ),
        "meanCandidateTotalCostUsd": _safe_number(
            value.get("meanCandidateTotalCostUsd")
        ),
        "failureFlagCounts": _safe_small_map(value.get("failureFlagCounts")),
        "rejectionReasonCounts": _safe_small_map(value.get("rejectionReasonCounts")),
        "bestCandidate": safe_best,
        "oneBarDelayDiagnostic": safe_delay,
        "regimeDiagnostics": value.get("regimeDiagnostics")
        if isinstance(value.get("regimeDiagnostics"), dict)
        else {},
    }


def read_sfv2_d0_postmortem(
    *, postmortem_path: str | Path | None = None
) -> dict[str, Any]:
    configured = (
        postmortem_path
        or os.getenv("EBA_SFV2_D0_POSTMORTEM_PATH", "").strip()
        or DEFAULT_POSTMORTEM_PATH
    )
    path = Path(configured)
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return _postmortem_unavailable("postmortem_unavailable")
    except (OSError, json.JSONDecodeError):
        return _postmortem_unavailable("postmortem_invalid")
    if not isinstance(payload, dict) or payload.get("schema") != POSTMORTEM_SCHEMA:
        return _postmortem_unavailable("postmortem_schema_rejected")
    safety_ok = (
        payload.get("authority") == "DISCOVERY_DIAGNOSTIC_ONLY"
        and payload.get("freshConfirmationEvidence") is False
        and payload.get("verificationAuthority") is False
        and payload.get("d1Opened") is False
        and payload.get("frozenOosOpened") is False
        and payload.get("liveExecutionAllowed") is False
        and payload.get("realExecutionAllowed") is False
    )
    if not safety_ok:
        return _postmortem_unavailable("postmortem_safety_rejected")
    if (
        payload.get("candidateCount") != 406
        or payload.get("familyCount") != 8
        or payload.get("stratumCount") != 12
        or payload.get("terminalTrialCount") != 4872
        or payload.get("survivorCount") != 0
    ):
        return _postmortem_unavailable("postmortem_completion_rejected")

    families_raw = payload.get("families")
    families: list[dict[str, Any]] = []
    if isinstance(families_raw, list):
        for item in families_raw[:_MAX_POSTMORTEM_FAMILIES]:
            safe = _safe_postmortem_family(item)
            if safe is not None:
                families.append(safe)
    if len(families) != 8:
        return _postmortem_unavailable("postmortem_family_count_rejected")

    return {
        "available": True,
        "authority": "DISCOVERY_DIAGNOSTIC_ONLY",
        "campaignId": payload.get("campaignId"),
        "sourceCodeSha": payload.get("sourceCodeSha"),
        "analysisCodeSha": payload.get("analysisCodeSha"),
        "generatedAt": payload.get("generatedAt"),
        "candidateCount": 406,
        "familyCount": 8,
        "stratumCount": 12,
        "terminalTrialCount": 4872,
        "survivorCount": 0,
        "roundTripFrictionBps": _safe_number(payload.get("roundTripFrictionBps")),
        "failureFlagCounts": _safe_small_map(payload.get("failureFlagCounts")),
        "familyDiagnosisCounts": _safe_small_map(payload.get("familyDiagnosisCounts")),
        "oneBarDelayDiagnostic": _safe_small_map(payload.get("oneBarDelayDiagnostic")),
        "families": families,
        "freshConfirmationEvidence": False,
        "verificationAuthority": False,
        "d1Opened": False,
        "frozenOosOpened": False,
        "liveExecutionAllowed": False,
        "realExecutionAllowed": False,
    }


def read_sfv2_d0_summary(*, status_path: str | Path | None = None) -> dict[str, Any]:
    configured = (
        status_path
        or os.getenv("EBA_SFV2_D0_STATUS_PATH", "").strip()
        or DEFAULT_STATUS_PATH
    )
    path = Path(configured)
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return _unavailable("status_unavailable")
    except (OSError, json.JSONDecodeError):
        return _unavailable("status_invalid")
    if not isinstance(payload, dict) or payload.get("schema") != STATUS_SCHEMA:
        return _unavailable("status_schema_rejected")

    safety_ok = (
        payload.get("authority") == "DISCOVERY_ONLY"
        and payload.get("freshConfirmationEvidence") is False
        and payload.get("verificationAuthority") is False
        and payload.get("d1Opened") is False
        and payload.get("frozenOosOpened") is False
        and payload.get("demoPromotionAllowed") is False
        and payload.get("liveExecutionAllowed") is False
        and payload.get("realExecutionAllowed") is False
    )
    if not safety_ok:
        return _unavailable("status_safety_rejected")

    phase = payload.get("phase")
    if phase not in {"IN_PROGRESS", "COMPLETE", "FAILED"}:
        return _unavailable("status_phase_rejected")

    top_raw = payload.get("topDiscoveryCandidates")
    top_candidates: list[dict[str, Any]] = []
    if isinstance(top_raw, list):
        for item in top_raw[:_MAX_TOP_CANDIDATES]:
            safe = _safe_candidate(item)
            if safe is not None:
                top_candidates.append(safe)

    survivor_ids_raw = payload.get("survivorCandidateIds")
    survivor_ids = (
        [
            item
            for item in survivor_ids_raw
            if isinstance(item, str) and item and len(item) <= 128
        ][:30]
        if isinstance(survivor_ids_raw, list)
        else []
    )
    return {
        "available": True,
        "phase": phase,
        "requestId": payload.get("requestId"),
        "campaignId": payload.get("campaignId"),
        "authority": "DISCOVERY_ONLY",
        "sourceCodeSha": payload.get("sourceCodeSha"),
        "candidateCount": _safe_number(payload.get("candidateCount")),
        "stratumCount": _safe_number(payload.get("stratumCount")),
        "expectedTrialCount": _safe_number(payload.get("expectedTrialCount")),
        "terminalTrialCount": _safe_number(payload.get("terminalTrialCount")),
        "progressFraction": _safe_number(payload.get("progressFraction")),
        "completeCandidateCount": _safe_number(payload.get("completeCandidateCount")),
        "rejectedCandidateCount": _safe_number(payload.get("rejectedCandidateCount")),
        "behaviorallyEligibleCandidateCount": _safe_number(
            payload.get("behaviorallyEligibleCandidateCount")
        ),
        "behavioralClusterCount": _safe_number(payload.get("behavioralClusterCount")),
        "selectionFrozen": payload.get("selectionFrozen") is True,
        "selectionId": payload.get("selectionId"),
        "survivorCount": _safe_number(payload.get("survivorCount")),
        "survivorCandidateIds": survivor_ids,
        "topDiscoveryCandidates": top_candidates,
        "postmortem": read_sfv2_d0_postmortem(),
        "updatedAt": payload.get("updatedAt"),
        "freshConfirmationEvidence": False,
        "verificationAuthority": False,
        "d1Opened": False,
        "frozenOosOpened": False,
        "liveExecutionAllowed": False,
        "realExecutionAllowed": False,
    }
