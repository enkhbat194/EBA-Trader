from __future__ import annotations

import json
import math
import statistics
import tempfile
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from .backtest_adapter import EmaFeatureBaselineV1Adapter, _result_metrics
from .history import validate_interval_window
from .m5_corpus_materializer import _load_completed_materialization
from .m5_study_policy import DEFAULT_M5_STUDY_POLICY
from .orderflow_feature_dataset import load_orderflow_feature_csv
from .research_evidence import canonical_json, sha256_text
from .sf2_protocol import (
    ADJUSTED_ALPHA_MAX,
    FEE_BPS,
    MINIMUM_BASELINE_BEATING_WINDOWS,
    MINIMUM_TOTAL_TRADES,
    PERMUTATION_COUNT,
    PLANNED_MULTIPLE_TESTING_BUDGET,
    SLIPPAGE_BPS,
    SF2ResearchProtocol,
    load_sf2_protocol,
)
from .sf2_signal_backtest import run_sf2_candidate_backtest

DEVELOPMENT_REPORT_SCHEMA = "sf2_development_report_v1"
VALIDATION_REPORT_SCHEMA = "sf2_validation_report_v1"
BASELINE_ID = "ema_feature_baseline_v1_12_26"
BASELINE_FAST_EMA = 12
BASELINE_SLOW_EMA = 26
INITIAL_CASH = 10_000.0
PRICE_BUCKET = 1.0
ORDERFLOW_SOURCE = "archive"
SF2_NAMESPACE = "sf2_orderflow_dev"


def _json_object(path: Path, *, label: str) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"cannot read {label}") from exc
    if not isinstance(payload, dict):
        raise RuntimeError(f"{label} must be a JSON object")
    return payload


def _resolve_under(root: Path, value: str | Path, *, label: str) -> Path:
    resolved_root = root.resolve()
    candidate = Path(value)
    candidate = (
        candidate.resolve()
        if candidate.is_absolute()
        else (resolved_root / candidate).resolve()
    )
    try:
        candidate.relative_to(resolved_root)
    except ValueError as exc:
        raise ValueError(f"{label} escapes configured dataset root") from exc
    return candidate


def candidate_set_sha256(protocol: SF2ResearchProtocol) -> str:
    return sha256_text(
        canonical_json([candidate.as_dict() for candidate in protocol.candidates])
    )


def _load_sf2_materialization(
    *,
    manifest_path: Path,
    dataset_root: Path,
    protocol: SF2ResearchProtocol,
) -> tuple[Any, tuple[dict[str, Any], ...]]:
    payload = _json_object(manifest_path, label="SF2 corpus materialization")
    materialization_id = str(payload.get("materialization_id") or "")
    if not materialization_id:
        raise RuntimeError("SF2 corpus materialization is missing materialization_id")

    materialization = _load_completed_materialization(
        manifest_path,
        materialization_id=materialization_id,
        corpus=protocol.corpus,
        dataset_root=dataset_root,
        price_bucket=PRICE_BUCKET,
        namespace=SF2_NAMESPACE,
        orderflow_source=ORDERFLOW_SOURCE,
    )
    policy = DEFAULT_M5_STUDY_POLICY
    if materialization.policy_id != policy.policy_id:
        raise RuntimeError("SF2 materialization policy mismatch")
    if materialization.corpus_id != protocol.corpus.corpus_id:
        raise RuntimeError("SF2 materialization corpus mismatch")
    if materialization.symbol != policy.symbol:
        raise RuntimeError("SF2 materialization symbol mismatch")
    if materialization.venue != policy.venue:
        raise RuntimeError("SF2 materialization venue mismatch")
    if materialization.interval != policy.interval:
        raise RuntimeError("SF2 materialization interval mismatch")
    if len(materialization.windows) != len(protocol.corpus.windows):
        raise RuntimeError("SF2 materialization window count mismatch")

    receipts: list[dict[str, Any]] = []
    for receipt, expected in zip(
        materialization.windows,
        protocol.corpus.windows,
        strict=True,
    ):
        if receipt.window_name != expected.name:
            raise RuntimeError("SF2 receipt window name mismatch")
        if receipt.start_ms != expected.start_ms or receipt.end_ms != expected.end_ms:
            raise RuntimeError("SF2 receipt time range mismatch")
        path = _resolve_under(
            dataset_root,
            receipt.dataset_ref,
            label="SF2 dataset_ref",
        )
        if not path.is_file():
            raise RuntimeError(f"SF2 feature dataset is missing: {expected.name}")
        receipts.append(
            {
                "window_name": receipt.window_name,
                "start_ms": receipt.start_ms,
                "end_ms": receipt.end_ms,
                "dataset_path": path,
            }
        )
    return materialization, tuple(receipts)


