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
    )
    for contract in required_checks:
        assert contract in text

    assert "deadline = time.time() + 900" in text
    assert "time.sleep(20)" in text
