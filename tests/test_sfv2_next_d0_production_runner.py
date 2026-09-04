from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_next_d0_service_is_bounded_and_local_only() -> None:
    service = (
        ROOT / "deploy/systemd/eba-sfv2-next-d0-materialization.service"
    ).read_text(encoding="utf-8")
    assert "Type=oneshot" in service
    assert "run_sfv2_next_d0_materialization.sh" in service
    assert "CPUQuota=45%" in service
    assert "MemoryMax=2G" in service
    assert "TimeoutStartSec=50min" in service
    assert "ReadWritePaths=/var/lib/eba-trader/research" in service
    assert "NoNewPrivileges=true" in service


def test_next_d0_wrapper_uses_shared_lock_and_pinned_builder_contract() -> None:
    script = (ROOT / "scripts/run_sfv2_next_d0_materialization.sh").read_text(
        encoding="utf-8"
    )
    assert "/run/lock/eba-trader-runtime-mutation.lock" in script
    assert "flock -n 9" in script
    assert "sha256_text(canonical_json(identity))" in script
    assert "strategy_factory_v2_next_dataset_workflow.py" in script
    assert "orderflow_archive.py" in script
    assert "git rev-parse HEAD" not in script
    assert "run_sfv2_next_d0_materialization.py" in script
    assert "backtest" not in script.lower()
    assert "frozen-oos" not in script.lower()


def test_auto_updater_starts_next_d0_only_after_first_d0_is_complete() -> None:
    script = (ROOT / "scripts/auto_update_entrypoint.sh").read_text(encoding="utf-8")
    assert 'SFV2_NEXT_SERVICE="eba-sfv2-next-d0-materialization.service"' in script
    assert '[[ "$SFV2_COMPLETE" == "1" && "$SFV2_NEXT_COMPLETE" != "1"' in script
    assert "completedWindowCount\") == 10" in script
    assert "performanceEvaluationAllowed\") is False" in script
    assert "sf4DataAccessAllowed\") is False" in script
    assert "systemctl start --no-block \"$SFV2_NEXT_SERVICE\"" in script


def test_progress_proof_surfaces_service_state_without_mutation_authority() -> None:
    workflow = (
        ROOT / ".github/workflows/sfv2-next-d0-progress-proof.yml"
    ).read_text(encoding="utf-8")
    assert 'service_state = next_d0.get("serviceState")' in workflow
    assert 'active_state == "failed"' in workflow
    assert 'exec_status != 0' in workflow
    assert '"serviceState": service_state' in workflow
    assert "systemctl start" not in workflow
    assert "performanceEvaluationAllowed" in workflow
    assert "realExecutionAllowed" in workflow
