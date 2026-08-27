from __future__ import annotations

import json
from pathlib import Path

from eba_trader.production_proof import read_production_proof

ROOT = Path(__file__).resolve().parents[1]


def test_missing_proof_is_explicitly_unavailable(tmp_path: Path) -> None:
    result = read_production_proof(tmp_path / "missing.json")

    assert result["ok"] is True
    assert result["available"] is False
    assert result["localContractPassed"] is False
    assert result["productionSmokePassed"] is False
    assert result["liveExecutionAllowed"] is False


def test_reader_strips_secrets_and_session_tokens_but_keeps_masked_key(tmp_path: Path) -> None:
    path = tmp_path / "proof.json"
    path.write_text(
        json.dumps(
            {
                "schemaVersion": 1,
                "localContractPassed": True,
                "productionSmokePassed": True,
                "demoReconnect": {
                    "passed": True,
                    "maskedApiKey": "••••D2q5",
                    "apiKey": "must-not-leak",
                    "apiSecret": "must-not-leak",
                    "sessionToken": "must-not-leak",
                    "credentials": {"secret": "must-not-leak"},
                },
            }
        ),
        encoding="utf-8",
    )

    result = read_production_proof(path)

    assert result["available"] is True
    assert result["productionSmokePassed"] is True
    reconnect = result["demoReconnect"]
    assert reconnect["maskedApiKey"] == "••••D2q5"
    assert "apiKey" not in reconnect
    assert "apiSecret" not in reconnect
    assert "sessionToken" not in reconnect
    assert "credentials" not in reconnect
    assert result["liveExecutionAllowed"] is False


def test_linode_deploy_collects_proof_without_making_m5_completion_a_gate() -> None:
    install = (ROOT / "scripts/install_linode_runtime.sh").read_text(encoding="utf-8")
    update = (ROOT / "scripts/update_linode_runtime.sh").read_text(encoding="utf-8")
    collector = (ROOT / "scripts/collect_linode_proof.py").read_text(encoding="utf-8")

    for script in (install, update):
        assert "/var/lib/eba-trader" in script
        assert 'PROOF_DIR="$STATE_DIR/proofs"' in script
        assert "scripts/collect_linode_proof.py" in script
        assert "--expected-build" in script

    assert "SystemMaxUse" in collector
    assert "SystemKeepFree" in collector
    assert "MaxRetentionSec" in collector
    assert "/api/demo/autoconnect" in collector
    assert "/api/research/status" in collector
    assert "/api/v1/positions" in collector
    assert "/api/chart" in collector
    assert "session token returned by the autoconnect endpoint" in collector
    assert "m5-real-ablation-latest.json" in collector
    assert "eba-m5-real-ablation.timer" in collector
    assert '"edgeClaimAllowed": False' in collector
    assert '"promotionAuthority": False' in collector
    assert '"m5RealAblation": _m5_ablation_status()' in collector
    assert 'proof["m5RealAblation"]["safe"]' in collector
    assert 'proof["m5RealAblation"]["phase"] == "COMPLETE"' not in collector


def test_research_ui_renders_production_proof_read_only() -> None:
    source = (ROOT / "web/research_ui.js").read_text(encoding="utf-8")

    assert "Linode runtime verification" in source
    assert "productionSmokePassed" in source
    assert "demoReconnect" in source
    assert "productionPositionsProof" in source
    assert "systemctl" not in source
