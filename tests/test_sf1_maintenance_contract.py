from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_sf1_runs_after_corpus_and_remains_independent_from_m5_promotion() -> None:
    script = (ROOT / "scripts/run_m5_research_maintenance_once.sh").read_text(
        encoding="utf-8"
    )

    corpus = "-m eba_trader.m5_corpus_runtime"
    sf1 = "-m eba_trader.sf1_runtime"
    multiwindow = "-m eba_trader.m5_multiwindow_runtime"
    significance = "-m eba_trader.m5_candidate_significance_runtime"
    robustness = "-m eba_trader.m5_absorption_robustness_runtime"

    assert corpus in script
    assert sf1 in script
    assert multiwindow in script
    assert significance in script
    assert robustness in script
    assert script.index(corpus) < script.index(sf1) < script.index(multiwindow)
    assert script.index(significance) < script.index(robustness)
    assert "sf1_exit -ne 0" in script
    assert 'sf1_state="blocked_corpus"' in script
    assert 'sf1_state="failed"' in script
    assert 'if [[ "$top_candidate" == "absorption_020" ]]' in script
    assert "m5FrozenOosOpened" not in script
    assert "liveExecutionAllowed" not in script
