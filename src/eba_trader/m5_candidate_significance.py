from __future__ import annotations

import json
import math
import statistics
import tempfile
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from .m5_candidate_qualification import REPORT_SCHEMA as QUALIFICATION_REPORT_SCHEMA
from .m5_multiwindow import REPORT_SCHEMA as MULTIWINDOW_REPORT_SCHEMA
from .research_evidence import canonical_json, sha256_text

REPORT_SCHEMA = "m5_candidate_significance_report_v1"
POLICY_ID = "m5_window_significance_v1"
ALPHA = 0.05
MAX_EXACT_WINDOWS = 20
CORRECTION_METHOD = "bonferroni_candidate_set"
NULL_MODEL = "exact_window_sign_flip"


def significance_policy() -> dict[str, Any]:
    return {
        "policyId": POLICY_ID,
        "alpha": ALPHA,
        "nullModel": NULL_MODEL,
        "multipleTestingCorrection": CORRECTION_METHOD,
        "maxExactWindows": MAX_EXACT_WINDOWS,
    }


def _numeric(mapping: Mapping[str, Any], key: str) -> float:
    value = mapping.get(key)
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise RuntimeError(f"missing numeric significance metric: {key}")
    number = float(value)
    if not math.isfinite(number):
        raise RuntimeError(f"non-finite significance metric: {key}")
    return number


def _validate_safety(payload: Mapping[str, Any], *, label: str) -> None:
    checks = {
        "developmentEvidenceOnly": payload.get("developmentEvidenceOnly") is True,
        "edgeClaimAllowed": payload.get("edgeClaimAllowed") is False,
        "promotionAuthority": payload.get("promotionAuthority") is False,
        "frozenOosOpened": payload.get("frozenOosOpened") is False,
        "m5FrozenOosOpened": payload.get("m5FrozenOosOpened") is False,
        "liveExecutionAllowed": payload.get("liveExecutionAllowed") is False,
    }
    failed = [name for name, passed in checks.items() if not passed]
    if failed:
        raise RuntimeError(f"{label} violates development-only safety: {', '.join(failed)}")


def _validate_inputs(
    multiwindow_report: Mapping[str, Any],
    qualification_report: Mapping[str, Any],
) -> None:
    if multiwindow_report.get("schema") != MULTIWINDOW_REPORT_SCHEMA:
        raise RuntimeError("unsupported M5 multi-window report schema for significance")
    if qualification_report.get("schema") != QUALIFICATION_REPORT_SCHEMA:
        raise RuntimeError("unsupported M5 qualification report schema for significance")
    if multiwindow_report.get("rankingIsDevelopmentOnly") is not True:
        raise RuntimeError("significance requires a development-only multi-window ranking")
    _validate_safety(multiwindow_report, label="multi-window report")
    _validate_safety(qualification_report, label="qualification report")
    for key in ("evaluationId", "materializationId", "candidateSetSha256"):
        if multiwindow_report.get(key) != qualification_report.get(key):
            raise RuntimeError(f"significance input identity mismatch: {key}")


def _candidate_by_id(multiwindow_report: Mapping[str, Any]) -> dict[str, Mapping[str, Any]]:
    raw = multiwindow_report.get("candidates")
    if not isinstance(raw, list):
        raise RuntimeError("multi-window candidates are missing")
    result: dict[str, Mapping[str, Any]] = {}
    for row in raw:
        if not isinstance(row, Mapping):
            raise RuntimeError("multi-window candidate row is invalid")
        candidate_id = row.get("candidateId")
        if not isinstance(candidate_id, str) or not candidate_id:
            raise RuntimeError("multi-window candidateId is invalid")
        if candidate_id in result:
            raise RuntimeError(f"duplicate multi-window candidateId: {candidate_id}")
        result[candidate_id] = row
    return result


