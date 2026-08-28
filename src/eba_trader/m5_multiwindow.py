from __future__ import annotations

import argparse
import json
import math
import statistics
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .backtest_adapter import EmaFeatureBaselineV1Adapter, EmaOrderFlowV1Adapter
from .m5_ablation import OrderFlowGate
from .m5_corpus_materializer import (
    CORPUS_MATERIALIZATION_SCHEMA,
    CORPUS_WINDOW_RECEIPT_SCHEMA,
)
from .m5_study_policy import (
    DEFAULT_M5_DEVELOPMENT_CORPUS,
    DEFAULT_M5_STUDY_POLICY,
    assert_m5_development_range,
)
from .research_evidence import canonical_json, sha256_file, sha256_text

CANDIDATE_SET_SCHEMA = "m5_multiwindow_candidate_set_v1"
REPORT_SCHEMA = "m5_multiwindow_development_report_v1"
EVALUATION_STAGE = "m5_multiwindow_development_eval"
DEFAULT_CANDIDATE_SET = Path("config/m5_multiwindow_candidate_set_v1.json")
DEFAULT_FAST_EMA = 12
DEFAULT_SLOW_EMA = 26
DEFAULT_INITIAL_CASH = 10_000.0
DEFAULT_FEE_BPS = 4.0
DEFAULT_SLIPPAGE_BPS = 1.5

_GATE_FIELDS = {
    "delta_ratio_threshold",
    "cvd_threshold",
    "stacked_imbalance_threshold",
    "absorption_threshold",
    "exhaustion_threshold",
    "price_delta_divergence_threshold",
}
_RECEIPT_FIELDS = {
    "schema",
    "materialization_id",
    "policy_id",
    "corpus_id",
    "window_name",
    "start_ms",
    "end_ms",
    "orderflow_source",
    "workflow_id",
    "workflow_manifest_ref",
    "feature_dataset_id",
    "dataset_ref",
    "feature_csv_sha256",
}
_MATERIALIZATION_FIELDS = {
    "schema",
    "materialization_id",
    "policy_id",
    "corpus_id",
    "symbol",
    "venue",
    "interval",
    "price_bucket",
    "namespace",
    "orderflow_source",
    "window_count",
    "windows",
    "frozen_oos_opened",
    "m5_frozen_oos_opened",
    "live_execution_allowed",
}


@dataclass(frozen=True, slots=True)
class M5MultiWindowCandidate:
    candidate_id: str
    parameters: dict[str, float | int]

    def as_dict(self) -> dict[str, object]:
        return {
            "candidate_id": self.candidate_id,
            "parameters": dict(self.parameters),
        }


@dataclass(frozen=True, slots=True)
class M5MultiWindowConfig:
    fast_ema: int = DEFAULT_FAST_EMA
    slow_ema: int = DEFAULT_SLOW_EMA
    initial_cash: float = DEFAULT_INITIAL_CASH
    fee_bps: float = DEFAULT_FEE_BPS
    slippage_bps: float = DEFAULT_SLIPPAGE_BPS

    def validate(self) -> None:
        if self.fast_ema < 1 or self.slow_ema < 2 or self.fast_ema >= self.slow_ema:
            raise ValueError("EMA parameters require 1 <= fast_ema < slow_ema")
        for name, value, allow_zero in (
            ("initial_cash", self.initial_cash, False),
            ("fee_bps", self.fee_bps, True),
            ("slippage_bps", self.slippage_bps, True),
        ):
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                raise ValueError(f"{name} must be numeric")
            number = float(value)
            if not math.isfinite(number):
                raise ValueError(f"{name} must be finite")
            if allow_zero and number < 0.0:
                raise ValueError(f"{name} must be non-negative")
            if not allow_zero and number <= 0.0:
                raise ValueError(f"{name} must be positive")

    def as_dict(self) -> dict[str, float | int]:
        self.validate()
        return {
            "fast_ema": self.fast_ema,
            "slow_ema": self.slow_ema,
            "initial_cash": float(self.initial_cash),
            "fee_bps": float(self.fee_bps),
            "slippage_bps": float(self.slippage_bps),
        }


def _json_object(path: Path, *, label: str) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"cannot read {label}") from exc
    if not isinstance(payload, dict):
        raise ValueError(f"{label} must be a JSON object")
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
        raise ValueError(f"{label} escapes the configured dataset root") from exc
    return candidate


