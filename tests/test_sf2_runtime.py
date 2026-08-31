from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

from eba_trader import sf2_runtime
from eba_trader.sf2_development import candidate_set_sha256
from eba_trader.sf2_protocol import SF2ResearchProtocol, load_sf2_protocol


def _materialization(protocol: SF2ResearchProtocol) -> SimpleNamespace:
    windows = tuple(
        SimpleNamespace(feature_csv_sha256="a" * 64)
        for _ in protocol.corpus.windows
    )
    return SimpleNamespace(
        materialization_id="sf2mat_test",
        corpus_id=protocol.corpus.corpus_id,
        windows=windows,
    )


def _development(protocol: SF2ResearchProtocol) -> dict[str, object]:
    return {
        "schema": "sf2_development_report_v1",
        "evaluationId": "sf2dev_test",
        "phaseId": protocol.phase_id,
        "protocolId": protocol.protocol_id,
        "materializationId": "sf2mat_test",
        "candidateSetSha256": candidate_set_sha256(protocol),
        "candidateCount": 24,
        "multipleTestingBudget": 48,
        "windowCount": 12,
        "topDevelopmentCandidate": "s2_div_l001",
        "developmentEvidenceOnly": True,
        "edgeClaimAllowed": False,
        "promotionAuthority": False,
        "frozenOosOpened": False,
        "m5FrozenOosOpened": False,
        "liveExecutionAllowed": False,
    }


def _validation(protocol: SF2ResearchProtocol) -> dict[str, object]:
    return {
        "schema": "sf2_validation_report_v1",
        "validationId": "sf2val_test",
        "developmentEvaluationId": "sf2dev_test",
        "phaseId": protocol.phase_id,
        "protocolId": protocol.protocol_id,
        "materializationId": "sf2mat_test",
        "candidateSetSha256": candidate_set_sha256(protocol),
        "candidateCount": 24,
        "multipleTestingBudget": 48,
        "windowCount": 12,
        "validationState": "NO_VERIFIED_CANDIDATE",
        "verifiedCandidateCount": 0,
        "topVerifiedCandidate": None,
        "developmentEvidenceOnly": True,
        "edgeClaimAllowed": False,
        "promotionAuthority": False,
        "frozenOosOpened": False,
        "m5FrozenOosOpened": False,
        "liveExecutionAllowed": False,
    }


def test_runtime_materializes_custom_corpus_and_writes_safe_terminal_evidence(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo_root = Path.cwd()
    protocol = load_sf2_protocol(repo_root / sf2_runtime.DEFAULT_PROTOCOL_PATH)
    calls: dict[str, object] = {}

    def fake_materialize(**kwargs: object) -> tuple[SimpleNamespace, Path]:
        calls.update(kwargs)
        manifest = tmp_path / "datasets" / "sf2.manifest.json"
        manifest.parent.mkdir(parents=True, exist_ok=True)
        manifest.write_text("{}", encoding="utf-8")
        return _materialization(protocol), manifest

    monkeypatch.setattr(
        sf2_runtime,
        "materialize_m5_development_corpus",
        fake_materialize,
    )
    monkeypatch.setattr(
        sf2_runtime,
        "evaluate_sf2_development",
        lambda **_: _development(protocol),
    )
    monkeypatch.setattr(
        sf2_runtime,
        "validate_sf2_development",
        lambda *_args, **_kwargs: _validation(protocol),
    )

    result = sf2_runtime.run_sf2_development(
        research_root=tmp_path,
        repo_root=repo_root,
    )

    assert calls["corpus"] == protocol.corpus
    assert calls["namespace"] == "sf2_orderflow_dev"
    assert calls["orderflow_source"] == "archive"
    assert result["phase"] == "COMPLETE"
    assert result["complete"] is True
    assert result["validationState"] == "NO_VERIFIED_CANDIDATE"
    assert result["verifiedCandidateCount"] == 0
    assert result["frozenOosOpened"] is False
    assert result["m5FrozenOosOpened"] is False
    assert result["liveExecutionAllowed"] is False
    assert Path(str(result["developmentReportPath"])).is_file()
    assert Path(str(result["validationReportPath"])).is_file()


def test_runtime_reuses_terminal_evidence_without_reevaluating(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo_root = Path.cwd()
    protocol = load_sf2_protocol(repo_root / sf2_runtime.DEFAULT_PROTOCOL_PATH)
    materialization = _materialization(protocol)
    manifest = tmp_path / "datasets" / "sf2.manifest.json"
    manifest.parent.mkdir(parents=True, exist_ok=True)
    manifest.write_text("{}", encoding="utf-8")

    monkeypatch.setattr(
        sf2_runtime,
        "materialize_m5_development_corpus",
        lambda **_: (materialization, manifest),
    )
    monkeypatch.setattr(
        sf2_runtime,
        "evaluate_sf2_development",
        lambda **_: _development(protocol),
    )
    monkeypatch.setattr(
        sf2_runtime,
        "validate_sf2_development",
        lambda *_args, **_kwargs: _validation(protocol),
    )
    first = sf2_runtime.run_sf2_development(
        research_root=tmp_path,
        repo_root=repo_root,
    )

    monkeypatch.setattr(
        sf2_runtime,
        "evaluate_sf2_development",
        lambda **_: pytest.fail("terminal SF2 evidence was reevaluated"),
    )
    monkeypatch.setattr(
        sf2_runtime,
        "validate_sf2_development",
        lambda *_args, **_kwargs: pytest.fail("terminal SF2 validation was rerun"),
    )
    second = sf2_runtime.run_sf2_development(
        research_root=tmp_path,
        repo_root=repo_root,
    )

    assert second == first
    assert second["phase"] == "COMPLETE"
    assert second["liveExecutionAllowed"] is False


def test_runtime_failure_writes_safe_failed_status(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo_root = Path.cwd()

    def fail_materialize(**_: object) -> tuple[object, Path]:
        raise RuntimeError("synthetic archive failure")

    monkeypatch.setattr(
        sf2_runtime,
        "materialize_m5_development_corpus",
        fail_materialize,
    )

    with pytest.raises(RuntimeError, match="synthetic archive failure"):
        sf2_runtime.run_sf2_development(
            research_root=tmp_path,
            repo_root=repo_root,
        )

    status = sf2_runtime._read_object(
        tmp_path / sf2_runtime.DEFAULT_STATUS_PATH.name,
        label="SF2 failed status",
    )
    assert status["phase"] == "FAILED"
    assert status["safe"] is True
    assert status["edgeClaimAllowed"] is False
    assert status["promotionAuthority"] is False
    assert status["frozenOosOpened"] is False
    assert status["m5FrozenOosOpened"] is False
    assert status["liveExecutionAllowed"] is False
