from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_activity_diagnostics_run_after_multiwindow_before_qualification() -> None:
    script = (ROOT / "scripts/run_m5_research_maintenance_once.sh").read_text(
        encoding="utf-8"
    )

    multiwindow = "-m eba_trader.m5_multiwindow_runtime"
    activity = "-m eba_trader.m5_candidate_activity_runtime"
    qualification = "-m eba_trader.m5_candidate_qualification_runtime"

    assert multiwindow in script
    assert activity in script
    assert qualification in script
    assert script.index(multiwindow) < script.index(activity) < script.index(qualification)
    assert "activity_exit -ne 0" in script
    assert 'activity_state="complete"' in script
    assert 'activity_state="failed"' in script
    assert 'activity_state="blocked_multiwindow"' in script
