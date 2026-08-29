from __future__ import annotations

import json
import math
import tempfile
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from .m5_candidate_qualification import MIN_ROBUSTNESS_TRADES
from .m5_multiwindow import REPORT_SCHEMA as MULTIWINDOW_REPORT_SCHEMA
from .research_evidence import canonical_json, sha256_text

REPORT_SCHEMA = "m5_candidate_activity_diagnostic_report_v1"


def _numeric(mapping: Mapping[str, Any], key: str) -> float:
    value = mapping.get(key)
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise RuntimeError(f"missing numeric candidate activity metric: {key}")
    number = float(value)
    if not math.isfinite(number):
        raise RuntimeError(f"non-finite candidate activity metric: {key}")
    return number


def _count(mapping: Mapping[str, Any], key: str) -> int:
    number = _numeric(mapping, key)
    if number < 0 or not number.is_integer():
        raise RuntimeError(f"candidate activity count must be a non-negative integer: {key}")
    return int(number)


def _validate_development_report(report: Mapping[str, Any]) -> None:
    if report.get("schema") != MULTIWINDOW_REPORT_SCHEMA:
        raise RuntimeError("unsupported M5 multi-window report schema for activity diagnostics")
    checks = {
        "rankingIsDevelopmentOnly": report.get("rankingIsDevelopmentOnly") is True,
        "edgeClaimAllowed": report.get("edgeClaimAllowed") is False,
        "promotionAuthority": report.get("promotionAuthority") is False,
        "frozenOosOpened": report.get("frozenOosOpened") is False,
        "m5FrozenOosOpened": report.get("m5FrozenOosOpened") is False,
        "liveExecutionAllowed": report.get("liveExecutionAllowed") is False,
    }
    failed = [name for name, passed in checks.items() if not passed]
    if failed:
        raise RuntimeError(
            "M5 activity diagnostics require locked development-only evidence: "
            + ", ".join(failed)
        )


def _windows(value: object, *, label: str) -> tuple[Mapping[str, Any], ...]:
    if not isinstance(value, list) or not value:
        raise RuntimeError(f"{label} windows are missing")
    rows: list[Mapping[str, Any]] = []
    seen: set[str] = set()
    for item in value:
        if not isinstance(item, Mapping):
            raise RuntimeError(f"{label} window row is invalid")
        name = item.get("windowName")
        metrics = item.get("metrics")
        if not isinstance(name, str) or not name.strip() or name in seen:
            raise RuntimeError(f"{label} windowName is invalid or duplicated")
        if not isinstance(metrics, Mapping):
            raise RuntimeError(f"{label} metrics are missing for {name}")
        seen.add(name)
        rows.append(item)
    return tuple(rows)


