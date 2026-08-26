from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_journald_limits_are_versioned_and_deployed() -> None:
    config = (ROOT / "deploy/journald/eba-trader.conf").read_text(encoding="utf-8")
    assert "SystemMaxUse=250M" in config
    assert "SystemKeepFree=1G" in config
    assert "MaxRetentionSec=7day" in config

    for script_name in ("install_linode_runtime.sh", "update_linode_runtime.sh"):
        script = (ROOT / "scripts" / script_name).read_text(encoding="utf-8")
        assert "deploy/journald/eba-trader.conf" in script
        assert "systemctl restart systemd-journald" in script


def test_linode_deploy_provisions_persistent_research_paths() -> None:
    install = (ROOT / "scripts/install_linode_runtime.sh").read_text(encoding="utf-8")
    update = (ROOT / "scripts/update_linode_runtime.sh").read_text(encoding="utf-8")

    for script in (install, update):
        assert "/var/lib/eba-trader" in script
        assert 'RESEARCH_DIR="$STATE_DIR/research"' in script
        assert 'RESEARCH_DATASET_DIR="$RESEARCH_DIR/datasets"' in script
        assert 'RESEARCH_EVIDENCE_DIR="$RESEARCH_DIR/evidence"' in script

    assert "EBA_RESEARCH_DB=/var/lib/eba-trader/research/eba_research.db" in install
    assert "EBA_RESEARCH_DATASET_ROOT=/var/lib/eba-trader/research/datasets" in install
    assert "EBA_RESEARCH_EVIDENCE_ROOT=/var/lib/eba-trader/research/evidence" in install
