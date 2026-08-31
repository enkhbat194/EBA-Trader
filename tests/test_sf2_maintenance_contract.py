from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_sf2_runs_as_independent_development_stage() -> None:
    script = (ROOT / "scripts/run_m5_research_maintenance_once.sh").read_text(
        encoding="utf-8"
    )

    sf2 = "-m eba_trader.sf2_runtime"
    demo = "-m eba_trader.binance_demo_execution_runtime"

    assert sf2 in script
    assert demo in script
    assert script.index(sf2) < script.index(demo)
    assert "sf2_exit -ne 0" in script
    assert 'sf2_state="complete"' in script
    assert 'sf2_state="failed"' in script

    # The final robustness guard controls only the disabled Demo proof. SF2 must run
    # before that guard, independently of the legacy candidate-specific robustness path.
    robustness_demo_guard = "if [[ $robustness_exit -eq 0 ]]; then"
    guard_index = script.rindex(robustness_demo_guard)
    assert script.index(sf2) < guard_index < script.index(demo)


def test_sf2_maintenance_comment_preserves_no_authority_contract() -> None:
    script = (ROOT / "scripts/run_m5_research_maintenance_once.sh").read_text(
        encoding="utf-8"
    )

    assert "independent fresh-development phase" in script
    assert "Frozen OOS and live execution locked" in script