def _numeric(metrics: Mapping[str, Any], key: str) -> float:
    value = metrics.get(key)
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise RuntimeError(f"missing numeric SF2 metric: {key}")
    number = float(value)
    if not math.isfinite(number):
        raise RuntimeError(f"non-finite SF2 metric: {key}")
    return number


def _aggregate(
    windows: list[dict[str, Any]],
    baseline: Mapping[str, dict[str, Any]] | None,
) -> dict[str, Any]:
    if not windows:
        raise RuntimeError("SF2 aggregate requires windows")
    returns: list[float] = []
    expectancies: list[float] = []
    drawdowns: list[float] = []
    trades: list[int] = []
    costs: list[float] = []
    deltas: list[float] = []
    for row in windows:
        metrics = row["metrics"]
        total_return = _numeric(metrics, "total_return")
        returns.append(total_return)
        expectancies.append(_numeric(metrics, "expectancy"))
        drawdowns.append(_numeric(metrics, "max_drawdown"))
        trades.append(int(_numeric(metrics, "trade_count")))
        costs.append(_numeric(metrics, "total_cost"))
        if baseline is not None:
            baseline_return = _numeric(
                baseline[row["windowName"]]["metrics"],
                "total_return",
            )
            deltas.append(total_return - baseline_return)

    result: dict[str, Any] = {
        "windowCount": len(windows),
        "meanReturn": statistics.fmean(returns),
        "medianReturn": statistics.median(returns),
        "worstWindowReturn": min(returns),
        "bestWindowReturn": max(returns),
        "positiveWindowCount": sum(value > 0.0 for value in returns),
        "meanExpectancy": statistics.fmean(expectancies),
        "worstMaxDrawdown": min(drawdowns),
        "totalTradeCount": sum(trades),
        "totalCost": sum(costs),
    }
    if deltas:
        result.update(
            {
                "beatBaselineWindowCount": sum(value > 0.0 for value in deltas),
                "notWorseThanBaselineWindowCount": sum(
                    value >= 0.0 for value in deltas
                ),
                "meanReturnDeltaVsBaseline": statistics.fmean(deltas),
                "medianReturnDeltaVsBaseline": statistics.median(deltas),
                "worstReturnDeltaVsBaseline": min(deltas),
                "bestReturnDeltaVsBaseline": max(deltas),
            }
        )
    return result


def _ranking_key(row: Mapping[str, Any]) -> tuple[float, ...]:
    aggregate = row["aggregate"]
    return (
        float(aggregate["beatBaselineWindowCount"]),
        float(aggregate["positiveWindowCount"]),
        float(aggregate["meanReturnDeltaVsBaseline"]),
        float(aggregate["meanReturn"]),
        float(aggregate["meanExpectancy"]),
        float(aggregate["totalTradeCount"]),
    )


def _safe_contract(payload: Mapping[str, Any]) -> bool:
    return (
        payload.get("developmentEvidenceOnly") is True
        and payload.get("edgeClaimAllowed") is False
        and payload.get("promotionAuthority") is False
        and payload.get("frozenOosOpened") is False
        and payload.get("m5FrozenOosOpened") is False
        and payload.get("liveExecutionAllowed") is False
    )


