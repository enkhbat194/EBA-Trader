from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_maintenance_qualifies_before_candidate_specific_robustness() -> None:
    script = (ROOT / "scripts/run_m5_research_maintenance_once.sh").read_text(
        encoding="utf-8"
    )

    qualification = "-m eba_trader.m5_candidate_qualification_runtime"
    robustness = "-m eba_trader.m5_absorption_robustness_runtime"
    multiwindow = "-m eba_trader.m5_multiwindow_runtime"

    assert multiwindow in script
    assert qualification in script
    assert robustness in script
    assert script.index(multiwindow) < script.index(qualification) < script.index(robustness)
    assert "m5-robustness-qualification-latest.json" in script
    assert 'if [[ "$eligible_count" == "0" ]]' in script
    assert 'robustness_state="skipped_no_eligible_candidate"' in script
    assert 'if [[ "$top_candidate" == "absorption_020" ]]' in script
    assert "blocked_candidate_runner_mismatch" in script
    assert "qualification_exit -ne 0" in script


def test_disabled_demo_probe_remains_after_qualification_gate() -> None:
    config = (ROOT / "config/binance_demo_execution_probe_v1.json").read_text(
        encoding="utf-8"
    )
    script = (ROOT / "scripts/run_m5_research_maintenance_once.sh").read_text(
        encoding="utf-8"
    )

    assert '"enabled": false' in config
    assert "-m eba_trader.binance_demo_execution_runtime" in script
    assert "must not submit a new order" in script