def _baseline_returns(multiwindow_report: Mapping[str, Any]) -> dict[str, float]:
    baseline = multiwindow_report.get("baseline")
    windows = baseline.get("windows") if isinstance(baseline, Mapping) else None
    if not isinstance(windows, list) or not windows:
        raise RuntimeError("multi-window baseline windows are missing")
    result: dict[str, float] = {}
    for row in windows:
        if not isinstance(row, Mapping):
            raise RuntimeError("baseline window row is invalid")
        name = row.get("windowName")
        metrics = row.get("metrics")
        if not isinstance(name, str) or not name or name in result:
            raise RuntimeError("baseline windowName is invalid or duplicated")
        if not isinstance(metrics, Mapping):
            raise RuntimeError(f"baseline metrics are missing for {name}")
        result[name] = _numeric(metrics, "total_return")
    return result


def _window_return_deltas(
    candidate: Mapping[str, Any],
    *,
    baseline_returns: Mapping[str, float],
) -> tuple[float, ...]:
    windows = candidate.get("windows")
    if not isinstance(windows, list) or not windows:
        raise RuntimeError("candidate windows are missing")
    by_name: dict[str, float] = {}
    for row in windows:
        if not isinstance(row, Mapping):
            raise RuntimeError("candidate window row is invalid")
        name = row.get("windowName")
        metrics = row.get("metrics")
        if not isinstance(name, str) or not name or name in by_name:
            raise RuntimeError("candidate windowName is invalid or duplicated")
        if not isinstance(metrics, Mapping):
            raise RuntimeError(f"candidate metrics are missing for {name}")
        if name not in baseline_returns:
            raise RuntimeError(f"candidate window not present in baseline: {name}")
        by_name[name] = _numeric(metrics, "total_return") - baseline_returns[name]
    if set(by_name) != set(baseline_returns):
        raise RuntimeError("candidate and baseline window sets do not match")
    return tuple(by_name[name] for name in baseline_returns)


def _exact_sign_flip_p_value(deltas: tuple[float, ...]) -> tuple[float, int, int]:
    if not deltas:
        raise RuntimeError("significance test requires window deltas")
    if len(deltas) > MAX_EXACT_WINDOWS:
        raise RuntimeError(
            f"exact sign-flip test supports at most {MAX_EXACT_WINDOWS} windows"
        )
    observed = statistics.fmean(deltas)
    permutation_count = 1 << len(deltas)
    extreme_count = 0
    tolerance = max(1e-15, abs(observed) * 1e-12)
    for mask in range(permutation_count):
        signed_sum = 0.0
        for index, delta in enumerate(deltas):
            signed_sum += delta if mask & (1 << index) else -delta
        signed_mean = signed_sum / len(deltas)
        if signed_mean >= observed - tolerance:
            extreme_count += 1
    return extreme_count / permutation_count, extreme_count, permutation_count


