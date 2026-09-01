from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ENTRYPOINT = ROOT / "scripts" / "auto_update_entrypoint.sh"
SERVICE = ROOT / "deploy" / "systemd" / "eba-sfv2-d0-authorized.service"
AUTHORIZATION = ROOT / "config" / "sfv2_d0_production_authorization_v1.json"


def test_dedicated_trigger_is_local_root_only_and_releases_checkout_lock_first() -> None:
    text = ENTRYPOINT.read_text(encoding="utf-8")
    assert 'SFV2_SERVICE="eba-sfv2-d0-authorized.service"' in text
    assert 'SFV2_RUNNER="$REPO_DIR/scripts/run_sfv2_d0_authorized_production.sh"' in text
    unlock = text.index("flock -u 9")
    start = text.index('systemctl start --no-block "$SFV2_SERVICE"')
    assert unlock < start
    assert "curl " not in text
    assert "workflow_dispatch" not in text


def test_dedicated_service_runs_only_the_authorized_wrapper_with_resource_bounds() -> None:
    text = SERVICE.read_text(encoding="utf-8")
    assert "User=root" in text
    assert "Group=root" in text
    assert (
        "ExecStart=/bin/bash /opt/Eba-Trader/scripts/"
        "run_sfv2_d0_authorized_production.sh"
    ) in text
    assert "CPUQuota=50%" in text
    assert "MemoryMax=1G" in text
    assert "TimeoutStartSec=35min" in text
    assert "NoNewPrivileges=true" in text
    assert "ProtectSystem=full" in text
    assert "ReadWritePaths=/var/lib/eba-trader/research" in text


def test_authorization_still_forbids_public_and_downstream_authority() -> None:
    payload = json.loads(AUTHORIZATION.read_text(encoding="utf-8"))
    assert payload["request_id"] == "sfv2-d0-prod-20260901-v1"
    assert payload["single_use"] is True
    assert payload["authority"] == "DISCOVERY_ONLY"
    assert payload["safety"] == {
        "fresh_confirmation_evidence": False,
        "verification_authority": False,
        "d1_opened": False,
        "frozen_oos_opened": False,
        "demo_promotion_allowed": False,
        "live_execution_allowed": False,
        "real_execution_allowed": False,
        "public_trigger_allowed": False,
    }
