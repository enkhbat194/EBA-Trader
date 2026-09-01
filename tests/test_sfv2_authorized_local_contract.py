from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_local_authorization_is_discovery_only_and_single_use() -> None:
    payload = json.loads(
        (ROOT / "config/sfv2_d0_production_authorization_v1.json").read_text(
            encoding="utf-8"
        )
    )
    assert payload["enabled"] is True
    assert payload["single_use"] is True
    assert payload["authority"] == "DISCOVERY_ONLY"
    assert payload["expected_candidate_count"] == 406
    assert payload["expected_stratum_count"] == 12
    assert payload["safety"]["public_trigger_allowed"] is False
    assert payload["safety"]["d1_opened"] is False
    assert payload["safety"]["frozen_oos_opened"] is False
    assert payload["safety"]["live_execution_allowed"] is False
    assert payload["safety"]["real_execution_allowed"] is False


def test_root_side_wrapper_uses_shared_checkout_lock_and_no_network_command() -> None:
    wrapper = (ROOT / "scripts/run_sfv2_d0_authorized_production.sh").read_text(
        encoding="utf-8"
    )
    assert "eba-trader-runtime-mutation.lock" in wrapper
    assert "run_sfv2_d0_authorized_until_frozen.py" in wrapper
    assert "curl " not in wrapper
    assert "wget " not in wrapper


def test_existing_research_maintenance_calls_authorized_wrapper() -> None:
    maintenance = (ROOT / "scripts/run_m5_research_maintenance_once.sh").read_text(
        encoding="utf-8"
    )
    assert "run_sfv2_d0_authorized_production.sh" in maintenance
    assert "sfv2_exit" in maintenance
    assert "sfv2_state" in maintenance
    assert "deferred_checkout_lock" in maintenance
