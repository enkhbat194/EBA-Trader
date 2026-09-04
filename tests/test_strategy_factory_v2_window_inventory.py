from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

import pytest

from eba_trader.strategy_factory_v2_window_inventory import (
    assert_discovery_window_allowed,
    assert_no_known_research_overlap,
    load_historical_window_inventory,
)

INVENTORY_PATH = Path("config/sfv2_historical_window_inventory_v1.json")


def _ms(value: str) -> int:
    text = value[:-1] + "+00:00" if value.endswith("Z") else value
    return int(datetime.fromisoformat(text).astimezone(UTC).timestamp() * 1000)


def test_inventory_freezes_all_known_research_boundaries() -> None:
    inventory = load_historical_window_inventory(INVENTORY_PATH)
    assert inventory.authority == "RESEARCH_BOUNDARY_ONLY"
    assert len(inventory.ranges) == 40

    classifications = [item.classification for item in inventory.ranges]
    assert classifications.count("INSPECTED") == 36
    assert classifications.count("INSPECTED_QUARANTINE") == 1
    assert classifications.count("FROZEN_OOS") == 2
    assert classifications.count("PROTECTED_SF4") == 1

    ids = {item.range_id for item in inventory.ranges}
    assert {f"m5-dev-{index:02d}" for index in range(1, 13)} <= ids
    assert {f"sf2-dev-{index:02d}" for index in range(1, 13)} <= ids
    assert {f"sf3-dev-{index:02d}" for index in range(1, 13)} <= ids


def test_inspected_reuse_must_be_explicit_and_is_returned_for_provenance() -> None:
    inventory = load_historical_window_inventory(INVENTORY_PATH)
    start = _ms("2026-07-02T01:00:00Z")
    end = _ms("2026-07-02T02:00:00Z")

    with pytest.raises(RuntimeError, match="without explicit reuse"):
        assert_discovery_window_allowed(inventory, start_ms=start, end_ms=end)

    conflicts = assert_discovery_window_allowed(
        inventory,
        start_ms=start,
        end_ms=end,
        allow_inspected_reuse=True,
    )
    assert [item.range_id for item in conflicts] == ["m5-dev-01"]


def test_original_smoke_day_is_conservatively_quarantined() -> None:
    inventory = load_historical_window_inventory(INVENTORY_PATH)
    start = _ms("2026-08-01T12:00:00Z")
    end = _ms("2026-08-01T13:00:00Z")
    with pytest.raises(RuntimeError, match="original-smoke-2026-08-01-quarantine"):
        assert_discovery_window_allowed(inventory, start_ms=start, end_ms=end)


def test_m5_frozen_oos_is_absolute_block_even_for_inspected_reuse() -> None:
    inventory = load_historical_window_inventory(INVENTORY_PATH)
    with pytest.raises(RuntimeError, match="m5-frozen-oos-2026"):
        assert_discovery_window_allowed(
            inventory,
            start_ms=_ms("2026-08-16T00:00:00Z"),
            end_ms=_ms("2026-08-17T00:00:00Z"),
            allow_inspected_reuse=True,
        )


def test_first_cycle_2025_frozen_oos_is_absolute_block() -> None:
    inventory = load_historical_window_inventory(INVENTORY_PATH)
    with pytest.raises(RuntimeError, match="first-cycle-frozen-oos-2025"):
        assert_discovery_window_allowed(
            inventory,
            start_ms=_ms("2025-06-01T00:00:00Z"),
            end_ms=_ms("2025-06-02T00:00:00Z"),
            allow_inspected_reuse=True,
        )


def test_sf4_prospective_interval_is_absolute_block() -> None:
    inventory = load_historical_window_inventory(INVENTORY_PATH)
    with pytest.raises(RuntimeError, match="sf4-prospective-replication"):
        assert_discovery_window_allowed(
            inventory,
            start_ms=_ms("2026-09-04T00:00:00Z"),
            end_ms=_ms("2026-09-05T00:00:00Z"),
            allow_inspected_reuse=True,
        )


def test_unlisted_forward_range_only_proves_no_known_overlap() -> None:
    inventory = load_historical_window_inventory(INVENTORY_PATH)
    start = _ms("2026-08-22T00:00:00Z")
    end = _ms("2026-08-23T00:00:00Z")
    assert assert_discovery_window_allowed(inventory, start_ms=start, end_ms=end) == ()
    assert_no_known_research_overlap(inventory, start_ms=start, end_ms=end)


def test_known_overlap_can_never_be_called_clean_by_no_overlap_helper() -> None:
    inventory = load_historical_window_inventory(INVENTORY_PATH)
    with pytest.raises(RuntimeError, match="sf3-dev-12"):
        assert_no_known_research_overlap(
            inventory,
            start_ms=_ms("2026-08-14T09:00:00Z"),
            end_ms=_ms("2026-08-14T10:00:00Z"),
        )


def test_sf4_hard_boundary_cannot_be_shortened(tmp_path: Path) -> None:
    payload = json.loads(INVENTORY_PATH.read_text(encoding="utf-8"))
    for row in payload["ranges"]:
        if row["range_id"] == "sf4-prospective-replication":
            row["end"] = "2026-09-12T00:00:00Z"
            break
    path = tmp_path / "inventory.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(ValueError, match="hard boundary changed"):
        load_historical_window_inventory(path)


def test_safety_rules_cannot_be_weakened(tmp_path: Path) -> None:
    payload = json.loads(INVENTORY_PATH.read_text(encoding="utf-8"))
    payload["rules"]["inspected_reuse_must_be_explicit"] = False
    path = tmp_path / "inventory.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(ValueError, match="safety rules changed"):
        load_historical_window_inventory(path)
