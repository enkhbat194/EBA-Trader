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
        '"m5_response_report_path": "m5-absorption-exhaustion-ablation-"',
        '"m5_report_all_passed": m5_report.get("allExperimentsPassed") is True',
        '"m5_report_treatments": isinstance(treatments, list) and len(treatments) == 4',
        '"m5_report_response_gates": response_gates == expected_response_gates',
    )
    for contract in required_checks:
        assert contract in text

    assert '"absorption_threshold": 0.1' in text
    assert '"absorption_threshold": 0.2' in text
    assert '"exhaustion_threshold": 0.01' in text
    assert '"exhaustion_threshold": 0.03' in text
    assert '"m5ResponseGates": response_gates' in text
    assert "deadline = time.time() + 900" in text
    assert "time.sleep(20)" in text
