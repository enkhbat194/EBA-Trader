from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_sf3_runs_as_independent_development_stage() -> None:
    script = (ROOT / "scripts/run_m5_research_maintenance_once.sh").read_text(
        encoding="utf-8"
    )

    sf2 = "-m eba_trader.sf2_runtime"
    sf3 = "-m eba_trader.sf3_runtime"
    demo = "-m eba_trader.binance_demo_execution_runtime"

    assert sf2 in script
    assert sf3 in script
    assert demo in script
    assert script.index(sf2) < script.index(sf3) < script.index(demo)
    assert "sf3_exit -ne 0" in script
    assert 'sf3_state="complete"' in script
    assert 'sf3_state="failed"' in script

    robustness_demo_guard = "if [[ $robustness_exit -eq 0 ]]; then"
    guard_index = script.rindex(robustness_demo_guard)
    assert script.index(sf3) < guard_index < script.index(demo)


def test_sf3_maintenance_preserves_research_locks() -> None:
    script = (ROOT / "scripts/run_m5_research_maintenance_once.sh").read_text(
        encoding="utf-8"
    )

    assert "distinct preregistered" in script
    assert "cannot reuse SF1/SF2 evidence" in script
    assert "Frozen OOS and live execution locked" in script
