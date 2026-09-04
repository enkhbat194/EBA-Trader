from __future__ import annotations

import json
from pathlib import Path

import pytest

from eba_trader.strategy_factory_v2_next_design import (
    DESIGN_AUTHORITY,
    EXPECTED_CAMPAIGN_ID,
    EXPECTED_FAMILY_IDS,
    load_next_campaign_design,
)

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "config" / "sfv2_next_campaign_design_v1.json"


def _payload() -> dict[str, object]:
    return json.loads(CONFIG.read_text(encoding="utf-8"))


def _write(tmp_path: Path, payload: dict[str, object]) -> Path:
    path = tmp_path / "design.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def test_canonical_next_campaign_design_is_design_only() -> None:
    design = load_next_campaign_design(CONFIG)
    assert design.authority == DESIGN_AUTHORITY
    assert design.enabled_for_evaluation is False
    assert design.campaign_id_reserved == EXPECTED_CAMPAIGN_ID
    assert design.raw_candidate_cap == 128
    assert design.candidate_cap_per_family == 32
    assert design.survivor_cap == 12
    assert design.family_ids == EXPECTED_FAMILY_IDS


def test_design_rejects_evaluation_authority(tmp_path: Path) -> None:
    payload = _payload()
    payload["enabled_for_evaluation"] = True
    with pytest.raises(ValueError, match="cannot authorize evaluation"):
        load_next_campaign_design(_write(tmp_path, payload))


def test_design_rejects_erasing_prior_search_history(tmp_path: Path) -> None:
    payload = _payload()
    history = dict(payload["search_history"])
    history["prior_inspected_candidate_count"] = 0
    payload["search_history"] = history
    with pytest.raises(ValueError, match="prior inspected candidate count changed"):
        load_next_campaign_design(_write(tmp_path, payload))


def test_design_rejects_claiming_unavailable_funding_data(tmp_path: Path) -> None:
    payload = _payload()
    data = dict(payload["data_policy"])
    data["historical_funding_available"] = True
    payload["data_policy"] = data
    with pytest.raises(ValueError, match="historical_funding_available"):
        load_next_campaign_design(_write(tmp_path, payload))


def test_design_rejects_opening_d1_or_sf4(tmp_path: Path) -> None:
    for field in ("d1_opened", "sf4_data_access_allowed"):
        payload = _payload()
        safety = dict(payload["safety"])
        safety[field] = True
        payload["safety"] = safety
        with pytest.raises(ValueError, match="safety boundary changed"):
            load_next_campaign_design(_write(tmp_path, payload))


def test_design_rejects_family_requesting_unavailable_data_plane(tmp_path: Path) -> None:
    payload = _payload()
    slots = [dict(item) for item in payload["family_slots"]]
    slots[0]["data_planes"] = ["historical_funding"]
    payload["family_slots"] = slots
    with pytest.raises(ValueError, match="unavailable data plane"):
        load_next_campaign_design(_write(tmp_path, payload))
