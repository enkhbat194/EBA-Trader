from __future__ import annotations

import json
import math
import statistics
import tempfile
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .atr_backtest import AtrTrailingConfig, run_atr_trailing_backtest
from .backtest_adapter import EmaFeatureBaselineV1Adapter, _result_metrics
from .history import validate_interval_window
from .m5_multiwindow import _load_materialization
from .orderflow_feature_dataset import load_orderflow_feature_csv
from .research_evidence import canonical_json, sha256_text

CANDIDATE_SET_SCHEMA = "sf1_candidate_set_v1"
REPORT_SCHEMA = "sf1_development_report_v1"
PHASE_ID = "sf1_independent_families_v1"
EXPECTED_SEARCH_BUDGET = 48
EXPECTED_WARMUP_BARS = 64
BASELINE_FAST_EMA = 12
BASELINE_SLOW_EMA = 26
INITIAL_CASH = 10_000.0
FEE_BPS = 4.0
SLIPPAGE_BPS = 1.5


@dataclass(frozen=True, slots=True)
class SF1Candidate:
    candidate_id: str
    family: str
    parameters: dict[str, float | int]

    def as_dict(self) -> dict[str, Any]:
        return {
            "candidate_id": self.candidate_id,
            "family": self.family,
            "parameters": dict(self.parameters),
        }


def _json_object(path: Path, *, label: str) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"cannot read {label}") from exc
    if not isinstance(payload, dict):
        raise ValueError(f"{label} must be a JSON object")
    return payload


def load_sf1_candidates(path: str | Path) -> tuple[int, int, tuple[SF1Candidate, ...]]:
    payload = _json_object(Path(path), label="SF1 candidate set")
    expected = {"schema", "phase_id", "planned_candidate_budget", "warmup_bars", "candidates"}
    if set(payload) != expected:
        raise ValueError("invalid SF1 candidate set fields")
    if payload.get("schema") != CANDIDATE_SET_SCHEMA or payload.get("phase_id") != PHASE_ID:
        raise ValueError("unsupported SF1 candidate set identity")
    budget = payload.get("planned_candidate_budget")
    warmup = payload.get("warmup_bars")
    if budget != EXPECTED_SEARCH_BUDGET:
        raise ValueError("SF1 planned candidate budget is not the preregistered value")
    if warmup != EXPECTED_WARMUP_BARS:
        raise ValueError("SF1 warmup bars are not the preregistered value")
    rows = payload.get("candidates")
    if not isinstance(rows, list) or not rows or len(rows) > budget:
        raise ValueError("SF1 candidate list is invalid")

    result: list[SF1Candidate] = []
    ids: set[str] = set()
    fingerprints: set[str] = set()
    for row in rows:
        if not isinstance(row, dict) or set(row) != {"candidate_id", "family", "parameters"}:
            raise ValueError("invalid SF1 candidate entry")
        candidate_id = str(row["candidate_id"]).strip()
        family = str(row["family"]).strip()
        parameters = row["parameters"]
        if not candidate_id or candidate_id in ids:
            raise ValueError("SF1 candidate_id is empty or duplicated")
        if family != "atr_trailing_v1":
            raise ValueError(f"SF1 family is not implemented yet: {family}")
        if not isinstance(parameters, Mapping) or set(parameters) != {"atr_period", "atr_multiplier"}:
            raise ValueError("ATR candidate parameters are invalid")
        period = parameters["atr_period"]
        multiplier = parameters["atr_multiplier"]
        if isinstance(period, bool) or not isinstance(period, int):
            raise ValueError("atr_period must be an integer")
        if isinstance(multiplier, bool) or not isinstance(multiplier, (int, float)):
            raise ValueError("atr_multiplier must be numeric")
        config = AtrTrailingConfig(atr_period=period, atr_multiplier=float(multiplier))
        normalized = {"atr_period": config.atr_period, "atr_multiplier": config.atr_multiplier}
        fingerprint = canonical_json({"family": family, "parameters": normalized})
        if fingerprint in fingerprints:
            raise ValueError("duplicate SF1 candidate parameters")
        ids.add(candidate_id)
        fingerprints.add(fingerprint)
        result.append(SF1Candidate(candidate_id, family, normalized))
    return budget, warmup, tuple(result)


def _numeric(metrics: Mapping[str, Any], key: str) -> float:
    value = metrics.get(key)
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise RuntimeError(f"missing numeric SF1 metric: {key}")
    number = float(value)
    if not math.isfinite(number):
        raise RuntimeError(f"non-finite SF1 metric: {key}")
    return number


