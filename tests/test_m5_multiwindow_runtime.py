from __future__ import annotations

import json
from pathlib import Path

import pytest

from eba_trader import m5_multiwindow_runtime
from eba_trader.m5_multiwindow import REPORT_SCHEMA, M5MultiWindowCandidate


def _write_corpus_status(research_root: Path, manifest: Path, *, complete: bool = True) -> None:
    payload = {
        "schema": "m5_corpus_runtime_status_v1",
        "phase": "COMPLETE" if complete else "RUNNING",
        "complete": complete,
        "safe": True,
        "integrityVerified": complete,
        "expectedWindowCount": 12,
        "windowCount": 12 if complete else None,
        "orderflowSource": "archive",
        "allFeatureHashesPresent": complete,
        "materializationId": "m5corpusmat_test",
        "manifestPath": str(manifest),
        "frozenOosOpened": False,
        "m5FrozenOosOpened": False,
        "liveExecutionAllowed": False,
        "edgeClaimAllowed": False,
        "promotionAuthority": False,
    }
    path = research_root / "m5-corpus-materialization-latest.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


def _fake_report(candidate_set_sha: str) -> dict[str, object]:
    aggregate = {
        "windowCount": 12,
        "meanReturn": 0.001,
        "medianReturn": 0.001,
        "worstWindowReturn": -0.001,
        "bestWindowReturn": 0.003,
        "positiveWindowCount": 8,
        "beatBaselineWindowCount": 9,
        "notWorseThanBaselineWindowCount": 10,
        "meanReturnDeltaVsBaseline": 0.001,
        "medianReturnDeltaVsBaseline": 0.001,
        "worstReturnDeltaVsBaseline": -0.001,
        "bestReturnDeltaVsBaseline": 0.004,
        "meanExpectancy": 1.0,
        "worstMaxDrawdown": -0.002,
        "totalTradeCount": 20,
        "totalCost": 40.0,
    }
    return {
        "schema": REPORT_SCHEMA,
        "evaluationId": "m5multi_test",
        "materializationId": "m5corpusmat_test",
        "policyId": "m5policy_test",
        "corpusId": "m5corpus_test",
        "candidateSetSha256": candidate_set_sha,
        "windowCount": 12,
        "candidateCount": 2,
        "baseline": {"aggregate": {"windowCount": 12, "meanReturn": -0.001}},
        "developmentRanking": [
            {
                "developmentPriorityRank": 1,
                "candidateId": "delta_020",
                "parameters": {"delta_ratio_threshold": 0.2},
                "aggregate": aggregate,
            }
        ],
        "rankingIsDevelopmentOnly": True,
        "edgeClaimAllowed": False,
        "promotionAuthority": False,
        "frozenOosOpened": False,
        "m5FrozenOosOpened": False,
        "liveExecutionAllowed": False,
    }


def test_runtime_evaluates_once_and_reuses_complete_report(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    research_root = tmp_path / "research"
    repo_root = tmp_path / "repo"
    manifest = research_root / "datasets" / "corpus.json"
    manifest.parent.mkdir(parents=True, exist_ok=True)
    manifest.write_text("{}\n", encoding="utf-8")
    _write_corpus_status(research_root, manifest)

    candidates = (
        M5MultiWindowCandidate("delta_020", {"delta_ratio_threshold": 0.2}),
        M5MultiWindowCandidate("stacked_1", {"stacked_imbalance_threshold": 1}),
    )
    candidate_sha = m5_multiwindow_runtime._candidate_set_sha(candidates)
    calls = {"evaluate": 0}

    monkeypatch.setattr(
        m5_multiwindow_runtime,
        "load_m5_multiwindow_candidates",
        lambda _: candidates,
    )

    def fake_evaluate(**_: object) -> dict[str, object]:
        calls["evaluate"] += 1
        return _fake_report(candidate_sha)

    def fake_write(path: str | Path, report: dict[str, object]) -> Path:
        output = Path(path)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(report), encoding="utf-8")
        return output

    monkeypatch.setattr(m5_multiwindow_runtime, "evaluate_m5_multiwindow", fake_evaluate)
    monkeypatch.setattr(
        m5_multiwindow_runtime,
        "write_immutable_m5_multiwindow_report",
        fake_write,
    )

    status_path = research_root / "m5-multiwindow-evaluation-latest.json"
    first = m5_multiwindow_runtime.run_m5_multiwindow_evaluation(
        research_root=research_root,
        repo_root=repo_root,
        status_path=status_path,
    )
    second = m5_multiwindow_runtime.run_m5_multiwindow_evaluation(
        research_root=research_root,
        repo_root=repo_root,
        status_path=status_path,
    )

    assert first == second
    assert calls["evaluate"] == 1
    assert first["phase"] == "COMPLETE"
    assert first["complete"] is True
    assert first["safe"] is True
    assert first["windowCount"] == 12
    assert first["candidateCount"] == 2
    assert first["topDevelopmentCandidate"] == "delta_020"
    assert first["rankingIsDevelopmentOnly"] is True
    assert first["edgeClaimAllowed"] is False
    assert first["promotionAuthority"] is False
    assert first["frozenOosOpened"] is False
    assert first["m5FrozenOosOpened"] is False
    assert first["liveExecutionAllowed"] is False


def test_runtime_fails_safe_when_corpus_is_not_complete(tmp_path: Path) -> None:
    research_root = tmp_path / "research"
    repo_root = tmp_path / "repo"
    manifest = research_root / "datasets" / "corpus.json"
    manifest.parent.mkdir(parents=True, exist_ok=True)
    manifest.write_text("{}\n", encoding="utf-8")
    _write_corpus_status(research_root, manifest, complete=False)
    status_path = research_root / "m5-multiwindow-evaluation-latest.json"

    with pytest.raises(RuntimeError, match="corpus is not ready"):
        m5_multiwindow_runtime.run_m5_multiwindow_evaluation(
            research_root=research_root,
            repo_root=repo_root,
            status_path=status_path,
        )

    payload = json.loads(status_path.read_text(encoding="utf-8"))
    assert payload["phase"] == "FAILED"
    assert payload["safe"] is True
    assert payload["complete"] is False
    assert payload["frozenOosOpened"] is False
    assert payload["m5FrozenOosOpened"] is False
    assert payload["liveExecutionAllowed"] is False
    assert payload["edgeClaimAllowed"] is False
    assert payload["promotionAuthority"] is False
