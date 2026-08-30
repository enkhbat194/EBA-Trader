from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github/workflows/production-proof.yml"


def test_external_production_proof_requires_terminal_m5_evidence() -> None:
    text = WORKFLOW.read_text(encoding="utf-8")

    required_checks = (
        '"m5_complete": m5.get("phase") == "COMPLETE"',
        '"m5_safe": m5.get("safe") is True',
        '"m5_all_terminal": m5.get("allTerminal") is True',
        '"m5_evidence_complete": m5.get("evidenceComplete") is True',
        '"m5_frozen_oos_closed": m5.get("frozenOosOpened") is False',
        '"m5_live_execution_locked": m5.get("liveExecutionAllowed") is False',
        '"m5_divergence_report_path": "m5-price-delta-divergence-ablation-"',
        '"m5_report_all_passed": m5_report.get("allExperimentsPassed") is True',
        '"m5_report_treatments": isinstance(treatments, list) and len(treatments) == 3',
        '"m5_report_divergence_gates": divergence_gates == expected_divergence_gates',
    )
    for contract in required_checks:
        assert contract in text

    assert '"price_delta_divergence_threshold": 0.01' in text
    assert '"price_delta_divergence_threshold": 0.05' in text
    assert '"price_delta_divergence_threshold": 0.1' in text
    assert '"m5DivergenceGates": divergence_gates' in text
    assert "deadline = time.time() + 900" in text
    assert "time.sleep(20)" in text


def test_external_production_proof_preserves_strict_sf1_contract() -> None:
    text = WORKFLOW.read_text(encoding="utf-8")

    required_checks = (
        '"sf1_candidate_count": sf1.get("candidateCount") == 48',
        '"sf1_search_budget": sf1.get("multipleTestingBudget") == 48',
        '"sf1_window_count": sf1.get("windowCount") == 12',
        '"sf1_development_only": sf1.get("developmentEvidenceOnly") is True',
        '"sf1_no_edge_claim": sf1.get("edgeClaimAllowed") is False',
        '"sf1_no_promotion": sf1.get("promotionAuthority") is False',
        '"sf1_frozen_oos_closed": sf1.get("frozenOosOpened") is False',
        '"sf1_m5_frozen_oos_closed": sf1.get("m5FrozenOosOpened") is False',
        '"sf1_live_locked": sf1.get("liveExecutionAllowed") is False',
    )
    for contract in required_checks:
        assert contract in text
