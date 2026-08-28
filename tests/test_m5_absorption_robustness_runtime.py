from __future__ import annotations

import json
from pathlib import Path

from eba_trader import m5_absorption_robustness_runtime as runtime


def _fake_report() -> dict[str, object]:
    return {
        "schema": "m5_absorption_robustness_report_v1",
        "robustnessId": "m5rob_test",
        "materializationId": "m5corpusmat_test",
        "candidateId": "absorption_020",
        "candidateParameters": {"absorption_threshold": 0.2},
        "scenarioCount": 9,
        "scenarios": [],
        "checks": {
            "parameterNeighborhoodStable": True,
            "costStressStable": True,
            "emaStable": True,
            "centerProfitable": False,
            "sampleSufficient": False,
            "minimumCenterTrades": 30,
            "minimumBeatBaselineWindows": 9,
        },
        "robustnessVerified": False,
        "developmentEvidenceOnly": True,
        "edgeClaimAllowed": False,
        "promotionAuthority": False,
        "frozenOosOpened": False,
        "m5FrozenOosOpened": False,
        "liveExecutionAllowed": False,
    }


def test_runtime_writes_complete_non_promoting_status_and_reuses_it(
    monkeypatch,
    tmp_path: Path,
) -> None:
    research_root = tmp_path / "research"
    manifest = research_root / "datasets" / "manifest.json"
    manifest.parent.mkdir(parents=True, exist_ok=True)
    manifest.write_text("{}\n", encoding="utf-8")

    monkeypatch.setattr(
        runtime,
        "_load_complete_corpus_status",
        lambda _: {
            "materializationId": "m5corpusmat_test",
            "manifestPath": str(manifest),
        },
    )
    calls = {"evaluate": 0}

    def fake_evaluate(**_: object) -> dict[str, object]:
        calls["evaluate"] += 1
        return _fake_report()

    def fake_write(path: str | Path, report: dict[str, object]) -> Path:
        output = Path(path)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(report), encoding="utf-8")
        return output

    monkeypatch.setattr(runtime, "evaluate_absorption_robustness", fake_evaluate)
    monkeypatch.setattr(runtime, "write_immutable_robustness_report", fake_write)

    status_path = research_root / "m5-absorption-robustness-latest.json"
    first = runtime.run_absorption_robustness(
        research_root=research_root,
        status_path=status_path,
    )
    second = runtime.run_absorption_robustness(
        research_root=research_root,
        status_path=status_path,
    )

    assert calls["evaluate"] == 1
    assert first == second
    assert first["phase"] == "COMPLETE"
    assert first["complete"] is True
    assert first["safe"] is True
    assert first["robustnessVerified"] is False
    assert first["checks"]["centerProfitable"] is False
    assert first["checks"]["sampleSufficient"] is False
    assert first["edgeClaimAllowed"] is False
    assert first["promotionAuthority"] is False
    assert first["frozenOosOpened"] is False
    assert first["m5FrozenOosOpened"] is False
    assert first["liveExecutionAllowed"] is False


def test_maintenance_runs_robustness_only_after_multiwindow_success() -> None:
    script = Path("scripts/run_m5_research_maintenance_once.sh").read_text(encoding="utf-8")

    assert "robustness_exit=0" in script
    assert "if [[ $multiwindow_exit -eq 0 ]]" in script
    assert "-m eba_trader.m5_absorption_robustness_runtime" in script
    assert "$robustness_exit -ne 0" in script
    assert "robustness=ok" in script
    assert "final-oos" not in script.lower()
    assert "order_send" not in script
    assert "place_order" not in script
