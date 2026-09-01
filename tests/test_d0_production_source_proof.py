from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_d0_production_source_workflow_is_observational_and_discovery_only() -> None:
    workflow = (ROOT / ".github/workflows/d0-production-source-proof.yml").read_text(
        encoding="utf-8"
    )

    assert "/api/app-info" in workflow
    assert "/api/research/status" in workflow
    assert 'd0.get("authority") == "DISCOVERY_ONLY"' in workflow
    assert "INSPECTED_REUSABLE_DISCOVERY_DATA" in workflow
    assert 'd0.get("freshConfirmationEvidence") is False' in workflow
    assert 'd0.get("verificationAuthority") is False' in workflow
    assert 'd0.get("d1Opened") is False' in workflow
    assert 'd0.get("frozenOosOpened") is False' in workflow
    assert 'd0.get("liveExecutionAllowed") is False' in workflow
    assert 'd0.get("sourceKind")' in workflow
    assert 'd0.get("datasetSha256")' in workflow
    assert '"ready": ready' in workflow
    assert '"blocked": not ready' in workflow
    assert "materialize_m5_development_corpus" not in workflow
    assert "build_usdm_orderflow_feature_dataset" not in workflow
    assert "apiSecret" not in workflow
    assert "sessionToken" not in workflow