def diagnose_candidate_activity(
    multiwindow_report: Mapping[str, Any],
    *,
    candidate_id: str,
) -> dict[str, Any]:
    _validate_development_report(multiwindow_report)
    candidate_id = candidate_id.strip()
    if not candidate_id:
        raise ValueError("candidate_id is required")

    baseline = multiwindow_report.get("baseline")
    if not isinstance(baseline, Mapping):
        raise RuntimeError("M5 multi-window baseline is missing")
    baseline_windows = _windows(baseline.get("windows"), label="baseline")
    baseline_aggregate = baseline.get("aggregate")
    if not isinstance(baseline_aggregate, Mapping):
        raise RuntimeError("M5 multi-window baseline aggregate is missing")

    candidates = multiwindow_report.get("candidates")
    if not isinstance(candidates, list):
        raise RuntimeError("M5 multi-window candidates are missing")
    selected: Mapping[str, Any] | None = None
    for item in candidates:
        if isinstance(item, Mapping) and item.get("candidateId") == candidate_id:
            if selected is not None:
                raise RuntimeError(f"duplicate candidate in multi-window report: {candidate_id}")
            selected = item
    if selected is None:
        raise RuntimeError(f"candidate is missing from multi-window report: {candidate_id}")

    candidate_windows = _windows(selected.get("windows"), label="candidate")
    candidate_aggregate = selected.get("aggregate")
    if not isinstance(candidate_aggregate, Mapping):
        raise RuntimeError("candidate aggregate is missing")
    parameters = selected.get("parameters")
    if not isinstance(parameters, Mapping) or not parameters:
        raise RuntimeError("candidate parameters are missing")

    candidate_by_name = {str(item["windowName"]): item for item in candidate_windows}
    baseline_names = [str(item["windowName"]) for item in baseline_windows]
    if set(candidate_by_name) != set(baseline_names):
        raise RuntimeError("candidate and baseline window sets do not match")

    window_rows: list[dict[str, Any]] = []
    active_trade_windows: list[str] = []
    baseline_trade_total = 0
    candidate_trade_total = 0
    for baseline_item in baseline_windows:
        name = str(baseline_item["windowName"])
        candidate_item = candidate_by_name[name]
        baseline_metrics = baseline_item["metrics"]
        candidate_metrics = candidate_item["metrics"]
        assert isinstance(baseline_metrics, Mapping)
        assert isinstance(candidate_metrics, Mapping)

        baseline_trades = _count(baseline_metrics, "trade_count")
        candidate_trades = _count(candidate_metrics, "trade_count")
        baseline_return = _numeric(baseline_metrics, "total_return")
        candidate_return = _numeric(candidate_metrics, "total_return")
        candidate_expectancy = _numeric(candidate_metrics, "expectancy")
        candidate_exposure = _numeric(candidate_metrics, "exposure")
        baseline_trade_total += baseline_trades
        candidate_trade_total += candidate_trades
        if candidate_trades > 0:
            active_trade_windows.append(name)

        window_rows.append(
            {
                "windowName": name,
                "startMs": baseline_item.get("startMs"),
                "endMs": baseline_item.get("endMs"),
                "baselineTradeCount": baseline_trades,
                "candidateTradeCount": candidate_trades,
                "tradeCountDeltaVsBaseline": candidate_trades - baseline_trades,
                "tradeRetentionRatioVsBaseline": (
                    candidate_trades / baseline_trades if baseline_trades > 0 else None
                ),
                "baselineReturn": baseline_return,
                "candidateReturn": candidate_return,
                "returnDeltaVsBaseline": candidate_return - baseline_return,
                "candidateExpectancy": candidate_expectancy,
                "candidateExposure": candidate_exposure,
                "active": candidate_trades > 0,
            }
        )

    expected_baseline_trades = _count(baseline_aggregate, "totalTradeCount")
    expected_candidate_trades = _count(candidate_aggregate, "totalTradeCount")
    if baseline_trade_total != expected_baseline_trades:
        raise RuntimeError("baseline per-window trade total does not match aggregate")
    if candidate_trade_total != expected_candidate_trades:
        raise RuntimeError("candidate per-window trade total does not match aggregate")

    window_count = len(window_rows)
    active_count = len(active_trade_windows)
    zero_trade_count = window_count - active_count
    sample_sufficient = candidate_trade_total >= MIN_ROBUSTNESS_TRADES
    diagnostic_state = (
        "ENTRY_FILTER_WITH_SUFFICIENT_SAMPLE"
        if sample_sufficient
        else "SPARSE_ENTRY_FILTER"
    )

    identity = {
        "schema": REPORT_SCHEMA,
        "evaluationId": multiwindow_report.get("evaluationId"),
        "candidateId": candidate_id,
        "candidateParameters": dict(parameters),
    }
    diagnostic_id = f"m5act_{sha256_text(canonical_json(identity))[:24]}"
    return {
        "schema": REPORT_SCHEMA,
        "diagnosticId": diagnostic_id,
        "evaluationId": multiwindow_report.get("evaluationId"),
        "materializationId": multiwindow_report.get("materializationId"),
        "candidateId": candidate_id,
        "candidateParameters": dict(parameters),
        "windowCount": window_count,
        "windows": window_rows,
        "activeTradeWindows": active_trade_windows,
        "activeWindowCount": active_count,
        "zeroTradeWindowCount": zero_trade_count,
        "candidateActiveWindowShare": active_count / window_count,
        "baselineTradeCount": baseline_trade_total,
        "candidateTradeCount": candidate_trade_total,
        "candidateTradeRetentionVsBaseline": (
            candidate_trade_total / baseline_trade_total if baseline_trade_total > 0 else None
        ),
        "minimumRobustnessTrades": MIN_ROBUSTNESS_TRADES,
        "sampleSufficientForRobustness": sample_sufficient,
        "structuralRole": "ema_crossover_entry_filter",
        "independentSignalGenerator": False,
        "diagnosticState": diagnostic_state,
        "developmentEvidenceOnly": True,
        "edgeClaimAllowed": False,
        "promotionAuthority": False,
        "frozenOosOpened": False,
        "m5FrozenOosOpened": False,
        "liveExecutionAllowed": False,
    }


def write_immutable_activity_report(path: str | Path, report: Mapping[str, Any]) -> Path:
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    serialized = json.dumps(dict(report), sort_keys=True, indent=2) + "\n"
    if output.exists():
        if output.read_text(encoding="utf-8") != serialized:
            raise RuntimeError("refusing to overwrite immutable M5 candidate activity report")
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