def _aggregate(windows: list[dict[str, Any]], baseline: Mapping[str, dict[str, Any]] | None) -> dict[str, Any]:
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
            base_return = _numeric(baseline[row["windowName"]]["metrics"], "total_return")
            deltas.append(total_return - base_return)

    aggregate: dict[str, Any] = {
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
        aggregate.update(
            {
                "beatBaselineWindowCount": sum(value > 0.0 for value in deltas),
                "notWorseThanBaselineWindowCount": sum(value >= 0.0 for value in deltas),
                "meanReturnDeltaVsBaseline": statistics.fmean(deltas),
                "medianReturnDeltaVsBaseline": statistics.median(deltas),
                "worstReturnDeltaVsBaseline": min(deltas),
                "bestReturnDeltaVsBaseline": max(deltas),
            }
        )
    return aggregate


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


def evaluate_sf1_atr(
    *,
    manifest_path: str | Path,
    dataset_root: str | Path,
    candidate_set_path: str | Path,
) -> dict[str, Any]:
    budget, warmup_bars, candidates = load_sf1_candidates(candidate_set_path)
    manifest, receipts = _load_materialization(
        manifest_path=Path(manifest_path), dataset_root=Path(dataset_root)
    )
    baseline_windows: list[dict[str, Any]] = []
    candidate_windows: dict[str, list[dict[str, Any]]] = {
        candidate.candidate_id: [] for candidate in candidates
    }

    for receipt in receipts:
        path = Path(receipt["dataset_path"])
        feature_rows = load_orderflow_feature_csv(path)
        candles = validate_interval_window(
            [row.candle for row in feature_rows],
            str(manifest["interval"]),
            int(receipt["start_ms"]),
            int(receipt["end_ms"]),
        )
        if len(candles) <= warmup_bars + 2:
            raise RuntimeError(f"SF1 window is too short for preregistered warmup: {receipt['window_name']}")
        evaluation_start_ms = candles[warmup_bars].open_time_ms
        strategy_spec = {
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
                "symbol": str(manifest["symbol"]),
                "interval": str(manifest["interval"]),
                "start_ms": int(receipt["start_ms"]),
                "end_ms": int(receipt["end_ms"]),
            },
        }
        baseline_execution = EmaFeatureBaselineV1Adapter().run(
            dataset_path=path,
            strategy_spec=strategy_spec,
            experiment_parameters={},
            stage="sf1_development_baseline",
        )
        baseline_windows.append(
            {
                "windowName": str(receipt["window_name"]),
                "evaluationStartMs": evaluation_start_ms,
                "metrics": baseline_execution.metrics,
            }
        )

        for candidate in candidates:
            cfg = AtrTrailingConfig(
                atr_period=int(candidate.parameters["atr_period"]),
                atr_multiplier=float(candidate.parameters["atr_multiplier"]),
                initial_cash=INITIAL_CASH,
                fee_bps=FEE_BPS,
                slippage_bps=SLIPPAGE_BPS,
            )
            result = run_atr_trailing_backtest(
                candles, cfg, trade_start_time_ms=evaluation_start_ms
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
    for candidate in candidates:
        windows = candidate_windows[candidate.candidate_id]
        evaluated.append(
            {
                "candidateId": candidate.candidate_id,
                "family": candidate.family,
                "parameters": dict(candidate.parameters),
                "windows": windows,
                "aggregate": _aggregate(windows, baseline_by_name),
            }
        )
    ranked = sorted(evaluated, key=_ranking_key, reverse=True)
    development_ranking = [
        {
            "developmentPriorityRank": index,
            "candidateId": row["candidateId"],
            "family": row["family"],
            "parameters": row["parameters"],
            "aggregate": row["aggregate"],
        }
        for index, row in enumerate(ranked, start=1)
    ]

    candidate_identity = [candidate.as_dict() for candidate in candidates]
    candidate_set_sha = sha256_text(canonical_json(candidate_identity))
    identity = {
        "schema": REPORT_SCHEMA,
        "phaseId": PHASE_ID,
        "materializationId": manifest["materialization_id"],
        "candidateSetSha256": candidate_set_sha,
        "multipleTestingBudget": budget,
        "warmupBars": warmup_bars,
    }
    evaluation_id = f"sf1eval_{sha256_text(canonical_json(identity))[:24]}"
    return {
        "schema": REPORT_SCHEMA,
        "evaluationId": evaluation_id,
        "phaseId": PHASE_ID,
        "materializationId": manifest["materialization_id"],
        "candidateSetSha256": candidate_set_sha,
        "candidateCount": len(candidates),
        "multipleTestingBudget": budget,
        "warmupBars": warmup_bars,
        "windowCount": len(baseline_windows),
        "baseline": {"family": "ema_feature_baseline_v1", "windows": baseline_windows, "aggregate": baseline_aggregate},
        "candidates": evaluated,
        "developmentRanking": development_ranking,
        "rankingIsDevelopmentOnly": True,
        "developmentEvidenceOnly": True,
        "edgeClaimAllowed": False,
        "promotionAuthority": False,
        "frozenOosOpened": False,
        "m5FrozenOosOpened": False,
        "liveExecutionAllowed": False,
    }


def write_immutable_sf1_report(path: str | Path, report: Mapping[str, Any]) -> Path:
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    serialized = json.dumps(dict(report), sort_keys=True, indent=2) + "\n"
    if output.exists():
        if output.read_text(encoding="utf-8") != serialized:
            raise RuntimeError("refusing to overwrite immutable SF1 development report")
        return output
    with tempfile.NamedTemporaryFile(
        mode="w", encoding="utf-8", dir=output.parent, prefix=f".{output.name}.", delete=False
    ) as handle:
        handle.write(serialized)
        temporary = Path(handle.name)
    temporary.chmod(0o640)
    temporary.replace(output)
    return output