def _validated_gate_parameters(raw: object) -> dict[str, float | int]:
    if not isinstance(raw, Mapping):
        raise ValueError("candidate parameters must be an object")
    unknown = sorted(set(raw) - _GATE_FIELDS)
    if unknown:
        raise ValueError(f"unsupported candidate parameter fields: {', '.join(unknown)}")
    kwargs = {str(key): value for key, value in raw.items()}
    try:
        gate = OrderFlowGate(**kwargs)
    except TypeError as exc:
        raise ValueError("invalid candidate parameters") from exc
    return gate.parameters()


def load_m5_multiwindow_candidates(path: str | Path) -> tuple[M5MultiWindowCandidate, ...]:
    payload = _json_object(Path(path), label="M5 multi-window candidate set")
    if set(payload) != {"schema", "candidates"}:
        raise ValueError("invalid M5 multi-window candidate set fields")
    if payload.get("schema") != CANDIDATE_SET_SCHEMA:
        raise ValueError("unsupported M5 multi-window candidate set schema")
    rows = payload.get("candidates")
    if not isinstance(rows, list) or not rows:
        raise ValueError("M5 multi-window candidate set must contain candidates")

    candidates: list[M5MultiWindowCandidate] = []
    ids: set[str] = set()
    parameter_fingerprints: set[str] = set()
    for row in rows:
        if not isinstance(row, dict) or set(row) != {"candidate_id", "parameters"}:
            raise ValueError("invalid M5 multi-window candidate entry")
        candidate_id = str(row["candidate_id"]).strip()
        if not candidate_id:
            raise ValueError("candidate_id is required")
        if candidate_id in ids:
            raise ValueError(f"duplicate candidate_id: {candidate_id}")
        parameters = _validated_gate_parameters(row["parameters"])
        fingerprint = canonical_json(parameters)
        if fingerprint in parameter_fingerprints:
            raise ValueError("duplicate M5 multi-window candidate parameters")
        ids.add(candidate_id)
        parameter_fingerprints.add(fingerprint)
        candidates.append(
            M5MultiWindowCandidate(
                candidate_id=candidate_id,
                parameters=parameters,
            )
        )
    return tuple(candidates)


def _load_materialization(
    *,
    manifest_path: Path,
    dataset_root: Path,
) -> tuple[dict[str, Any], tuple[dict[str, Any], ...]]:
    payload = _json_object(manifest_path, label="M5 corpus materialization manifest")
    if set(payload) != _MATERIALIZATION_FIELDS:
        raise ValueError("invalid M5 corpus materialization fields")
    if payload.get("schema") != CORPUS_MATERIALIZATION_SCHEMA:
        raise ValueError("unsupported M5 corpus materialization schema")
    policy = DEFAULT_M5_STUDY_POLICY
    corpus = DEFAULT_M5_DEVELOPMENT_CORPUS
    if payload.get("policy_id") != policy.policy_id:
        raise RuntimeError("M5 multi-window materialization policy mismatch")
    if payload.get("corpus_id") != corpus.corpus_id:
        raise RuntimeError("M5 multi-window materialization corpus mismatch")
    if payload.get("symbol") != policy.symbol:
        raise RuntimeError("M5 multi-window materialization symbol mismatch")
    if payload.get("venue") != policy.venue:
        raise RuntimeError("M5 multi-window materialization venue mismatch")
    if payload.get("interval") != policy.interval:
        raise RuntimeError("M5 multi-window materialization interval mismatch")
    if payload.get("orderflow_source") != "archive":
        raise RuntimeError("M5 multi-window evaluator requires archive order-flow provenance")
    if payload.get("window_count") != len(corpus.windows):
        raise RuntimeError("M5 multi-window materialization must contain the sealed 12 windows")
    if payload.get("frozen_oos_opened") is not False:
        raise RuntimeError("legacy frozen OOS must remain closed")
    if payload.get("m5_frozen_oos_opened") is not False:
        raise RuntimeError("M5 frozen OOS must remain closed")
    if payload.get("live_execution_allowed") is not False:
        raise RuntimeError("M5 multi-window evaluator cannot enable live execution")

    raw_windows = payload.get("windows")
    if not isinstance(raw_windows, list) or len(raw_windows) != len(corpus.windows):
        raise RuntimeError("M5 multi-window materialization windows are incomplete")

    validated: list[dict[str, Any]] = []
    for raw, expected in zip(raw_windows, corpus.windows, strict=True):
        if not isinstance(raw, dict) or set(raw) != _RECEIPT_FIELDS:
            raise ValueError("invalid M5 corpus window receipt")
        if raw.get("schema") != CORPUS_WINDOW_RECEIPT_SCHEMA:
            raise ValueError("unsupported M5 corpus window receipt schema")
        if raw.get("materialization_id") != payload.get("materialization_id"):
            raise RuntimeError("M5 corpus receipt materialization mismatch")
        if raw.get("policy_id") != policy.policy_id or raw.get("corpus_id") != corpus.corpus_id:
            raise RuntimeError("M5 corpus receipt policy/corpus mismatch")
        if raw.get("window_name") != expected.name:
            raise RuntimeError("M5 corpus receipt window name mismatch")
        if raw.get("start_ms") != expected.start_ms or raw.get("end_ms") != expected.end_ms:
            raise RuntimeError("M5 corpus receipt window range mismatch")
        if raw.get("orderflow_source") != "archive":
            raise RuntimeError("M5 corpus receipt order-flow provenance mismatch")
        assert_m5_development_range(
            symbol=policy.symbol,
            venue=policy.venue,
            interval=policy.interval,
            start_ms=expected.start_ms,
            end_ms=expected.end_ms,
            context=f"M5 multi-window evaluation {expected.name}",
        )
        dataset_ref = str(raw.get("dataset_ref") or "")
        dataset_path = _resolve_under(dataset_root, dataset_ref, label="dataset_ref")
        if not dataset_path.is_file():
            raise RuntimeError(f"M5 multi-window dataset is missing: {expected.name}")
        expected_hash = str(raw.get("feature_csv_sha256") or "")
        if len(expected_hash) != 64 or sha256_file(dataset_path) != expected_hash:
            raise RuntimeError(f"M5 multi-window dataset integrity mismatch: {expected.name}")
        validated.append({**raw, "dataset_path": dataset_path})
    return payload, tuple(validated)


