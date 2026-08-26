from __future__ import annotations

import json
from pathlib import Path

import pytest

from eba_trader.m5_ablation_cli import emit_real_ablation_batch
from eba_trader.research_evidence import sha256_file
from eba_trader.research_store import ResearchStore


START_MS = 1_704_067_200_000
END_MS = START_MS + 600_000


def _fixture(tmp_path: Path) -> tuple[Path, Path, Path, Path]:
    dataset_root = tmp_path / "datasets"
    feature_dir = dataset_root / "m5_orderflow_dev" / "features"
    feature_dir.mkdir(parents=True)
    dataset = feature_dir / "off_fixture.csv"
    dataset.write_text("open_time_ms,close\n1704067200000,42000\n", encoding="utf-8")
    dataset_sha = sha256_file(dataset)

    feature_manifest = {
        "dataset_id": "off_fixture",
        "schema": "m5_orderflow_feature_dataset_v1",
        "symbol": "BTCUSDT",
        "interval": "1m",
        "start_ms": START_MS,
        "end_ms": END_MS,
        "row_count": 10,
        "price_bucket": 1.0,
        "venue": "usd_m_futures",
        "acquisition_id": "acq_fixture",
        "candle_sha256": "candle-sha",
        "orderflow_dataset_id": "ofd_fixture",
        "orderflow_records_sha256": "records-sha",
        "feature_csv_sha256": dataset_sha,
        "feature_csv_path": str(dataset),
    }
    dataset.with_suffix(".manifest.json").write_text(
        json.dumps(feature_manifest, sort_keys=True),
        encoding="utf-8",
    )

    workflow = {
        "workflow_id": "m5ds_fixture",
        "schema": "m5_usdm_feature_build_v1",
        "symbol": "BTCUSDT",
        "venue": "usd_m_futures",
        "interval": "1m",
        "start_ms": START_MS,
        "end_ms": END_MS,
        "price_bucket": 1.0,
        "candle_acquisition_id": "candle_acq_fixture",
        "candle_manifest_path": "unused-candle-manifest.json",
        "orderflow_dataset_id": "ofd_fixture",
        "orderflow_manifest_path": "unused-orderflow-manifest.json",
        "orderflow_acquisition_id": "acq_fixture",
        "orderflow_acquisition_path": "unused-acquisition.json",
        "feature_dataset_id": "off_fixture",
        "feature_manifest_path": str(dataset.with_suffix(".manifest.json")),
        "feature_csv_sha256": dataset_sha,
        "dataset_ref": "m5_orderflow_dev/features/off_fixture.csv",
    }
    workflow_path = tmp_path / "workflow.json"
    workflow_path.write_text(json.dumps(workflow, sort_keys=True), encoding="utf-8")

    gate_set = {
        "schema": "m5_orderflow_gate_set_v1",
        "gates": [
            {"delta_ratio_threshold": 0.05},
            {"delta_ratio_threshold": 0.10, "cvd_threshold": 0.0},
        ],
    }
    gates_path = tmp_path / "gates.json"
    gates_path.write_text(json.dumps(gate_set, sort_keys=True), encoding="utf-8")
    return dataset_root, workflow_path, gates_path, dataset


def _emit(tmp_path: Path) -> dict[str, object]:
    dataset_root, workflow_path, gates_path, _ = _fixture(tmp_path)
    return emit_real_ablation_batch(
        workflow_manifest_path=workflow_path,
        gates_path=gates_path,
        dataset_root=dataset_root,
        db_path=tmp_path / "research.db",
        fast_ema=12,
        slow_ema=26,
        initial_cash=10_000.0,
        fee_bps=4.0,
        slippage_bps=1.5,
    )


def test_real_ablation_cli_emits_deterministic_development_jobs(tmp_path: Path) -> None:
    first = _emit(tmp_path)
    second = emit_real_ablation_batch(
        workflow_manifest_path=tmp_path / "workflow.json",
        gates_path=tmp_path / "gates.json",
        dataset_root=tmp_path / "datasets",
        db_path=tmp_path / "research.db",
        fast_ema=12,
        slow_ema=26,
        initial_cash=10_000.0,
        fee_bps=4.0,
        slippage_bps=1.5,
    )

    assert first == second
    assert first["stage"] == "m5_orderflow_ablation_dev"
    assert first["treatment_count"] == 2
    assert len(first["experiment_ids"]) == 3
    assert first["frozen_oos_opened"] is False
    assert first["live_execution_allowed"] is False

    store = ResearchStore(tmp_path / "research.db")
    assert len(store.list_experiments()) == 3


def test_real_ablation_cli_rejects_tampered_feature_csv(tmp_path: Path) -> None:
    dataset_root, workflow_path, gates_path, dataset = _fixture(tmp_path)
    dataset.write_text("tampered\n", encoding="utf-8")

    with pytest.raises(ValueError, match="feature CSV hash mismatch"):
        emit_real_ablation_batch(
            workflow_manifest_path=workflow_path,
            gates_path=gates_path,
            dataset_root=dataset_root,
            db_path=tmp_path / "research.db",
            fast_ema=12,
            slow_ema=26,
            initial_cash=10_000.0,
            fee_bps=4.0,
            slippage_bps=1.5,
        )


def test_real_ablation_cli_rejects_wrong_venue_and_path_escape(tmp_path: Path) -> None:
    dataset_root, workflow_path, gates_path, _ = _fixture(tmp_path)
    workflow = json.loads(workflow_path.read_text(encoding="utf-8"))
    workflow["venue"] = "spot"
    workflow_path.write_text(json.dumps(workflow), encoding="utf-8")

    with pytest.raises(ValueError, match="requires USD-M futures"):
        emit_real_ablation_batch(
            workflow_manifest_path=workflow_path,
            gates_path=gates_path,
            dataset_root=dataset_root,
            db_path=tmp_path / "research.db",
            fast_ema=12,
            slow_ema=26,
            initial_cash=10_000.0,
            fee_bps=4.0,
            slippage_bps=1.5,
        )

    workflow["venue"] = "usd_m_futures"
    workflow["dataset_ref"] = "../escape.csv"
    workflow_path.write_text(json.dumps(workflow), encoding="utf-8")
    with pytest.raises(ValueError, match="escapes the configured dataset root"):
        emit_real_ablation_batch(
            workflow_manifest_path=workflow_path,
            gates_path=gates_path,
            dataset_root=dataset_root,
            db_path=tmp_path / "research.db",
            fast_ema=12,
            slow_ema=26,
            initial_cash=10_000.0,
            fee_bps=4.0,
            slippage_bps=1.5,
        )
