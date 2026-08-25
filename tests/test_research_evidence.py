from pathlib import Path

from eba_trader.research_evidence import EVIDENCE_SCHEMA, ResearchEvidenceStore
from eba_trader.research_store import ResearchStore


def _store(tmp_path: Path) -> tuple[ResearchStore, ResearchEvidenceStore, str]:
    store = ResearchStore(tmp_path / "research.db")
    store.register_strategy_version(
        strategy_id="STR-E",
        name="Evidence Test",
        version=1,
        spec={"adapter": "ema_trend_v1"},
    )
    experiment_id = store.create_experiment(
        strategy_id="STR-E",
        strategy_version=1,
        stage="development_backtest",
        parameters={"fast_ema": 3, "slow_ema": 8},
        dataset_ref="btc-15m.csv",
    )
    return store, ResearchEvidenceStore(store, tmp_path / "evidence"), experiment_id


def _manifest(experiment_id: str, *, commit: str = "abc123") -> dict[str, object]:
    return {
        "schema": EVIDENCE_SCHEMA,
        "experiment_id": experiment_id,
        "strategy": {
            "strategy_id": "STR-E",
            "version": 1,
            "spec_sha256": "a" * 64,
        },
        "stage": "development_backtest",
        "adapter": {"name": "ema_trend_v1", "version": "1"},
        "experiment_parameters": {"fast_ema": 3, "slow_ema": 8},
        "experiment_parameters_sha256": "b" * 64,
        "resolved_config": {"fast_ema": 3, "slow_ema": 8},
        "dataset": {
            "ref": "btc-15m.csv",
            "sha256": "c" * 64,
            "size_bytes": 1234,
            "symbol": "BTCUSDT",
            "interval": "15m",
            "start_ms": 1,
            "end_ms": 2,
            "candle_count": 80,
        },
        "source": {
            "git_commit": commit,
            "tracked_working_tree_clean": True,
            "source_files_sha256": {"eba_trader/backtest.py": "d" * 64},
        },
        "metrics": {"total_return": 0.12, "trade_count": 7},
    }


def test_evidence_artifact_is_content_addressed_and_idempotent(tmp_path: Path) -> None:
    store, evidence_store, experiment_id = _store(tmp_path)
    manifest = _manifest(experiment_id)

    first = evidence_store.persist_backtest_manifest(manifest)
    second = evidence_store.persist_backtest_manifest(manifest)

    assert first.evidence_id == second.evidence_id
    assert first.sha256 == second.sha256
    assert first.path.read_text(encoding="utf-8") == second.path.read_text(encoding="utf-8")

    records = evidence_store.list_for_experiment(experiment_id)
    assert len(records) == 1
    assert records[0]["artifact_sha256"] == first.sha256
    assert records[0]["manifest"]["metrics"]["trade_count"] == 7

    experiment = store.list_experiments(strategy_id="STR-E", strategy_version=1)[0]
    assert experiment["experiment_id"] == experiment_id


def test_different_source_commit_creates_distinct_evidence(tmp_path: Path) -> None:
    _, evidence_store, experiment_id = _store(tmp_path)
    first = evidence_store.persist_backtest_manifest(_manifest(experiment_id, commit="abc123"))
    second = evidence_store.persist_backtest_manifest(_manifest(experiment_id, commit="def456"))

    assert first.evidence_id != second.evidence_id
    records = evidence_store.list_for_experiment(experiment_id)
    assert len(records) == 2
    assert {row["source_commit"] for row in records} == {"abc123", "def456"}
