from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from eba_trader.research_evidence import sha256_file
from eba_trader.sfv2_next_d0_dashboard import read_sfv2_next_d0_materialization_summary
from eba_trader.strategy_factory_v2_next_materialization import (
    EXPECTED_CATALOG_SHA256,
    EXPECTED_PLAN_SHA256,
    load_next_d0_materialization_authorization,
    run_next_d0_materialization_cycle,
)

ROOT = Path(__file__).resolve().parents[1]
AUTH = ROOT / "config/sfv2_next_d0_materialization_authorization_v1.json"
PLAN = ROOT / "config/sfv2_next_d0_dataset_plan_v1.json"
INVENTORY = ROOT / "config/sfv2_historical_window_inventory_v1.json"
SOURCE_SHA = "a" * 40


def _fake_builder(calls: list[str]):
    def build(*, window_name, dataset_root, plan_path, inventory_path):
        del plan_path, inventory_path
        calls.append(window_name)
        root = Path(dataset_root)
        feature_dir = root / "sfv2_next_d0_low_turnover_v1" / "features"
        workflow_dir = root / "sfv2_next_d0_low_turnover_v1" / "workflow"
        feature_dir.mkdir(parents=True, exist_ok=True)
        workflow_dir.mkdir(parents=True, exist_ok=True)
        dataset_ref = f"sfv2_next_d0_low_turnover_v1/features/{window_name}.csv"
        feature_path = root / dataset_ref
        feature_path.write_text(f"window={window_name}\n", encoding="utf-8")
        workflow_path = workflow_dir / f"{window_name}.json"
        workflow_path.write_text("{}", encoding="utf-8")
        index = int(window_name.rsplit("-", 1)[-1])
        manifest = SimpleNamespace(
            window_name=window_name,
            workflow_id=f"workflow-{window_name}",
            feature_dataset_id=f"feature-{window_name}",
            feature_csv_sha256=sha256_file(feature_path),
            dataset_ref=dataset_ref,
            row_count=1425 if index == 1 else 1440,
            start_ms=index * 1000,
            end_ms=index * 1000 + 500,
            required_orderflow_start_ms=index * 1000 - 60,
            candle_acquisition_id=f"candle-{window_name}",
            orderflow_dataset_id=f"flow-dataset-{window_name}",
            orderflow_acquisition_id=f"flow-acquisition-{window_name}",
        )
        return manifest, workflow_path

    return build


def test_authorization_and_plan_sha_are_exactly_frozen() -> None:
    authorization = load_next_d0_materialization_authorization(AUTH)
    assert authorization.max_windows_per_invocation == 1
    assert sha256_file(PLAN) == EXPECTED_PLAN_SHA256
    assert EXPECTED_CATALOG_SHA256 == (
        "0aa793ca70ba8719486ba6edae314c77803e1b87884665d17ec88019ec71654a"
    )


def test_materializer_builds_exactly_one_window_per_invocation(tmp_path: Path) -> None:
    calls: list[str] = []
    status = tmp_path / "status.json"
    dataset_root = tmp_path / "datasets"
    payload = run_next_d0_materialization_cycle(
        authorization_path=AUTH,
        plan_path=PLAN,
        inventory_path=INVENTORY,
        dataset_root=dataset_root,
        status_path=status,
        source_code_sha=SOURCE_SHA,
        build_window=_fake_builder(calls),
    )
    assert calls == ["next-d0-01"]
    assert payload["phase"] == "IN_PROGRESS"
    assert payload["completedWindowCount"] == 1
    assert payload["nextWindowName"] == "next-d0-02"
    assert payload["datasetBundleSha256"] is None
    assert payload["performanceEvaluationAllowed"] is False
    assert payload["d1Opened"] is False
    assert payload["frozenOosOpened"] is False
    assert payload["sf4DataAccessAllowed"] is False
    assert payload["realExecutionAllowed"] is False


def test_materializer_freezes_bundle_only_after_all_ten_windows(tmp_path: Path) -> None:
    calls: list[str] = []
    status = tmp_path / "status.json"
    dataset_root = tmp_path / "datasets"
    payload = None
    for _ in range(10):
        payload = run_next_d0_materialization_cycle(
            authorization_path=AUTH,
            plan_path=PLAN,
            inventory_path=INVENTORY,
            dataset_root=dataset_root,
            status_path=status,
            source_code_sha=SOURCE_SHA,
            build_window=_fake_builder(calls),
        )
    assert payload is not None
    assert payload["phase"] == "COMPLETE"
    assert payload["completedWindowCount"] == 10
    assert payload["nextWindowName"] is None
    assert isinstance(payload["datasetBundleSha256"], str)
    assert len(payload["datasetBundleSha256"]) == 64
    assert calls == [f"next-d0-{index:02d}" for index in range(1, 11)]

    replay = run_next_d0_materialization_cycle(
        authorization_path=AUTH,
        plan_path=PLAN,
        inventory_path=INVENTORY,
        dataset_root=dataset_root,
        status_path=status,
        source_code_sha=SOURCE_SHA,
        build_window=_fake_builder(calls),
    )
    assert replay == payload
    assert calls == [f"next-d0-{index:02d}" for index in range(1, 11)]

    public = read_sfv2_next_d0_materialization_summary(status)
    assert public["available"] is True
    assert public["phase"] == "COMPLETE"
    assert public["completedWindowCount"] == 10
    assert public["performanceEvaluationAllowed"] is False
    assert public["verificationAuthority"] is False


def test_materializer_rejects_source_code_change_mid_freeze(tmp_path: Path) -> None:
    calls: list[str] = []
    status = tmp_path / "status.json"
    dataset_root = tmp_path / "datasets"
    run_next_d0_materialization_cycle(
        authorization_path=AUTH,
        plan_path=PLAN,
        inventory_path=INVENTORY,
        dataset_root=dataset_root,
        status_path=status,
        source_code_sha=SOURCE_SHA,
        build_window=_fake_builder(calls),
    )
    with pytest.raises(RuntimeError, match="source code changed"):
        run_next_d0_materialization_cycle(
            authorization_path=AUTH,
            plan_path=PLAN,
            inventory_path=INVENTORY,
            dataset_root=dataset_root,
            status_path=status,
            source_code_sha="b" * 40,
            build_window=_fake_builder(calls),
        )
    assert calls == ["next-d0-01"]


def test_authorization_cannot_enable_evaluation(tmp_path: Path) -> None:
    payload = json.loads(AUTH.read_text(encoding="utf-8"))
    payload["safety"]["performance_evaluation_allowed"] = True
    changed = tmp_path / "authorization.json"
    changed.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(ValueError, match="safety boundary"):
        load_next_d0_materialization_authorization(changed)


def test_dashboard_rejects_status_that_opens_frozen_oos(tmp_path: Path) -> None:
    calls: list[str] = []
    status = tmp_path / "status.json"
    dataset_root = tmp_path / "datasets"
    run_next_d0_materialization_cycle(
        authorization_path=AUTH,
        plan_path=PLAN,
        inventory_path=INVENTORY,
        dataset_root=dataset_root,
        status_path=status,
        source_code_sha=SOURCE_SHA,
        build_window=_fake_builder(calls),
    )
    payload = json.loads(status.read_text(encoding="utf-8"))
    payload["frozenOosOpened"] = True
    status.write_text(json.dumps(payload), encoding="utf-8")
    public = read_sfv2_next_d0_materialization_summary(status)
    assert public["available"] is False
    assert public["reason"] == "status_safety_rejected"
