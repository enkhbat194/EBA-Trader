from __future__ import annotations

import json
import math
import tempfile
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from .m5_multiwindow import REPORT_SCHEMA as MULTIWINDOW_REPORT_SCHEMA
from .research_evidence import canonical_json, sha256_text

REPORT_SCHEMA = "m5_robustness_qualification_report_v1"
MIN_ROBUSTNESS_TRADES = 30
MIN_BEAT_BASELINE_WINDOWS = 9


def _numeric(mapping: Mapping[str, Any], key: str) -> float:
    value = mapping.get(key)
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise RuntimeError(f"missing numeric qualification metric: {key}")
    number = float(value)
    if not math.isfinite(number):
        raise RuntimeError(f"non-finite qualification metric: {key}")
    return number


def qualification_policy() -> dict[str, int | str]:
    return {
        "policyId": "m5_robustness_qualification_v1",
        "minimumTrades": MIN_ROBUSTNESS_TRADES,
        "minimumBeatBaselineWindows": MIN_BEAT_BASELINE_WINDOWS,
    }


def qualify_aggregate(aggregate: Mapping[str, Any]) -> dict[str, Any]:
    mean_return = _numeric(aggregate, "meanReturn")
    mean_expectancy = _numeric(aggregate, "meanExpectancy")
    total_trades = _numeric(aggregate, "totalTradeCount")
    beat_baseline_windows = _numeric(aggregate, "beatBaselineWindowCount")

    profitable = mean_return > 0.0 and mean_expectancy > 0.0
    sample_sufficient = total_trades >= MIN_ROBUSTNESS_TRADES
    baseline_coverage_sufficient = beat_baseline_windows >= MIN_BEAT_BASELINE_WINDOWS
    eligible = profitable and sample_sufficient and baseline_coverage_sufficient

    failed_checks: list[str] = []
    if not profitable:
        failed_checks.append("profitable")
    if not sample_sufficient:
        failed_checks.append("sampleSufficient")
    if not baseline_coverage_sufficient:
        failed_checks.append("baselineCoverageSufficient")

    return {
        "eligibleForRobustness": eligible,
        "checks": {
            "profitable": profitable,
            "sampleSufficient": sample_sufficient,
            "baselineCoverageSufficient": baseline_coverage_sufficient,
            "minimumTrades": MIN_ROBUSTNESS_TRADES,
            "minimumBeatBaselineWindows": MIN_BEAT_BASELINE_WINDOWS,
        },
        "failedChecks": failed_checks,
    }


def evaluate_candidate_qualification(multiwindow_report: Mapping[str, Any]) -> dict[str, Any]:
    if multiwindow_report.get("schema") != MULTIWINDOW_REPORT_SCHEMA:
        raise RuntimeError("unsupported M5 multi-window report schema for qualification")
    if multiwindow_report.get("rankingIsDevelopmentOnly") is not True:
        raise RuntimeError("M5 qualification requires development-only ranking")
    if multiwindow_report.get("edgeClaimAllowed") is not False:
        raise RuntimeError("M5 qualification cannot consume edge-authoritative evidence")
    if multiwindow_report.get("promotionAuthority") is not False:
        raise RuntimeError("M5 qualification cannot consume promotion-authoritative evidence")
    if multiwindow_report.get("frozenOosOpened") is not False:
        raise RuntimeError("legacy Frozen OOS must remain closed during qualification")
    if multiwindow_report.get("m5FrozenOosOpened") is not False:
        raise RuntimeError("M5 Frozen OOS must remain closed during qualification")
    if multiwindow_report.get("liveExecutionAllowed") is not False:
        raise RuntimeError("M5 qualification cannot enable live execution")

    ranking = multiwindow_report.get("developmentRanking")
    candidate_count = multiwindow_report.get("candidateCount")
    if not isinstance(ranking, list) or not ranking:
        raise RuntimeError("M5 multi-window report has no development ranking")
    if isinstance(candidate_count, bool) or not isinstance(candidate_count, int):
        raise RuntimeError("M5 multi-window report candidateCount is invalid")
    if len(ranking) != candidate_count:
        raise RuntimeError("M5 multi-window ranking candidate count mismatch")

    qualifications: list[dict[str, Any]] = []
    eligible: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    for item in ranking:
        if not isinstance(item, dict):
            raise RuntimeError("M5 multi-window ranking row is invalid")
        rank = item.get("developmentPriorityRank")
        candidate_id = item.get("candidateId")
        parameters = item.get("parameters")
        aggregate = item.get("aggregate")
        if isinstance(rank, bool) or not isinstance(rank, int) or rank < 1:
            raise RuntimeError("M5 multi-window development rank is invalid")
        if not isinstance(candidate_id, str) or not candidate_id.strip():
            raise RuntimeError("M5 multi-window candidateId is invalid")
        if candidate_id in seen_ids:
            raise RuntimeError("M5 multi-window ranking contains duplicate candidateId")
        if not isinstance(parameters, dict) or not isinstance(aggregate, dict):
            raise RuntimeError("M5 multi-window candidate payload is invalid")
        seen_ids.add(candidate_id)
        qualification = qualify_aggregate(aggregate)
        row = {
            "developmentPriorityRank": rank,
            "candidateId": candidate_id,
            "parameters": dict(parameters),
            "aggregate": dict(aggregate),
            "qualification": qualification,
        }
        qualifications.append(row)
        if qualification["eligibleForRobustness"] is True:
            eligible.append(row)

    policy = qualification_policy()
    identity = {
        "schema": REPORT_SCHEMA,
        "evaluationId": multiwindow_report.get("evaluationId"),
        "materializationId": multiwindow_report.get("materializationId"),
        "candidateSetSha256": multiwindow_report.get("candidateSetSha256"),
        "policy": policy,
    }
    qualification_id = f"m5qual_{sha256_text(canonical_json(identity))[:24]}"
    top_eligible = eligible[0] if eligible else None

    return {
        "schema": REPORT_SCHEMA,
        "qualificationId": qualification_id,
        "evaluationId": multiwindow_report.get("evaluationId"),
        "materializationId": multiwindow_report.get("materializationId"),
        "candidateSetSha256": multiwindow_report.get("candidateSetSha256"),
        "candidateCount": candidate_count,
        "policy": policy,
        "candidateQualifications": qualifications,
        "eligibleCandidateCount": len(eligible),
        "eligibleCandidates": [
            {
                "developmentPriorityRank": row["developmentPriorityRank"],
                "candidateId": row["candidateId"],
                "parameters": row["parameters"],
                "aggregate": row["aggregate"],
                "qualification": row["qualification"],
            }
            for row in eligible
        ],
        "topEligibleCandidate": top_eligible["candidateId"] if top_eligible else None,
        "topEligibleParameters": top_eligible["parameters"] if top_eligible else None,
        "qualificationState": (
            "ELIGIBLE_CANDIDATE_AVAILABLE" if eligible else "NO_ELIGIBLE_CANDIDATE"
        ),
        "developmentEvidenceOnly": True,
        "edgeClaimAllowed": False,
        "promotionAuthority": False,
        "frozenOosOpened": False,
        "m5FrozenOosOpened": False,
        "liveExecutionAllowed": False,
    }


def write_immutable_qualification_report(
    path: str | Path,
    report: Mapping[str, Any],
) -> Path:
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    serialized = json.dumps(dict(report), sort_keys=True, indent=2) + "\n"
    if output.exists():
        existing = output.read_text(encoding="utf-8")
        if existing != serialized:
            raise RuntimeError("refusing to overwrite immutable qualification report")
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