def evaluate_sf2_development(
    *,
    manifest_path: str | Path,
    dataset_root: str | Path,
    protocol_path: str | Path,
) -> dict[str, Any]:
    protocol = load_sf2_protocol(protocol_path)
    dataset_root_path = Path(dataset_root).resolve()
    materialization, receipts = _load_sf2_materialization(
        manifest_path=Path(manifest_path).resolve(),
        dataset_root=dataset_root_path,
        protocol=protocol,
    )
    candidate_sha = candidate_set_sha256(protocol)
    baseline_windows: list[dict[str, Any]] = []
    candidate_windows: dict[str, list[dict[str, Any]]] = {
        candidate.candidate_id: [] for candidate in protocol.candidates
    }

    for receipt in receipts:
        path = Path(receipt["dataset_path"])
        feature_rows = load_orderflow_feature_csv(path)
        candles = validate_interval_window(
            [row.candle for row in feature_rows],
            DEFAULT_M5_STUDY_POLICY.interval,
            int(receipt["start_ms"]),
            int(receipt["end_ms"]),
        )
        if len(candles) <= protocol.warmup_bars + 2:
            raise RuntimeError(
                "SF2 window is too short for preregistered warmup: "
                f"{receipt['window_name']}"
            )
        evaluation_start_ms = candles[protocol.warmup_bars].open_time_ms
        baseline_spec = {
            "adapter": "ema_feature_baseline_v1",
            "fixed": {
                "fast_ema": BASELINE_FAST_EMA,
                "slow_ema": BASELINE_SLOW_EMA,
                "initial_cash": INITIAL_CASH,
                "fee_bps": FEE_BPS,
                "slippage_bps": SLIPPAGE_BPS,
                "trade_start_time_ms": evaluation_start_ms,
            },
            "dataset": {
                "symbol": DEFAULT_M5_STUDY_POLICY.symbol,
                "interval": DEFAULT_M5_STUDY_POLICY.interval,
                "start_ms": int(receipt["start_ms"]),
                "end_ms": int(receipt["end_ms"]),
            },
        }
        baseline = EmaFeatureBaselineV1Adapter().run(
            dataset_path=path,
            strategy_spec=baseline_spec,
            experiment_parameters={},
            stage="sf2_development_baseline",
        )
        baseline_windows.append(
            {
                "windowName": str(receipt["window_name"]),
                "evaluationStartMs": evaluation_start_ms,
                "metrics": baseline.metrics,
            }
        )

        for candidate in protocol.candidates:
            result = run_sf2_candidate_backtest(
                feature_rows,
                candidate,
                trade_start_time_ms=evaluation_start_ms,
            )
            candidate_windows[candidate.candidate_id].append(
                {
                    "windowName": str(receipt["window_name"]),
                    "evaluationStartMs": evaluation_start_ms,
                    "metrics": _result_metrics(result),
                }
            )

    baseline_by_name = {row["windowName"]: row for row in baseline_windows}
    baseline_aggregate = _aggregate(baseline_windows, None)
    evaluated: list[dict[str, Any]] = []
    for candidate in protocol.candidates:
        windows = candidate_windows[candidate.candidate_id]
        evaluated.append(
            {
                "candidateId": candidate.candidate_id,
                "family": candidate.family,
                "parameters": dict(candidate.parameters),
                "aggregate": _aggregate(windows, baseline_by_name),
                "windows": windows,
            }
        )
    evaluated.sort(key=_ranking_key, reverse=True)
    ranking = [
        {
            "developmentPriorityRank": index,
            "candidateId": row["candidateId"],
            "family": row["family"],
            "parameters": dict(row["parameters"]),
            "aggregate": dict(row["aggregate"]),
        }
        for index, row in enumerate(evaluated, start=1)
    ]

    identity = {
        "schema": DEVELOPMENT_REPORT_SCHEMA,
        "phaseId": protocol.phase_id,
        "protocolId": protocol.protocol_id,
        "materializationId": materialization.materialization_id,
        "candidateSetSha256": candidate_sha,
        "baselineId": BASELINE_ID,
    }
    evaluation_id = f"sf2dev_{sha256_text(canonical_json(identity))[:24]}"
    return {
        "schema": DEVELOPMENT_REPORT_SCHEMA,
        "evaluationId": evaluation_id,
        "phaseId": protocol.phase_id,
        "protocolId": protocol.protocol_id,
        "policyId": materialization.policy_id,
        "corpusId": materialization.corpus_id,
        "materializationId": materialization.materialization_id,
        "candidateSetSha256": candidate_sha,
        "candidateCount": len(protocol.candidates),
        "multipleTestingBudget": protocol.planned_candidate_budget,
        "warmupBars": protocol.warmup_bars,
        "windowCount": len(receipts),
        "baseline": {
            "baselineId": BASELINE_ID,
            "adapter": "ema_feature_baseline_v1",
            "parameters": {
                "fastEma": BASELINE_FAST_EMA,
                "slowEma": BASELINE_SLOW_EMA,
                "initialCash": INITIAL_CASH,
                "feeBps": FEE_BPS,
                "slippageBps": SLIPPAGE_BPS,
            },
            "aggregate": baseline_aggregate,
            "windows": baseline_windows,
        },
        "candidates": evaluated,
        "developmentRanking": ranking,
        "topDevelopmentCandidate": ranking[0]["candidateId"] if ranking else None,
        "developmentEvidenceOnly": True,
        "edgeClaimAllowed": False,
        "promotionAuthority": False,
        "frozenOosOpened": False,
        "m5FrozenOosOpened": False,
        "liveExecutionAllowed": False,
    }


