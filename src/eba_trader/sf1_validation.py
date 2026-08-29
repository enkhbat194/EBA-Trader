from __future__ import annotations

import json
import math
import statistics
import tempfile
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from .research_evidence import canonical_json, sha256_text
from .sf1_strategy_factory import REPORT_SCHEMA as DEVELOPMENT_REPORT_SCHEMA

REPORT_SCHEMA = "sf1_validation_report_v1"
POLICY_ID = "sf1_validation_policy_v1"
MIN_TRADES = 30
MIN_BEAT_BASELINE_WINDOWS = 9
ALPHA = 0.05
MAX_EXACT_WINDOWS = 20


def _numeric(mapping: Mapping[str, Any], key: str) -> float:
    value = mapping.get(key)
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise RuntimeError(f"missing numeric SF1 validation metric: {key}")
    number = float(value)
    if not math.isfinite(number):
        raise RuntimeError(f"non-finite SF1 validation metric: {key}")
    return number


def _validate_safety(report: Mapping[str, Any]) -> None:
    checks = {
        "rankingIsDevelopmentOnly": report.get("rankingIsDevelopmentOnly") is True,
        "developmentEvidenceOnly": report.get("developmentEvidenceOnly") is True,
        "edgeClaimAllowed": report.get("edgeClaimAllowed") is False,
        "promotionAuthority": report.get("promotionAuthority") is False,
        "frozenOosOpened": report.get("frozenOosOpened") is False,
        "m5FrozenOosOpened": report.get("m5FrozenOosOpened") is False,
        "liveExecutionAllowed": report.get("liveExecutionAllowed") is False,
    }
    failed = [name for name, passed in checks.items() if not passed]
    if failed:
        raise RuntimeError(f"unsafe SF1 development evidence: {', '.join(failed)}")


def _window_returns(rows: object, *, label: str) -> dict[str, float]:
    if not isinstance(rows, list) or not rows:
        raise RuntimeError(f"{label} windows are missing")
    result: dict[str, float] = {}
    for row in rows:
        if not isinstance(row, Mapping):
            raise RuntimeError(f"{label} window row is invalid")
        name = row.get("windowName")
        metrics = row.get("metrics")
        if not isinstance(name, str) or not name or name in result:
            raise RuntimeError(f"{label} window name is invalid or duplicated")
        if not isinstance(metrics, Mapping):
            raise RuntimeError(f"{label} metrics are missing")
        result[name] = _numeric(metrics, "total_return")
    return result


def _exact_sign_flip_p_value(deltas: tuple[float, ...]) -> tuple[float, int, int]:
    if not deltas:
        raise RuntimeError("SF1 significance requires window deltas")
    if len(deltas) > MAX_EXACT_WINDOWS:
        raise RuntimeError("SF1 exact significance window count exceeds the supported maximum")
    observed = statistics.fmean(deltas)
    permutation_count = 1 << len(deltas)
    extreme_count = 0
    tolerance = max(1e-15, abs(observed) * 1e-12)
    for mask in range(permutation_count):
        signed_sum = 0.0
        for index, delta in enumerate(deltas):
            signed_sum += delta if mask & (1 << index) else -delta
        if signed_sum / len(deltas) >= observed - tolerance:
            extreme_count += 1
    return extreme_count / permutation_count, extreme_count, permutation_count


