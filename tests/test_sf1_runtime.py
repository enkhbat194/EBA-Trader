from __future__ import annotations

import json
from pathlib import Path

import pytest

from eba_trader import sf1_runtime
from eba_trader.sf1_strategy_factory import REPORT_SCHEMA as DEVELOPMENT_SCHEMA
from eba_trader.sf1_strategy_factory import SF1Candidate
from eba_trader.sf1_validation import REPORT_SCHEMA as VALIDATION_SCHEMA


def _write_corpus_status(
    research_root: Path,
    manifest: Path,
    *,
    complete: bool = True,
) -> None:
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
        "materializationId": "m5corpusmat_sf1_test",
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


def _fake_development(candidate_sha: str) -> dict[str, object]:
    return {
        "schema": DEVELOPMENT_SCHEMA,
        "evaluationId": "sf1eval_runtime_test",
        "phaseId": "sf1_independent_families_v1",
        "materializationId": "m5corpusmat_sf1_test",
        "candidateSetSha256": candidate_sha,
        "candidateCount": 2,
        "multipleTestingBudget": 48,
        "warmupBars": 64,
        "windowCount": 12,
        "baseline": {"windows": [], "aggregate": {}},
        "candidates": [],
        "developmentRanking": [],
        "rankingIsDevelopmentOnly": True,
        "developmentEvidenceOnly": True,
        "edgeClaimAllowed": False,
        "promotionAuthority": False,
        "frozenOosOpened": False,
        "m5FrozenOosOpened": False,
        "liveExecutionAllowed": False,
    }


def _fake_validation(candidate_sha: str) -> dict[str, object]:
    return {
        "schema": VALIDATION_SCHEMA,
        "validationId": "sf1val_runtime_test",
        "developmentEvaluationId": "sf1eval_runtime_test",
        "phaseId": "sf1_independent_families_v1",
        "materializationId": "m5corpusmat_sf1_test",
        "candidateSetSha256": candidate_sha,
        "candidateCount": 2,
        "multipleTestingBudget": 48,
        "windowCount": 12,
        "candidateValidation": [],
        "verifiedCandidateCount": 0,
        "topVerifiedCandidate": None,
        "validationState": "NO_VERIFIED_CANDIDATE",
        "developmentEvidenceOnly": True,
        "edgeClaimAllowed": False,
        "promotionAuthority": False,
        "frozenOosOpened": False,
        "m5FrozenOosOpened": False,
        "liveExecutionAllowed": False,
    }


def _fake_write(path: str | Path, report: dict[str, object]) -> Path:
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report), encoding="utf-8")
    return output


def test_sf1_runtime_evaluates_validates_and_reuses(
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
        SF1Candidate("atr_a", "atr_trailing_v1", {"atr_period": 7, "atr_multiplier": 2.0}),
        SF1Candidate("atr_b", "atr_trailing_v1", {"atr_period": 14, "atr_multiplier": 2.5}),
    )
    candidate_sha = sf1_runtime._candidate_set_sha(candidates)
    calls = {"evaluate": 0, "validate": 0}

    monkeypatch.setattr(
        sf1_runtime,
        "load_sf1_candidates",
        lambda _: (48, 64, candidates),
    )

    def fake_evaluate(**_: object) -> dict[str, object]:
        calls["evaluate"] += 1
        return _fake_development(candidate_sha)

    def fake_validate(_: object) -> dict[str, object]:
        calls["validate"] += 1
        return _fake_validation(candidate_sha)

    monkeypatch.setattr(sf1_runtime, "evaluate_sf1_atr", fake_evaluate)
    monkeypatch.setattr(sf1_runtime, "validate_sf1_development", fake_validate)
    monkeypatch.setattr(sf1_runtime, "write_immutable_sf1_report", _fake_write)
    monkeypatch.setattr(sf1_runtime, "write_immutable_sf1_validation", _fake_write)

    status_path = research_root / "sf1-development-latest.json"
    first = sf1_runtime.run_sf1_development(
        research_root=research_root,
        repo_root=repo_root,
        status_path=status_path,
    )
    second = sf1_runtime.run_sf1_development(
        research_root=research_root,
        repo_root=repo_root,
        status_path=status_path,
    )

    assert first == second
    assert calls == {"evaluate": 1, "validate": 1}
    assert first["phase"] == "COMPLETE"
    assert first["complete"] is True
    assert first["safe"] is True
    assert first["candidateCount"] == 2
    assert first["multipleTestingBudget"] == 48
    assert first["windowCount"] == 12
    assert first["validationState"] == "NO_VERIFIED_CANDIDATE"
    assert first["verifiedCandidateCount"] == 0
    assert first["topVerifiedCandidate"] is None
    assert first["developmentEvidenceOnly"] is True
    assert first["edgeClaimAllowed"] is False
    assert first["promotionAuthority"] is False
    assert first["frozenOosOpened"] is False
    assert first["m5FrozenOosOpened"] is False
    assert first["liveExecutionAllowed"] is False


def test_sf1_runtime_fails_closed_when_corpus_is_incomplete(tmp_path: Path) -> None:
    research_root = tmp_path / "research"
    repo_root = tmp_path / "repo"
    manifest = research_root / "datasets" / "corpus.json"
    manifest.parent.mkdir(parents=True, exist_ok=True)
    manifest.write_text("{}\n", encoding="utf-8")
    _write_corpus_status(research_root, manifest, complete=False)
    status_path = research_root / "sf1-development-latest.json"

    with pytest.raises(RuntimeError, match="corpus is not ready"):
        sf1_runtime.run_sf1_development(
            research_root=research_root,
            repo_root=repo_root,
            status_path=status_path,
        )

    payload = json.loads(status_path.read_text(encoding="utf-8"))
    assert payload["phase"] == "FAILED"
    assert payload["safe"] is True
    assert payload["complete"] is False
    assert payload["developmentEvidenceOnly"] is True
    assert payload["edgeClaimAllowed"] is False
    assert payload["promotionAuthority"] is False
    assert payload["frozenOosOpened"] is False
    assert payload["m5FrozenOosOpened"] is False
    assert payload["liveExecutionAllowed"] is False
