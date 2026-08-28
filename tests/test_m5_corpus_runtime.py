from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from eba_trader import m5_corpus_runtime


def _fake_materialization() -> SimpleNamespace:
    windows = tuple(
        SimpleNamespace(feature_csv_sha256=f"{index:064x}") for index in range(1, 13)
    )
    return SimpleNamespace(
        materialization_id="m5corpusmat_test",
        policy_id="m5_policy_test",
        corpus_id="m5_corpus_test",
        windows=windows,
    )


def test_runtime_writes_complete_safe_status(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    research_root = tmp_path / "research"
    manifest = research_root / "datasets" / "m5_orderflow_dev" / "manifest.json"
    manifest.parent.mkdir(parents=True)
    manifest.write_text("{}\n", encoding="utf-8")

    def fake_materialize(**kwargs: object) -> tuple[SimpleNamespace, Path]:
        assert kwargs["dataset_root"] == research_root / "datasets"
        assert kwargs["namespace"] == "m5_orderflow_dev"
        assert kwargs["price_bucket"] == 1.0
        assert kwargs["orderflow_source"] == "archive"
        return _fake_materialization(), manifest

    monkeypatch.setattr(
        m5_corpus_runtime,
        "materialize_m5_development_corpus",
        fake_materialize,
    )

    status_path = research_root / "m5-corpus-materialization-latest.json"
    payload = m5_corpus_runtime.run_m5_corpus_materialization(
        research_root=research_root,
        status_path=status_path,
    )

    persisted = json.loads(status_path.read_text(encoding="utf-8"))
    assert persisted == payload
    assert payload["phase"] == "COMPLETE"
    assert payload["complete"] is True
    assert payload["safe"] is True
    assert payload["integrityVerified"] is True
    assert payload["expectedWindowCount"] == 12
    assert payload["windowCount"] == 12
    assert payload["orderflowSource"] == "archive"
    assert payload["allFeatureHashesPresent"] is True
    assert payload["frozenOosOpened"] is False
    assert payload["m5FrozenOosOpened"] is False
    assert payload["liveExecutionAllowed"] is False
    assert payload["edgeClaimAllowed"] is False
    assert payload["promotionAuthority"] is False


def test_runtime_failure_stays_execution_safe_and_retryable(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    research_root = tmp_path / "research"
    status_path = research_root / "m5-corpus-materialization-latest.json"

    def fail_materialize(**_: object) -> tuple[SimpleNamespace, Path]:
        raise RuntimeError("archive temporarily unavailable")

    monkeypatch.setattr(
        m5_corpus_runtime,
        "materialize_m5_development_corpus",
        fail_materialize,
    )

    with pytest.raises(RuntimeError, match="archive temporarily unavailable"):
        m5_corpus_runtime.run_m5_corpus_materialization(
            research_root=research_root,
            status_path=status_path,
        )

    payload = json.loads(status_path.read_text(encoding="utf-8"))
    assert payload["phase"] == "FAILED"
    assert payload["complete"] is False
    assert payload["safe"] is True
    assert payload["integrityVerified"] is False
    assert payload["windowCount"] is None
    assert payload["frozenOosOpened"] is False
    assert payload["m5FrozenOosOpened"] is False
    assert payload["liveExecutionAllowed"] is False
    assert payload["edgeClaimAllowed"] is False
    assert payload["promotionAuthority"] is False
    assert payload["errorType"] == "RuntimeError"


def test_m5_maintenance_keeps_ablation_and_corpus_retry_together() -> None:
    script = Path("scripts/run_m5_research_maintenance_once.sh").read_text(encoding="utf-8")
    service = Path("deploy/systemd/eba-m5-real-ablation.service").read_text(encoding="utf-8")

    assert "run_m5_real_ablation_once.sh" in script
    assert "-m eba_trader.m5_corpus_runtime" in script
    assert "ablation_exit" in script
    assert "corpus_exit" in script
    assert "run_m5_research_maintenance_once.sh" in service
    assert "TimeoutStartSec=45min" in service
    assert "ReadWritePaths=/var/lib/eba-trader/research" in service