def validate_sf1_development(report: Mapping[str, Any]) -> dict[str, Any]:
    if report.get("schema") != DEVELOPMENT_REPORT_SCHEMA:
        raise RuntimeError("unsupported SF1 development report schema")
    _validate_safety(report)
    candidate_count = report.get("candidateCount")
    budget = report.get("multipleTestingBudget")
    window_count = report.get("windowCount")
    if (
        isinstance(candidate_count, bool)
        or not isinstance(candidate_count, int)
        or candidate_count < 1
    ):
        raise RuntimeError("SF1 candidateCount is invalid")
    if isinstance(budget, bool) or not isinstance(budget, int) or budget < candidate_count:
        raise RuntimeError("SF1 multiple-testing budget is invalid")
    if isinstance(window_count, bool) or not isinstance(window_count, int) or window_count < 2:
        raise RuntimeError("SF1 windowCount is invalid")

    baseline = report.get("baseline")
    if not isinstance(baseline, Mapping):
        raise RuntimeError("SF1 baseline is missing")
    baseline_returns = _window_returns(baseline.get("windows"), label="baseline")
    if len(baseline_returns) != window_count:
        raise RuntimeError("SF1 baseline window count mismatch")

    candidates = report.get("candidates")
    if not isinstance(candidates, list) or len(candidates) != candidate_count:
        raise RuntimeError("SF1 candidate payload count mismatch")

    rows: list[dict[str, Any]] = []
    verified: list[dict[str, Any]] = []
    seen: set[str] = set()
    for candidate in candidates:
        if not isinstance(candidate, Mapping):
            raise RuntimeError("SF1 candidate row is invalid")
        candidate_id = candidate.get("candidateId")
        aggregate = candidate.get("aggregate")
        if not isinstance(candidate_id, str) or not candidate_id or candidate_id in seen:
            raise RuntimeError("SF1 candidateId is invalid or duplicated")
        if not isinstance(aggregate, Mapping):
            raise RuntimeError("SF1 candidate aggregate is missing")
        seen.add(candidate_id)

        mean_return = _numeric(aggregate, "meanReturn")
        mean_expectancy = _numeric(aggregate, "meanExpectancy")
        total_trades = _numeric(aggregate, "totalTradeCount")
        beat_windows = _numeric(aggregate, "beatBaselineWindowCount")
        profitable = mean_return > 0.0 and mean_expectancy > 0.0
        sample_sufficient = total_trades >= MIN_TRADES
        coverage_sufficient = beat_windows >= MIN_BEAT_BASELINE_WINDOWS
        qualified = profitable and sample_sufficient and coverage_sufficient

        candidate_returns = _window_returns(candidate.get("windows"), label=candidate_id)
        if set(candidate_returns) != set(baseline_returns):
            raise RuntimeError(f"SF1 candidate window set mismatch: {candidate_id}")
        deltas = tuple(
            candidate_returns[name] - baseline_returns[name]
            for name in baseline_returns
        )
        observed_mean = statistics.fmean(deltas)
        raw_p, extreme_count, permutation_count = _exact_sign_flip_p_value(deltas)
        adjusted_p = min(1.0, raw_p * budget)
        significant = qualified and observed_mean > 0.0 and adjusted_p <= ALPHA

        failed_checks: list[str] = []
        if not profitable:
            failed_checks.append("profitable")
        if not sample_sufficient:
            failed_checks.append("sampleSufficient")
        if not coverage_sufficient:
            failed_checks.append("baselineCoverageSufficient")
        if qualified and not significant:
            failed_checks.append("statisticalSignificance")

        row = {
            "candidateId": candidate_id,
            "family": candidate.get("family"),
            "parameters": dict(candidate.get("parameters") or {}),
            "qualified": qualified,
            "verifiedForRobustness": significant,
            "failedChecks": failed_checks,
            "checks": {
                "profitable": profitable,
                "sampleSufficient": sample_sufficient,
                "baselineCoverageSufficient": coverage_sufficient,
                "minimumTrades": MIN_TRADES,
                "minimumBeatBaselineWindows": MIN_BEAT_BASELINE_WINDOWS,
            },
            "windowCount": len(deltas),
            "positiveDeltaWindowCount": sum(value > 0.0 for value in deltas),
            "observedMeanReturnDeltaVsBaseline": observed_mean,
            "rawPValue": raw_p,
            "adjustedPValue": adjusted_p,
            "multipleTestingBudget": budget,
            "extremePermutationCount": extreme_count,
            "permutationCount": permutation_count,
        }
        rows.append(row)
        if significant:
            verified.append(row)

    state = "VERIFIED_CANDIDATE_AVAILABLE" if verified else "NO_VERIFIED_CANDIDATE"
    identity = {
        "schema": REPORT_SCHEMA,
        "developmentEvaluationId": report.get("evaluationId"),
        "candidateSetSha256": report.get("candidateSetSha256"),
        "policyId": POLICY_ID,
        "multipleTestingBudget": budget,
    }
    validation_id = f"sf1val_{sha256_text(canonical_json(identity))[:24]}"
    top = verified[0] if verified else None
    return {
        "schema": REPORT_SCHEMA,
        "validationId": validation_id,
        "developmentEvaluationId": report.get("evaluationId"),
        "phaseId": report.get("phaseId"),
        "materializationId": report.get("materializationId"),
        "candidateSetSha256": report.get("candidateSetSha256"),
        "candidateCount": candidate_count,
        "multipleTestingBudget": budget,
        "windowCount": window_count,
        "policy": {
            "policyId": POLICY_ID,
            "minimumTrades": MIN_TRADES,
            "minimumBeatBaselineWindows": MIN_BEAT_BASELINE_WINDOWS,
            "alpha": ALPHA,
            "nullModel": "exact_window_sign_flip",
            "multipleTestingCorrection": "preregistered_search_budget_bonferroni",
        },
        "candidateValidation": rows,
        "verifiedCandidateCount": len(verified),
        "topVerifiedCandidate": top["candidateId"] if top else None,
        "validationState": state,
        "developmentEvidenceOnly": True,
        "edgeClaimAllowed": False,
        "promotionAuthority": False,
        "frozenOosOpened": False,
        "m5FrozenOosOpened": False,
        "liveExecutionAllowed": False,
    }


def write_immutable_sf1_validation(path: str | Path, report: Mapping[str, Any]) -> Path:
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    serialized = json.dumps(dict(report), sort_keys=True, indent=2) + "\n"
    if output.exists():
        if output.read_text(encoding="utf-8") != serialized:
            raise RuntimeError("refusing to overwrite immutable SF1 validation report")
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
