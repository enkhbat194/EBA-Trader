from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from eba_trader.m5_corpus_materializer import (
    CORPUS_MATERIALIZATION_SCHEMA,
    CORPUS_WINDOW_RECEIPT_SCHEMA,
)
from eba_trader.m5_multiwindow import (
    CANDIDATE_SET_SCHEMA,
    M5MultiWindowCandidate,
    evaluate_m5_multiwindow,
    load_m5_multiwindow_candidates,
)
from eba_trader.m5_study_policy import (
    DEFAULT_M5_DEVELOPMENT_CORPUS,
    DEFAULT_M5_STUDY_POLICY,
)
from eba_trader.research_evidence import sha256_file


def _metrics(total_return: float, *, trades: int = 2) -> dict[str, float | int]:
    return {
        "initial_cash": 10_000.0,
        "final_equity": 10_000.0 * (1.0 + total_return),
        "total_return": total_return,
        "benchmark_return": 0.0,
        "benchmark_max_drawdown": -0.01,
        "benchmark_relative_return": total_return,
        "max_drawdown": min(0.0, total_return),
        "trade_count": trades,
        "win_rate": 0.5,
        "expectancy": total_return * 1_000.0,
        "average_win": 10.0,
        "average_loss": -10.0,
        "sharpe": 0.0,
        "sortino": 0.0,
        "exposure": 0.5,
        "total_cost": float(trades),
    }


class _BaselineAdapter:
    def run(self, **kwargs: object) -> SimpleNamespace:
        spec = kwargs["strategy_spec"]
        start_ms = spec["dataset"]["start_ms"]  # type: ignore[index]
        ordered = [window.start_ms for window in DEFAULT_M5_DEVELOPMENT_CORPUS.windows]
        index = ordered.index(start_ms)
        return SimpleNamespace(metrics=_metrics(-0.002 + index * 0.0001))


class _OrderFlowAdapter:
    def run(self, **kwargs: object) -> SimpleNamespace:
        spec = kwargs["strategy_spec"]
        params = kwargs["experiment_parameters"]
        start_ms = spec["dataset"]["start_ms"]  # type: ignore[index]
        ordered = [window.start_ms for window in DEFAULT_M5_DEVELOPMENT_CORPUS.windows]
        index = ordered.index(start_ms)
        baseline = -0.002 + index * 0.0001
        improvement = (
            0.0015
            if params.get("delta_ratio_threshold") == 0.2  # type: ignore[union-attr]
            else 0.0003
        )
        return SimpleNamespace(metrics=_metrics(baseline + improvement, trades=1))


def _materialization(tmp_path: Path) -> tuple[Path, Path]:
    dataset_root = tmp_path / "datasets"
    rows = []
    for window in DEFAULT_M5_DEVELOPMENT_CORPUS.windows:
        dataset = dataset_root / "m5_orderflow_dev" / f"{window.name}.csv"
        dataset.parent.mkdir(parents=True, exist_ok=True)
        dataset.write_text(f"window={window.name}\n", encoding="utf-8")
        rows.append(
            {
                "schema": CORPUS_WINDOW_RECEIPT_SCHEMA,
                "materialization_id": "m5corpusmat_test",
                "policy_id": DEFAULT_M5_STUDY_POLICY.policy_id,
                "corpus_id": DEFAULT_M5_DEVELOPMENT_CORPUS.corpus_id,
                "window_name": window.name,
                "start_ms": window.start_ms,
                "end_ms": window.end_ms,
                "orderflow_source": "archive",
                "workflow_id": f"workflow_{window.name}",
                "workflow_manifest_ref": f"workflow/{window.name}.json",
                "feature_dataset_id": f"dataset_{window.name}",
                "dataset_ref": str(dataset.relative_to(dataset_root)),
                "feature_csv_sha256": sha256_file(dataset),
            }
        )
    payload = {
        "schema": CORPUS_MATERIALIZATION_SCHEMA,
        "materialization_id": "m5corpusmat_test",
        "policy_id": DEFAULT_M5_STUDY_POLICY.policy_id,
        "corpus_id": DEFAULT_M5_DEVELOPMENT_CORPUS.corpus_id,
        "symbol": DEFAULT_M5_STUDY_POLICY.symbol,
        "venue": DEFAULT_M5_STUDY_POLICY.venue,
        "interval": DEFAULT_M5_STUDY_POLICY.interval,
        "price_bucket": 1.0,
        "namespace": "m5_orderflow_dev",
        "orderflow_source": "archive",
        "window_count": len(rows),
        "windows": rows,
        "frozen_oos_opened": False,
        "m5_frozen_oos_opened": False,
        "live_execution_allowed": False,
    }
    manifest = dataset_root / "m5_orderflow_dev" / "corpus" / "manifest.json"
    manifest.parent.mkdir(parents=True, exist_ok=True)
    manifest.write_text(json.dumps(payload), encoding="utf-8")
    return dataset_root, manifest


