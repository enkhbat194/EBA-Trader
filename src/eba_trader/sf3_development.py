from __future__ import annotations

import math
import statistics
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from .backtest_adapter import EmaFeatureBaselineV1Adapter, _result_metrics
from .history import validate_interval_window
from .m5_corpus_materializer import _load_completed_materialization
from .m5_study_policy import DEFAULT_M5_STUDY_POLICY
from .orderflow_feature_dataset import load_orderflow_feature_csv
from .research_evidence import canonical_json, sha256_text
from .sf2_development import (
    _aggregate,
    _exact_sign_flip_p_value,
    _numeric,
    _ranking_key,
    _resolve_under,
    _safe_contract,
    _window_returns,
    write_immutable_report,
)
from .sf3_protocol import (
    ADJUSTED_ALPHA_MAX,
    FEE_BPS,
    MINIMUM_BASELINE_BEATING_WINDOWS,
    MINIMUM_TOTAL_TRADES,
    PERMUTATION_COUNT,
    PLANNED_MULTIPLE_TESTING_BUDGET,
    SLIPPAGE_BPS,
    SF3ResearchProtocol,
    load_sf3_protocol,
)
from .sf3_signal_backtest import run_sf3_candidate_backtest

DEVELOPMENT_REPORT_SCHEMA = "sf3_development_report_v1"
VALIDATION_REPORT_SCHEMA = "sf3_validation_report_v1"
BASELINE_ID = "ema_feature_baseline_v1_12_26"
BASELINE_FAST_EMA = 12
BASELINE_SLOW_EMA = 26
INITIAL_CASH = 10_000.0
PRICE_BUCKET = 1.0
ORDERFLOW_SOURCE = "archive"
SF3_NAMESPACE = "sf3_orderflow_dev"


def candidate_set_sha256(protocol: SF3ResearchProtocol) -> str:
    payload = [candidate.as_dict() for candidate in protocol.candidates]
    return sha256_text(canonical_json(payload))


def _load_sf3_materialization(
    *,
    manifest_path: Path,
    dataset_root: Path,
    protocol: SF3ResearchProtocol,
) -> tuple[Any, tuple[dict[str, Any], ...]]:
    import json

    try:
        payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise RuntimeError("cannot read SF3 corpus materialization") from exc
    if not isinstance(payload, dict):
        raise RuntimeError("SF3 corpus materialization must be a JSON object")
    materialization_id = str(payload.get("materialization_id") or "")
    if not materialization_id:
        raise RuntimeError("SF3 corpus materialization is missing materialization_id")

    materialization = _load_completed_materialization(
        manifest_path,
        materialization_id=materialization_id,
        corpus=protocol.corpus,
        dataset_root=dataset_root,
        price_bucket=PRICE_BUCKET,
        namespace=SF3_NAMESPACE,
        orderflow_source=ORDERFLOW_SOURCE,
    )
    policy = DEFAULT_M5_STUDY_POLICY
    checks = (
        materialization.policy_id == policy.policy_id,
        materialization.corpus_id == protocol.corpus.corpus_id,
        materialization.symbol == policy.symbol,
        materialization.venue == policy.venue,
        materialization.interval == policy.interval,
        len(materialization.windows) == len(protocol.corpus.windows),
    )
    if not all(checks):
        raise RuntimeError("SF3 materialization identity mismatch")

    receipts: list[dict[str, Any]] = []
    for receipt, expected in zip(materialization.windows, protocol.corpus.windows, strict=True):
        if receipt.window_name != expected.name:
            raise RuntimeError("SF3 receipt window name mismatch")
        if receipt.start_ms != expected.start_ms or receipt.end_ms != expected.end_ms:
            raise RuntimeError("SF3 receipt time range mismatch")
        path = _resolve_under(dataset_root, receipt.dataset_ref, label="SF3 dataset_ref")
        if not path.is_file():
            raise RuntimeError(f"SF3 feature dataset is missing: {expected.name}")
        receipts.append(
            {
                "window_name": receipt.window_name,
                "start_ms": receipt.start_ms,
                "end_ms": receipt.end_ms,
                "dataset_path": path,
            }
        )
    return materialization, tuple(receipts)


