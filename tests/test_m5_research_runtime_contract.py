from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_research_worker_timer_is_bounded_and_persistent() -> None:
    service = (ROOT / "deploy/systemd/eba-research-worker.service").read_text(encoding="utf-8")
    timer = (ROOT / "deploy/systemd/eba-research-worker.timer").read_text(encoding="utf-8")

    assert "/var/lib/eba-trader/research/eba_research.db" in service
    assert "/var/lib/eba-trader/research/datasets" in service
    assert "/var/lib/eba-trader/research/evidence" in service
    assert "--max-jobs 8" in service
    assert "CPUQuota=50%" in service
    assert "MemoryMax=512M" in service
    assert "ReadWritePaths=/var/lib/eba-trader/research" in service
    assert "OnUnitActiveSec=1min" in timer
    assert "Persistent=true" in timer


def test_one_command_runner_keeps_research_only_guards() -> None:
    script = (ROOT / "scripts/run_m5_real_ablation.sh").read_text(encoding="utf-8")
    assert "eba-build-orderflow-features" in script
    assert "eba-m5-real-ablation" in script
    assert "eba-research-worker" in script
    assert "m5_orderflow_ablation_dev" in script
    assert "/var/lib/eba-trader/research" in script
    assert "--result-json" in script
    assert "m5_ablation_report" in script
    assert "Frozen OOS was not opened" in script
    assert "real execution remains locked" in script


def test_real_ablation_autorun_is_bounded_idempotent_and_development_only() -> None:
    wrapper = (ROOT / "scripts/run_m5_real_ablation_once.sh").read_text(encoding="utf-8")
    service = (ROOT / "deploy/systemd/eba-m5-real-ablation.service").read_text(
        encoding="utf-8"
    )
    timer = (ROOT / "deploy/systemd/eba-m5-real-ablation.timer").read_text(
        encoding="utf-8"
    )

    assert 'START="2026-08-01T00:00:00Z"' in wrapper
    assert 'END="2026-08-01T04:00:00Z"' in wrapper
    assert "m5-real-ablation-latest.json" in wrapper
    assert "allTerminal" in wrapper
    assert "evidenceComplete" in wrapper
    assert '"frozenOosOpened": False' in wrapper
    assert '"liveExecutionAllowed": False' in wrapper
    assert '"edgeClaimAllowed": False' in wrapper
    assert '"promotionAuthority": False' in wrapper
    assert "order_send" not in wrapper
    assert "place_order" not in wrapper

    assert "CPUQuota=40%" in service
    assert "MemoryMax=700M" in service
    assert "TimeoutStartSec=45min" in service
    assert "ReadWritePaths=/var/lib/eba-trader/research" in service
    assert "OnBootSec=4min" in timer
    assert "OnUnitInactiveSec=30min" in timer
    assert "Persistent=true" in timer


def test_linode_deploy_provisions_m5_autorun_without_touching_oos_lock() -> None:
    update = (ROOT / "scripts/update_linode_runtime.sh").read_text(encoding="utf-8")

    assert 'M5_ABLATION_SERVICE="eba-m5-real-ablation.service"' in update
    assert 'M5_ABLATION_TIMER="eba-m5-real-ablation.timer"' in update
    assert 'deploy/systemd/eba-m5-real-ablation.service' in update
    assert 'deploy/systemd/eba-m5-real-ablation.timer' in update
    assert '"$M5_ABLATION_TIMER"' in update
    assert "final-oos" not in update.lower()


def test_existing_linode_env_is_upgraded_without_overwrite() -> None:
    helper = (ROOT / "scripts/ensure_linode_research_env.sh").read_text(encoding="utf-8")
    update = (ROOT / "scripts/update_linode_runtime.sh").read_text(encoding="utf-8")

    assert 'grep -q "^${key}="' in helper
    assert "EBA_RESEARCH_DB" in helper
    assert "EBA_RESEARCH_DATASET_ROOT" in helper
    assert "EBA_RESEARCH_EVIDENCE_ROOT" in helper
    assert "bash scripts/ensure_linode_research_env.sh" in update