def _window_returns(rows: Any, *, label: str) -> dict[str, float]:
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
    if len(deltas) != 12:
        raise RuntimeError("SF2 significance requires exactly 12 preregistered windows")
    permutation_count = 1 << len(deltas)
    if permutation_count != PERMUTATION_COUNT:
        raise RuntimeError("SF2 permutation count does not match preregistration")
    observed = statistics.fmean(deltas)
    tolerance = max(1e-15, abs(observed) * 1e-12)
    extreme_count = 0
    for mask in range(permutation_count):
        signed_sum = 0.0
        for index, delta in enumerate(deltas):
            signed_sum += delta if mask & (1 << index) else -delta
        if signed_sum / len(deltas) >= observed - tolerance:
            extreme_count += 1
    return extreme_count / permutation_count, extreme_count, permutation_count


def _expected_baseline_parameters() -> dict[str, float | int]:
    return {
        "fastEma": BASELINE_FAST_EMA,
        "slowEma": BASELINE_SLOW_EMA,
        "initialCash": INITIAL_CASH,
        "feeBps": FEE_BPS,
        "slippageBps": SLIPPAGE_BPS,
    }


def validate_sf2_development(
    report: Mapping[str, Any],
    *,
    protocol_path: str | Path,
) -> dict[str, Any]:
    protocol = load_sf2_protocol(protocol_path)
    if report.get("schema") != DEVELOPMENT_REPORT_SCHEMA:
        raise RuntimeError("unsupported SF2 development report schema")
    if not _safe_contract(report):
        raise RuntimeError("unsafe SF2 development report")
    if (
        report.get("phaseId") != protocol.phase_id
        or report.get("protocolId") != protocol.protocol_id
    ):
        raise RuntimeError("SF2 development report protocol identity mismatch")
    if report.get("candidateSetSha256") != candidate_set_sha256(protocol):
        raise RuntimeError("SF2 development candidate set identity mismatch")
    if report.get("candidateCount") != len(protocol.candidates):
        raise RuntimeError("SF2 development candidate count mismatch")
    if report.get("multipleTestingBudget") != PLANNED_MULTIPLE_TESTING_BUDGET:
        raise RuntimeError("SF2 multiple-testing budget mismatch")
    if report.get("windowCount") != 12:
        raise RuntimeError("SF2 development window count mismatch")

    baseline = report.get("baseline")
    if not isinstance(baseline, Mapping) or baseline.get("baselineId") != BASELINE_ID:
        raise RuntimeError("SF2 baseline identity mismatch")
    if baseline.get("adapter") != "ema_feature_baseline_v1":
        raise RuntimeError("SF2 baseline adapter mismatch")
    if baseline.get("parameters") != _expected_baseline_parameters():
        raise RuntimeError("SF2 baseline parameter mismatch")
    baseline_returns = _window_returns(baseline.get("windows"), label="SF2 baseline")
    candidates = report.get("candidates")
    if not isinstance(candidates, list) or len(candidates) != len(protocol.candidates):
        raise RuntimeError("SF2 candidate payload count mismatch")
    protocol_candidates = {
        candidate.candidate_id: candidate for candidate in protocol.candidates
    }

    rows: list[dict[str, Any]] = []
    verified: list[dict[str, Any]] = []
    seen: set[str] = set()
    for candidate in candidates:
        if not isinstance(candidate, Mapping):
            raise RuntimeError("SF2 candidate row is invalid")
        candidate_id = candidate.get("candidateId")
        aggregate = candidate.get("aggregate")
        if not isinstance(candidate_id, str) or not candidate_id or candidate_id in seen:
            raise RuntimeError("SF2 candidateId is invalid or duplicated")
        expected = protocol_candidates.get(candidate_id)
        if expected is None:
            raise RuntimeError(f"SF2 candidate is not preregistered: {candidate_id}")
        if candidate.get("family") != expected.family:
            raise RuntimeError(f"SF2 candidate family mismatch: {candidate_id}")
        raw_parameters = candidate.get("parameters")
        if not isinstance(raw_parameters, Mapping):
            raise RuntimeError(f"SF2 candidate parameters are missing: {candidate_id}")
        if dict(raw_parameters) != dict(expected.parameters):
            raise RuntimeError(f"SF2 candidate parameter mismatch: {candidate_id}")
        if not isinstance(aggregate, Mapping):
            raise RuntimeError("SF2 candidate aggregate is missing")
        seen.add(candidate_id)

        mean_return = _numeric(aggregate, "meanReturn")
        mean_expectancy = _numeric(aggregate, "meanExpectancy")
        total_trades = _numeric(aggregate, "totalTradeCount")
        beat_windows = _numeric(aggregate, "beatBaselineWindowCount")
        profitable = mean_return > 0.0 and mean_expectancy > 0.0
        sample_sufficient = total_trades >= MINIMUM_TOTAL_TRADES
        coverage_sufficient = beat_windows >= MINIMUM_BASELINE_BEATING_WINDOWS

        candidate_returns = _window_returns(candidate.get("windows"), label=candidate_id)
        if set(candidate_returns) != set(baseline_returns):
            raise RuntimeError(f"SF2 candidate window set mismatch: {candidate_id}")
        deltas = tuple(
            candidate_returns[name] - baseline_returns[name]
            for name in baseline_returns
        )
        observed_mean = statistics.fmean(deltas)
        raw_p, extreme_count, permutation_count = _exact_sign_flip_p_value(deltas)
        adjusted_p = min(1.0, raw_p * PLANNED_MULTIPLE_TESTING_BUDGET)
        positive_delta = observed_mean > 0.0
        significant = (
            profitable
            and sample_sufficient
            and coverage_sufficient
            and positive_delta
            and adjusted_p <= ADJUSTED_ALPHA_MAX
        )

        failed: list[str] = []
        if not profitable:
            failed.append("profitable")
        if not sample_sufficient:
            failed.append("sampleSufficient")
        if not coverage_sufficient:
            failed.append("baselineCoverageSufficient")
        if not positive_delta:
            failed.append("positiveMeanDeltaVsBaseline")
        if (
            profitable
            and sample_sufficient
            and coverage_sufficient
            and positive_delta
            and adjusted_p > ADJUSTED_ALPHA_MAX
        ):
            failed.append("statisticalSignificance")

        row = {
            "candidateId": candidate_id,
            "family": expected.family,
            "parameters": dict(expected.parameters),
            "qualified": profitable and sample_sufficient and coverage_sufficient,
            "verifiedForRobustness": significant,
            "failedChecks": failed,
            "checks": {
                "profitable": profitable,
                "sampleSufficient": sample_sufficient,
                "baselineCoverageSufficient": coverage_sufficient,
                "positiveMeanDeltaVsBaseline": positive_delta,
                "minimumTrades": MINIMUM_TOTAL_TRADES,
                "minimumBeatBaselineWindows": MINIMUM_BASELINE_BEATING_WINDOWS,
            },
            "windowCount": len(deltas),
            "positiveDeltaWindowCount": sum(value > 0.0 for value in deltas),
            "observedMeanReturnDeltaVsBaseline": observed_mean,
            "rawPValue": raw_p,
            "adjustedPValue": adjusted_p,
            "multipleTestingBudget": PLANNED_MULTIPLE_TESTING_BUDGET,
            "extremePermutationCount": extreme_count,
            "permutationCount": permutation_count,
        }
        rows.append(row)
        if significant:
            verified.append(row)

    if seen != set(protocol_candidates):
        raise RuntimeError("SF2 development candidate set is incomplete")

    state = "VERIFIED_CANDIDATE_AVAILABLE" if verified else "NO_VERIFIED_CANDIDATE"
    ranking = report.get("developmentRanking")
    rank_order = (
        {
            row.get("candidateId"): index
            for index, row in enumerate(ranking)
            if isinstance(row, Mapping)
        }
        if isinstance(ranking, list)
        else {}
    )
    verified.sort(key=lambda item: rank_order.get(item["candidateId"], 10**9))
    top = verified[0] if verified else None
    identity = {
        "schema": VALIDATION_REPORT_SCHEMA,
        "developmentEvaluationId": report.get("evaluationId"),
        "protocolId": protocol.protocol_id,
        "candidateSetSha256": report.get("candidateSetSha256"),
        "multipleTestingBudget": PLANNED_MULTIPLE_TESTING_BUDGET,
    }
    validation_id = f"sf2val_{sha256_text(canonical_json(identity))[:24]}"
    return {
        "schema": VALIDATION_REPORT_SCHEMA,
        "validationId": validation_id,
        "developmentEvaluationId": report.get("evaluationId"),
        "phaseId": protocol.phase_id,
        "protocolId": protocol.protocol_id,
        "materializationId": report.get("materializationId"),
        "candidateSetSha256": report.get("candidateSetSha256"),
        "candidateCount": len(protocol.candidates),
        "multipleTestingBudget": PLANNED_MULTIPLE_TESTING_BUDGET,
        "windowCount": 12,
        "baselineId": BASELINE_ID,
        "policy": {
            "minimumTrades": MINIMUM_TOTAL_TRADES,
            "minimumBeatBaselineWindows": MINIMUM_BASELINE_BEATING_WINDOWS,
            "adjustedAlphaMax": ADJUSTED_ALPHA_MAX,
            "nullModel": "exact_window_sign_flip",
            "permutationCount": PERMUTATION_COUNT,
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


def write_immutable_report(path: str | Path, report: Mapping[str, Any]) -> Path:
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    serialized = json.dumps(dict(report), sort_keys=True, indent=2) + "\n"
    if output.exists():
        if output.read_text(encoding="utf-8") != serialized:
            raise RuntimeError("refusing to overwrite immutable SF2 report")
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
