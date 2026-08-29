from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_maintenance_gates_robustness_on_qualification_and_significance() -> None:
    script = (ROOT / "scripts/run_m5_research_maintenance_once.sh").read_text(
        encoding="utf-8"
    )

    multiwindow = "-m eba_trader.m5_multiwindow_runtime"
    qualification = "-m eba_trader.m5_candidate_qualification_runtime"
    significance = "-m eba_trader.m5_candidate_significance_runtime"
    robustness = "-m eba_trader.m5_absorption_robustness_runtime"

    for marker in (multiwindow, qualification, significance, robustness):
        assert marker in script
    assert (
        script.index(multiwindow)
        < script.index(qualification)
        < script.index(significance)
        < script.index(robustness)
    )
    assert "m5-candidate-significance-latest.json" in script
    assert 'if [[ "$eligible_count" == "0" ]]' in script
    assert 'elif [[ "$significant_count" == "0" ]]' in script
    assert 'robustness_state="skipped_no_eligible_candidate"' in script
    assert 'robustness_state="skipped_significance_gate"' in script
    assert 'if [[ "$top_candidate" == "absorption_020" ]]' in script
    assert "blocked_candidate_runner_mismatch" in script
    assert "significance_exit -ne 0" in script


def test_disabled_demo_probe_remains_after_significance_gate() -> None:
    config = (ROOT / "config/binance_demo_execution_probe_v1.json").read_text(
        encoding="utf-8"
    )
    script = (ROOT / "scripts/run_m5_research_maintenance_once.sh").read_text(
        encoding="utf-8"
    )

    assert '"enabled": false' in config
    assert "-m eba_trader.binance_demo_execution_runtime" in script
    assert "must not submit a new order" in script