def evaluate_sf3_development(
    *,
    manifest_path: str | Path,
    dataset_root: str | Path,
    protocol_path: str | Path,
) -> dict[str, Any]:
    protocol = load_sf3_protocol(protocol_path)
    dataset_root_path = Path(dataset_root).resolve()
    materialization, receipts = _load_sf3_materialization(
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
            name = receipt["window_name"]
            raise RuntimeError(f"SF3 window is too short for preregistered warmup: {name}")
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
            stage="sf3_development_baseline",
        )
        baseline_windows.append(
            {
                "windowName": str(receipt["window_name"]),
                "evaluationStartMs": evaluation_start_ms,
                "metrics": baseline.metrics,
            }
        )

        for candidate in protocol.candidates:
            result = run_sf3_candidate_backtest(
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
    evaluation_id = f"sf3dev_{sha256_text(canonical_json(identity))[:24]}"
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


def _same_number(left: Any, right: float) -> bool:
    if isinstance(left, bool) or not isinstance(left, (int, float)):
        return False
    value = float(left)
    if not math.isfinite(value):
        return False
    return math.isclose(value, right, rel_tol=1e-12, abs_tol=1e-15)


def validate_sf3_development(
    report: Mapping[str, Any],
    *,
    protocol_path: str | Path,
) -> dict[str, Any]:
    protocol = load_sf3_protocol(protocol_path)
    if report.get("schema") != DEVELOPMENT_REPORT_SCHEMA:
        raise RuntimeError("unsupported SF3 development report schema")
    if not _safe_contract(report):
        raise RuntimeError("unsafe SF3 development report")
    if report.get("phaseId") != protocol.phase_id:
        raise RuntimeError("SF3 development phase identity mismatch")
    if report.get("protocolId") != protocol.protocol_id:
        raise RuntimeError("SF3 development protocol identity mismatch")
    if report.get("candidateSetSha256") != candidate_set_sha256(protocol):
        raise RuntimeError("SF3 candidate-set identity mismatch")
    if report.get("candidateCount") != len(protocol.candidates):
        raise RuntimeError("SF3 development candidate count mismatch")
    if report.get("multipleTestingBudget") != PLANNED_MULTIPLE_TESTING_BUDGET:
        raise RuntimeError("SF3 multiple-testing budget mismatch")
    if report.get("windowCount") != 12:
        raise RuntimeError("SF3 development window count mismatch")

    baseline = report.get("baseline")
    if not isinstance(baseline, Mapping) or baseline.get("baselineId") != BASELINE_ID:
        raise RuntimeError("SF3 baseline identity mismatch")
    baseline_rows = baseline.get("windows")
    baseline_returns = _window_returns(baseline_rows, label="SF3 baseline")
    if not isinstance(baseline_rows, list):
        raise RuntimeError("SF3 baseline windows are missing")
    baseline_by_name = {
        row["windowName"]: row
        for row in baseline_rows
        if isinstance(row, dict) and isinstance(row.get("windowName"), str)
    }
    if set(baseline_by_name) != set(baseline_returns):
        raise RuntimeError("SF3 baseline window identity mismatch")

    candidates = report.get("candidates")
    if not isinstance(candidates, list) or len(candidates) != len(protocol.candidates):
        raise RuntimeError("SF3 candidate payload count mismatch")
    expected = {candidate.candidate_id: candidate for candidate in protocol.candidates}

    rows: list[dict[str, Any]] = []
    verified: list[dict[str, Any]] = []
    seen: set[str] = set()
    for candidate in candidates:
        if not isinstance(candidate, Mapping):
            raise RuntimeError("SF3 candidate row is invalid")
        candidate_id = candidate.get("candidateId")
        if not isinstance(candidate_id, str) or candidate_id not in expected or candidate_id in seen:
            raise RuntimeError("SF3 candidateId is invalid, unknown or duplicated")
        seen.add(candidate_id)
        spec = expected[candidate_id]
        if candidate.get("family") != spec.family:
            raise RuntimeError(f"SF3 candidate family mismatch: {candidate_id}")
        if dict(candidate.get("parameters") or {}) != spec.parameters:
            raise RuntimeError(f"SF3 candidate parameters mismatch: {candidate_id}")

        candidate_windows = candidate.get("windows")
        if not isinstance(candidate_windows, list):
            raise RuntimeError(f"SF3 candidate windows are missing: {candidate_id}")
        recomputed = _aggregate(candidate_windows, baseline_by_name)
        aggregate = candidate.get("aggregate")
        if not isinstance(aggregate, Mapping):
            raise RuntimeError("SF3 candidate aggregate is missing")
        for key in (
            "meanReturn",
            "meanExpectancy",
            "totalTradeCount",
            "beatBaselineWindowCount",
            "meanReturnDeltaVsBaseline",
        ):
            if not _same_number(aggregate.get(key), _numeric(recomputed, key)):
                raise RuntimeError(f"SF3 aggregate mismatch for {candidate_id}: {key}")

        mean_return = _numeric(recomputed, "meanReturn")
        mean_expectancy = _numeric(recomputed, "meanExpectancy")
        total_trades = _numeric(recomputed, "totalTradeCount")
        beat_windows = _numeric(recomputed, "beatBaselineWindowCount")
        profitable = mean_return > 0.0 and mean_expectancy > 0.0
        sample_sufficient = total_trades >= MINIMUM_TOTAL_TRADES
        coverage_sufficient = beat_windows >= MINIMUM_BASELINE_BEATING_WINDOWS

        candidate_returns = _window_returns(candidate_windows, label=candidate_id)
        if set(candidate_returns) != set(baseline_returns):
            raise RuntimeError(f"SF3 candidate window set mismatch: {candidate_id}")
        deltas = tuple(
            candidate_returns[name] - baseline_returns[name] for name in baseline_returns
        )
        observed_mean = statistics.fmean(deltas)
        raw_p, extreme_count, permutation_count = _exact_sign_flip_p_value(deltas)
        if permutation_count != PERMUTATION_COUNT:
            raise RuntimeError("SF3 permutation-count identity mismatch")
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
            "family": spec.family,
            "parameters": dict(spec.parameters),
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

    if seen != set(expected):
        raise RuntimeError("SF3 candidate set is incomplete")

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
    validation_id = f"sf3val_{sha256_text(canonical_json(identity))[:24]}"
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
