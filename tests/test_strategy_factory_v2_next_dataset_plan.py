from __future__ import annotations

import json
from pathlib import Path

import pytest

from eba_trader.history import parse_utc
from eba_trader.strategy_factory_v2_next_dataset_plan import (
    load_next_d0_dataset_plan,
)

PLAN_PATH = Path("config/sfv2_next_d0_dataset_plan_v1.json")
INVENTORY_PATH = Path("config/sfv2_historical_window_inventory_v1.json")


def test_next_d0_dataset_plan_freezes_safe_pre_sf4_windows() -> None:
    plan = load_next_d0_dataset_plan(PLAN_PATH, inventory_path=INVENTORY_PATH)
    assert plan.authority == "DATASET_PLAN_FREEZE_ONLY"
    assert plan.provenance_class == "D0_DISCOVERY_ONLY_NOT_CONFIRMATION"
    assert plan.performance_evaluation_allowed is False
    assert plan.dataset_receipt_frozen is False
    assert plan.orderflow_source == "archive"
    assert len(plan.windows) == 10

    first = plan.windows[0]
    last = plan.windows[-1]
    assert first.start_ms == parse_utc("2026-08-22T00:15:00Z")
    assert first.required_orderflow_start_ms == parse_utc("2026-08-22T00:14:00Z")
    assert first.required_orderflow_start_ms >= parse_utc("2026-08-22T00:00:00Z")
    assert last.end_ms == parse_utc("2026-09-01T00:00:00Z")


def test_next_d0_windows_are_contiguous_after_deliberate_first_offset() -> None:
    plan = load_next_d0_dataset_plan(PLAN_PATH, inventory_path=INVENTORY_PATH)
    assert plan.windows[0].end_ms == plan.windows[1].start_ms
    for previous, current in zip(plan.windows[1:], plan.windows[2:], strict=False):
        assert previous.end_ms == current.start_ms


def test_dataset_plan_cannot_move_into_m5_frozen_oos(tmp_path: Path) -> None:
    payload = json.loads(PLAN_PATH.read_text(encoding="utf-8"))
    payload["windows"][0]["start"] = "2026-08-21T23:45:00Z"
    path = tmp_path / "plan.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(ValueError, match="windows changed"):
        load_next_d0_dataset_plan(path, inventory_path=INVENTORY_PATH)


def test_dataset_plan_cannot_enter_sf4(tmp_path: Path) -> None:
    payload = json.loads(PLAN_PATH.read_text(encoding="utf-8"))
    payload["windows"][-1]["end"] = "2026-09-01T00:01:00Z"
    path = tmp_path / "plan.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(ValueError, match="windows changed"):
        load_next_d0_dataset_plan(path, inventory_path=INVENTORY_PATH)


def test_dataset_plan_cannot_switch_to_rest_post_hoc(tmp_path: Path) -> None:
    payload = json.loads(PLAN_PATH.read_text(encoding="utf-8"))
    payload["orderflow_source"] = "rest"
    path = tmp_path / "plan.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(ValueError, match="order-flow source changed"):
        load_next_d0_dataset_plan(path, inventory_path=INVENTORY_PATH)


def test_dataset_plan_cannot_claim_confirmation_or_open_evaluation(tmp_path: Path) -> None:
    payload = json.loads(PLAN_PATH.read_text(encoding="utf-8"))
    payload["materialization"]["performance_evaluation_allowed"] = True
    path = tmp_path / "plan.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(ValueError, match="materialization boundary changed"):
        load_next_d0_dataset_plan(path, inventory_path=INVENTORY_PATH)


def test_dataset_plan_is_bound_to_frozen_candidate_catalog(tmp_path: Path) -> None:
    payload = json.loads(PLAN_PATH.read_text(encoding="utf-8"))
    payload["catalog_sha256"] = "0" * 64
    path = tmp_path / "plan.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(ValueError, match="catalog binding changed"):
        load_next_d0_dataset_plan(path, inventory_path=INVENTORY_PATH)