def evaluate_candidate_significance(
    multiwindow_report: Mapping[str, Any],
    qualification_report: Mapping[str, Any],
) -> dict[str, Any]:
    _validate_inputs(multiwindow_report, qualification_report)
    candidate_count = multiwindow_report.get("candidateCount")
    if isinstance(candidate_count, bool) or not isinstance(candidate_count, int) or candidate_count < 1:
        raise RuntimeError("multi-window candidateCount is invalid")

    eligible_raw = qualification_report.get("eligibleCandidates")
    if not isinstance(eligible_raw, list):
        raise RuntimeError("qualification eligibleCandidates is invalid")
    eligible_count = qualification_report.get("eligibleCandidateCount")
    if (
        isinstance(eligible_count, bool)
        or not isinstance(eligible_count, int)
        or eligible_count < 0
        or eligible_count != len(eligible_raw)
    ):
        raise RuntimeError("qualification eligible candidate count mismatch")

    baseline_returns = _baseline_returns(multiwindow_report)
    candidates = _candidate_by_id(multiwindow_report)
    if len(candidates) != candidate_count:
        raise RuntimeError("multi-window candidate count mismatch")

    rows: list[dict[str, Any]] = []
    significant: list[dict[str, Any]] = []
    for eligible in eligible_raw:
        if not isinstance(eligible, Mapping):
            raise RuntimeError("qualification eligible candidate row is invalid")
        candidate_id = eligible.get("candidateId")
        rank = eligible.get("developmentPriorityRank")
        if not isinstance(candidate_id, str) or candidate_id not in candidates:
            raise RuntimeError("qualified candidate is missing from multi-window evidence")
        if isinstance(rank, bool) or not isinstance(rank, int) or rank < 1:
            raise RuntimeError("qualified development rank is invalid")
        deltas = _window_return_deltas(
            candidates[candidate_id], baseline_returns=baseline_returns
        )
        observed_mean = statistics.fmean(deltas)
        raw_p, extreme_count, permutation_count = _exact_sign_flip_p_value(deltas)
        adjusted_p = min(1.0, raw_p * candidate_count)
        verified = observed_mean > 0.0 and adjusted_p <= ALPHA
        row = {
            "developmentPriorityRank": rank,
            "candidateId": candidate_id,
            "parameters": dict(eligible.get("parameters") or {}),
            "windowCount": len(deltas),
            "returnDeltasVsBaseline": list(deltas),
            "observedMeanReturnDeltaVsBaseline": observed_mean,
            "positiveDeltaWindowCount": sum(value > 0.0 for value in deltas),
            "rawPValue": raw_p,
            "adjustedPValue": adjusted_p,
            "extremePermutationCount": extreme_count,
            "permutationCount": permutation_count,
            "candidateCountCorrection": candidate_count,
            "statisticallySignificant": verified,
        }
        rows.append(row)
        if verified:
            significant.append(row)

    if not rows:
        state = "NO_ELIGIBLE_CANDIDATE"
    elif significant:
        state = "SIGNIFICANT_CANDIDATE_AVAILABLE"
    else:
        state = "NO_SIGNIFICANT_CANDIDATE"
    top = significant[0] if significant else None
    policy = significance_policy()
    identity = {
        "schema": REPORT_SCHEMA,
        "evaluationId": multiwindow_report.get("evaluationId"),
        "qualificationId": qualification_report.get("qualificationId"),
        "candidateSetSha256": multiwindow_report.get("candidateSetSha256"),
        "policy": policy,
    }
    significance_id = f"m5sig_{sha256_text(canonical_json(identity))[:24]}"
    return {
        "schema": REPORT_SCHEMA,
        "significanceId": significance_id,
        "evaluationId": multiwindow_report.get("evaluationId"),
        "qualificationId": qualification_report.get("qualificationId"),
        "materializationId": multiwindow_report.get("materializationId"),
        "candidateSetSha256": multiwindow_report.get("candidateSetSha256"),
        "candidateCount": candidate_count,
        "eligibleCandidateCount": eligible_count,
        "testedCandidateCount": len(rows),
        "significantCandidateCount": len(significant),
        "candidateSignificance": rows,
        "topSignificantCandidate": top["candidateId"] if top else None,
        "topSignificantParameters": top["parameters"] if top else None,
        "significanceState": state,
        "policy": policy,
        "developmentEvidenceOnly": True,
        "edgeClaimAllowed": False,
        "promotionAuthority": False,
        "frozenOosOpened": False,
        "m5FrozenOosOpened": False,
        "liveExecutionAllowed": False,
    }


def write_immutable_significance_report(
    path: str | Path,
    report: Mapping[str, Any],
) -> Path:
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    serialized = json.dumps(dict(report), sort_keys=True, indent=2) + "\n"
    if output.exists():
        if output.read_text(encoding="utf-8") != serialized:
            raise RuntimeError("refusing to overwrite immutable candidate significance report")
        return output
    with tempfile.NamedTemporaryFile(
        mode="w",
        encoding="utf-8",
        dir=output.parent,
        prefix=f".{output.name}.",
        delete=False,
    ) as handle:
        handle.write(serialized)
        temporary = Path(handle.name)
    temporary.chmod(0o640)
    temporary.replace(output)
    return output