def test_multiwindow_evaluator_aggregates_12_windows_and_ranks_development_only(
    tmp_path: Path,
) -> None:
    dataset_root, manifest = _materialization(tmp_path)
    candidates = (
        M5MultiWindowCandidate(
            candidate_id="delta_020",
            parameters={"delta_ratio_threshold": 0.2},
        ),
        M5MultiWindowCandidate(
            candidate_id="stacked_1",
            parameters={"stacked_imbalance_threshold": 1},
        ),
    )

    report = evaluate_m5_multiwindow(
        materialization_manifest=manifest,
        dataset_root=dataset_root,
        candidates=candidates,
        baseline_adapter=_BaselineAdapter(),
        orderflow_adapter=_OrderFlowAdapter(),
    )

    assert report["windowCount"] == 12
    assert report["candidateCount"] == 2
    assert len(report["baseline"]["windows"]) == 12
    assert report["developmentRanking"][0]["candidateId"] == "delta_020"
    assert report["developmentRanking"][0]["aggregate"]["beatBaselineWindowCount"] == 12
    assert report["rankingIsDevelopmentOnly"] is True
    assert report["edgeClaimAllowed"] is False
    assert report["promotionAuthority"] is False
    assert report["frozenOosOpened"] is False
    assert report["m5FrozenOosOpened"] is False
    assert report["liveExecutionAllowed"] is False


def test_multiwindow_evaluator_fails_closed_on_dataset_tamper(tmp_path: Path) -> None:
    dataset_root, manifest = _materialization(tmp_path)
    first = dataset_root / "m5_orderflow_dev" / "dev-01.csv"
    first.write_text("tampered\n", encoding="utf-8")

    with pytest.raises(RuntimeError, match="dataset integrity mismatch"):
        evaluate_m5_multiwindow(
            materialization_manifest=manifest,
            dataset_root=dataset_root,
            candidates=(
                M5MultiWindowCandidate(
                    candidate_id="delta_020",
                    parameters={"delta_ratio_threshold": 0.2},
                ),
            ),
            baseline_adapter=_BaselineAdapter(),
            orderflow_adapter=_OrderFlowAdapter(),
        )


def test_multiwindow_evaluator_rejects_live_authority(tmp_path: Path) -> None:
    dataset_root, manifest = _materialization(tmp_path)
    payload = json.loads(manifest.read_text(encoding="utf-8"))
    payload["live_execution_allowed"] = True
    manifest.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(RuntimeError, match="cannot enable live execution"):
        evaluate_m5_multiwindow(
            materialization_manifest=manifest,
            dataset_root=dataset_root,
            candidates=(
                M5MultiWindowCandidate(
                    candidate_id="delta_020",
                    parameters={"delta_ratio_threshold": 0.2},
                ),
            ),
            baseline_adapter=_BaselineAdapter(),
            orderflow_adapter=_OrderFlowAdapter(),
        )


def test_candidate_loader_rejects_unknown_fields(tmp_path: Path) -> None:
    path = tmp_path / "candidates.json"
    path.write_text(
        json.dumps(
            {
                "schema": CANDIDATE_SET_SCHEMA,
                "candidates": [
                    {
                        "candidate_id": "bad",
                        "parameters": {"future_magic_threshold": 0.5},
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="unsupported candidate parameter fields"):
        load_m5_multiwindow_candidates(path)


def test_pre_registered_candidate_set_covers_all_existing_feature_families() -> None:
    candidates = load_m5_multiwindow_candidates("config/m5_multiwindow_candidate_set_v1.json")
    assert len(candidates) == 17
    fields = {field for candidate in candidates for field in candidate.parameters}
    assert fields == {
        "delta_ratio_threshold",
        "cvd_threshold",
        "stacked_imbalance_threshold",
        "absorption_threshold",
        "exhaustion_threshold",
        "price_delta_divergence_threshold",
    }
