from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_m5_maintenance_runs_multiwindow_only_after_corpus_success() -> None:
    script = (ROOT / "scripts/run_m5_research_maintenance_once.sh").read_text(
        encoding="utf-8"
    )

    assert "multiwindow_exit=0" in script
    assert "-m eba_trader.m5_corpus_runtime" in script
    assert "if [[ $corpus_exit -eq 0 ]]" in script
    assert "-m eba_trader.m5_multiwindow_runtime" in script
    assert "multiwindow_exit=$?" in script
    assert "multiwindow_exit=1" in script
    assert "$multiwindow_exit -ne 0" in script
    assert "multiwindow=ok" in script
    assert "final-oos" not in script.lower()
    assert "order_send" not in script
    assert "place_order" not in script


def test_linode_bundle_checks_multiwindow_runtime_wiring() -> None:
    workflow = (ROOT / ".github/workflows/linode-production.yml").read_text(encoding="utf-8")

    assert "bash -n scripts/run_m5_research_maintenance_once.sh" in workflow
    assert "python -m py_compile scripts/collect_linode_proof.py" in workflow
    assert "grep -q 'm5_multiwindow_runtime' scripts/run_m5_research_maintenance_once.sh" in workflow


def test_production_collector_exposes_sanitized_development_only_multiwindow_status() -> None:
    collector = (ROOT / "scripts/collect_linode_proof.py").read_text(encoding="utf-8")

    assert 'M5_MULTIWINDOW_PROOF = RESEARCH_ROOT / "m5-multiwindow-evaluation-latest.json"' in collector
    assert "EXPECTED_M5_MULTIWINDOW_CANDIDATES = 17" in collector
    assert '"m5MultiWindow": _m5_multiwindow_status()' in collector
    assert 'proof["m5MultiWindow"]["safe"]' in collector
    assert 'report.get("candidateCount") == EXPECTED_M5_MULTIWINDOW_CANDIDATES' in collector
    assert 'report.get("rankingIsDevelopmentOnly") is True' in collector
    assert 'report.get("edgeClaimAllowed") is False' in collector
    assert 'report.get("promotionAuthority") is False' in collector
    assert 'report.get("frozenOosOpened") is False' in collector
    assert 'report.get("m5FrozenOosOpened") is False' in collector
    assert 'report.get("liveExecutionAllowed") is False' in collector
    assert '"developmentRanking": ranking' in collector
    assert '"expectedCandidateCount": EXPECTED_M5_MULTIWINDOW_CANDIDATES' in collector