def _numeric_metric(metrics: Mapping[str, Any], name: str) -> float:
    value = metrics.get(name)
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise RuntimeError(f"M5 multi-window metric {name} is missing or non-numeric")
    number = float(value)
    if not math.isfinite(number):
        raise RuntimeError(f"M5 multi-window metric {name} must be finite")
    return number


def _metric_delta(
    baseline: Mapping[str, Any],
    treatment: Mapping[str, Any],
) -> dict[str, float]:
    result: dict[str, float] = {}
    for key in sorted(set(baseline) & set(treatment)):
        left = baseline[key]
        right = treatment[key]
        if isinstance(left, bool) or isinstance(right, bool):
            continue
        if not isinstance(left, (int, float)) or not isinstance(right, (int, float)):
            continue
        left_number = float(left)
        right_number = float(right)
        if math.isfinite(left_number) and math.isfinite(right_number):
            result[str(key)] = right_number - left_number
    return result


def _aggregate_baseline(windows: tuple[dict[str, Any], ...]) -> dict[str, Any]:
    returns = [_numeric_metric(item["metrics"], "total_return") for item in windows]
    expectancies = [_numeric_metric(item["metrics"], "expectancy") for item in windows]
    drawdowns = [_numeric_metric(item["metrics"], "max_drawdown") for item in windows]
    costs = [_numeric_metric(item["metrics"], "total_cost") for item in windows]
    trades = [int(_numeric_metric(item["metrics"], "trade_count")) for item in windows]
    return {
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


def _aggregate_candidate(
    *,
    windows: tuple[dict[str, Any], ...],
    baseline_by_name: Mapping[str, dict[str, Any]],
) -> dict[str, Any]:
    returns: list[float] = []
    return_deltas: list[float] = []
    expectancies: list[float] = []
    drawdowns: list[float] = []
    costs: list[float] = []
    trades: list[int] = []
    beat_baseline_count = 0
    not_worse_baseline_count = 0
    for item in windows:
        metrics = item["metrics"]
        total_return = _numeric_metric(metrics, "total_return")
        baseline_return = _numeric_metric(
            baseline_by_name[item["windowName"]]["metrics"],
            "total_return",
        )
        delta = total_return - baseline_return
        returns.append(total_return)
        return_deltas.append(delta)
        expectancies.append(_numeric_metric(metrics, "expectancy"))
        drawdowns.append(_numeric_metric(metrics, "max_drawdown"))
        costs.append(_numeric_metric(metrics, "total_cost"))
        trades.append(int(_numeric_metric(metrics, "trade_count")))
        beat_baseline_count += int(delta > 0.0)
        not_worse_baseline_count += int(delta >= 0.0)

    return {
        "windowCount": len(windows),
        "meanReturn": statistics.fmean(returns),
        "medianReturn": statistics.median(returns),
        "worstWindowReturn": min(returns),
        "bestWindowReturn": max(returns),
        "positiveWindowCount": sum(value > 0.0 for value in returns),
        "beatBaselineWindowCount": beat_baseline_count,
        "notWorseThanBaselineWindowCount": not_worse_baseline_count,
        "meanReturnDeltaVsBaseline": statistics.fmean(return_deltas),
        "medianReturnDeltaVsBaseline": statistics.median(return_deltas),
        "worstReturnDeltaVsBaseline": min(return_deltas),
        "bestReturnDeltaVsBaseline": max(return_deltas),
        "meanExpectancy": statistics.fmean(expectancies),
        "worstMaxDrawdown": min(drawdowns),
        "totalTradeCount": sum(trades),
        "totalCost": sum(costs),
    }


def _ranking_key(candidate: Mapping[str, Any]) -> tuple[float, ...]:
    aggregate = candidate["aggregate"]
    return (
        float(aggregate["beatBaselineWindowCount"]),
        float(aggregate["positiveWindowCount"]),
        float(aggregate["medianReturnDeltaVsBaseline"]),
        float(aggregate["worstReturnDeltaVsBaseline"]),
        float(aggregate["meanReturnDeltaVsBaseline"]),
    )


def evaluate_m5_multiwindow(
    *,
    materialization_manifest: str | Path,
    dataset_root: str | Path,
    candidates: tuple[M5MultiWindowCandidate, ...],
    config: M5MultiWindowConfig | None = None,
    baseline_adapter: Any | None = None,
    orderflow_adapter: Any | None = None,
) -> dict[str, Any]:
    if not candidates:
        raise ValueError("M5 multi-window evaluation requires candidates")
    config = config or M5MultiWindowConfig()
    config_payload = config.as_dict()
    dataset_root_path = Path(dataset_root).resolve()
    materialization, receipts = _load_materialization(
        manifest_path=Path(materialization_manifest).resolve(),
        dataset_root=dataset_root_path,
    )
    baseline_adapter = baseline_adapter or EmaFeatureBaselineV1Adapter()
    orderflow_adapter = orderflow_adapter or EmaOrderFlowV1Adapter()

    baseline_windows: list[dict[str, Any]] = []
    candidate_windows: dict[str, list[dict[str, Any]]] = {
        candidate.candidate_id: [] for candidate in candidates
    }
    for receipt in receipts:
        dataset_spec = {
            "symbol": DEFAULT_M5_STUDY_POLICY.symbol,
            "interval": DEFAULT_M5_STUDY_POLICY.interval,
            "start_ms": receipt["start_ms"],
            "end_ms": receipt["end_ms"],
        }
        baseline_spec = {
            "adapter": "ema_feature_baseline_v1",
            "fixed": config_payload,
            "dataset": dataset_spec,
        }
        baseline_execution = baseline_adapter.run(
            dataset_path=receipt["dataset_path"],
            strategy_spec=baseline_spec,
            experiment_parameters={},
            stage=EVALUATION_STAGE,
            allow_frozen_oos=False,
        )
        baseline_item = {
            "windowName": receipt["window_name"],
            "startMs": receipt["start_ms"],
            "endMs": receipt["end_ms"],
            "datasetRef": receipt["dataset_ref"],
            "featureCsvSha256": receipt["feature_csv_sha256"],
            "metrics": baseline_execution.metrics,
        }
        baseline_windows.append(baseline_item)

        orderflow_spec = {
            "adapter": "ema_orderflow_v1",
            "fixed": config_payload,
            "dataset": dataset_spec,
        }
        for candidate in candidates:
            execution = orderflow_adapter.run(
                dataset_path=receipt["dataset_path"],
                strategy_spec=orderflow_spec,
                experiment_parameters=candidate.parameters,
                stage=EVALUATION_STAGE,
                allow_frozen_oos=False,
            )
            candidate_windows[candidate.candidate_id].append(
                {
                    "windowName": receipt["window_name"],
                    "startMs": receipt["start_ms"],
                    "endMs": receipt["end_ms"],
                    "datasetRef": receipt["dataset_ref"],
                    "featureCsvSha256": receipt["feature_csv_sha256"],
                    "metrics": execution.metrics,
                    "metricDeltaVsBaseline": _metric_delta(
                        baseline_execution.metrics,
                        execution.metrics,
                    ),
                }
            )

    baseline_tuple = tuple(baseline_windows)
    baseline_by_name = {item["windowName"]: item for item in baseline_tuple}
    candidate_reports: list[dict[str, Any]] = []
    for candidate in candidates:
        windows = tuple(candidate_windows[candidate.candidate_id])
        candidate_reports.append(
            {
                "candidateId": candidate.candidate_id,
                "parameters": dict(candidate.parameters),
                "windows": list(windows),
                "aggregate": _aggregate_candidate(
                    windows=windows,
                    baseline_by_name=baseline_by_name,
                ),
            }
        )

    ranked = sorted(
        candidate_reports,
        key=lambda item: (*_ranking_key(item), item["candidateId"]),
        reverse=True,
    )
    ranking = [
        {
            "developmentPriorityRank": index,
            "candidateId": item["candidateId"],
            "parameters": item["parameters"],
            "aggregate": item["aggregate"],
        }
        for index, item in enumerate(ranked, start=1)
    ]
    candidate_identity = [candidate.as_dict() for candidate in candidates]
    identity = {
        "schema": REPORT_SCHEMA,
        "materialization_id": materialization["materialization_id"],
        "policy_id": materialization["policy_id"],
        "corpus_id": materialization["corpus_id"],
        "candidate_set": candidate_identity,
        "config": config_payload,
    }
    evaluation_id = f"m5multi_{sha256_text(canonical_json(identity))[:24]}"
    return {
        "schema": REPORT_SCHEMA,
        "evaluationId": evaluation_id,
        "stage": EVALUATION_STAGE,
        "materializationId": materialization["materialization_id"],
        "policyId": materialization["policy_id"],
        "corpusId": materialization["corpus_id"],
        "symbol": materialization["symbol"],
        "venue": materialization["venue"],
        "interval": materialization["interval"],
        "orderflowSource": materialization["orderflow_source"],
        "windowCount": len(baseline_tuple),
        "candidateCount": len(candidates),
        "fixedConfig": config_payload,
        "candidateSetSha256": sha256_text(canonical_json(candidate_identity)),
        "baseline": {
            "windows": list(baseline_tuple),
            "aggregate": _aggregate_baseline(baseline_tuple),
        },
        "candidates": candidate_reports,
        "developmentRanking": ranking,
        "rankingIsDevelopmentOnly": True,
        "edgeClaimAllowed": False,
        "promotionAuthority": False,
        "frozenOosOpened": False,
        "m5FrozenOosOpened": False,
        "liveExecutionAllowed": False,
    }


def write_immutable_m5_multiwindow_report(path: str | Path, report: dict[str, Any]) -> Path:
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(report, sort_keys=True, indent=2) + "\n"
    if output.exists():
        if output.read_text(encoding="utf-8") != text:
            raise RuntimeError("immutable M5 multi-window report collision")
        return output
    output.write_text(text, encoding="utf-8")
    output.chmod(0o640)
    return output


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Evaluate pre-registered M5 order-flow candidates across 12 development windows"
    )
    parser.add_argument("--materialization-manifest", required=True)
    parser.add_argument("--dataset-root", required=True)
    parser.add_argument("--candidates-json", default=str(DEFAULT_CANDIDATE_SET))
    parser.add_argument("--output", required=True)
    parser.add_argument("--fast-ema", type=int, default=DEFAULT_FAST_EMA)
    parser.add_argument("--slow-ema", type=int, default=DEFAULT_SLOW_EMA)
    parser.add_argument("--initial-cash", type=float, default=DEFAULT_INITIAL_CASH)
    parser.add_argument("--fee-bps", type=float, default=DEFAULT_FEE_BPS)
    parser.add_argument("--slippage-bps", type=float, default=DEFAULT_SLIPPAGE_BPS)
    args = parser.parse_args()

    candidates = load_m5_multiwindow_candidates(args.candidates_json)
    report = evaluate_m5_multiwindow(
        materialization_manifest=args.materialization_manifest,
        dataset_root=args.dataset_root,
        candidates=candidates,
        config=M5MultiWindowConfig(
            fast_ema=args.fast_ema,
            slow_ema=args.slow_ema,
            initial_cash=args.initial_cash,
            fee_bps=args.fee_bps,
            slippage_bps=args.slippage_bps,
        ),
    )
    output = write_immutable_m5_multiwindow_report(args.output, report)
    print(
        json.dumps(
            {
                "report": str(output),
                "evaluationId": report["evaluationId"],
                "windowCount": report["windowCount"],
                "candidateCount": report["candidateCount"],
                "topDevelopmentCandidate": report["developmentRanking"][0]["candidateId"],
                "rankingIsDevelopmentOnly": True,
                "edgeClaimAllowed": False,
                "promotionAuthority": False,
                "frozenOosOpened": False,
                "m5FrozenOosOpened": False,
                "liveExecutionAllowed": False,
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
