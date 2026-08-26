from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_auto_update_service_uses_diagnostic_wrapper() -> None:
    service = (ROOT / "deploy/systemd/eba-auto-update.service").read_text(encoding="utf-8")
    wrapper = (ROOT / "scripts/auto_update_entrypoint.sh").read_text(encoding="utf-8")

    assert "ExecStart=/usr/bin/bash /opt/Eba-Trader/scripts/auto_update_entrypoint.sh" in service
    assert "TimeoutStartSec=15min" in service
    assert "last_attempt_at" in wrapper
    assert "last_output.log" in wrapper
    assert "last_error" in wrapper
    assert "update_linode_runtime.sh" in wrapper


def test_repair_helper_is_fail_closed_on_dirty_checkout() -> None:
    repair = (ROOT / "scripts/repair_linode_auto_update.sh").read_text(encoding="utf-8")

    assert "git status --porcelain" in repair
    assert "Refusing destructive repair" in repair
    assert "dirty-checkout.txt" in repair
    assert "raw.githubusercontent.com/enkhbat194/EBA-Trader/main" in repair
    assert "systemctl enable --now" in repair
    assert "api/app-info" in repair
