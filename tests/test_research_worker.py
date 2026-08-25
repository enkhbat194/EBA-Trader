from pathlib import Path

from eba_trader.experiment_queue import ExperimentStatus
from eba_trader.history import Candle, INTERVAL_MS, save_csv
from eba_trader.research_evidence import ResearchEvidenceStore
from eba_trader.research_queue import ExperimentQueue
from eba_trader.research_store import ResearchStore
from eba_trader.research_worker import ResearchBacktestWorker, WorkerOutcome


def _dataset(tmp_path: Path) -> tuple[Path, int, int]:
    start_ms = 1_704_067_200_000
    step = INTERVAL_MS["15m"]
    count = 80
    previous_close = 100.0
    candles: list[Candle] = []
    for index in range(count):
        open_price = previous_close
        close_price = open_price + (1.1 if index % 20 < 10 else -0.9)
        open_time = start_ms + index * step
        candles.append(
            Candle(
                open_time_ms=open_time,
                open=open_price,
                high=max(open_price, close_price) + 0.5,
                low=min(open_price, close_price) - 0.5,
                close=close_price,
                volume=100.0 + index,
                close_time_ms=open_time + step - 1,
                quote_volume=(100.0 + index) * close_price,
                trade_count=100 + index,
            )
        )
        previous_close = close_price
    return save_csv(candles, tmp_path / "btc.csv"), start_ms, start_ms + count * step


def _provenance() -> dict[str, object]:
    return {
        "git_commit": "test-commit-123",
        "git_branch": "test",
        "tracked_working_tree_clean": True,
        "python_version": "test",
    }


def _build_worker(
    tmp_path: Path,
    *,
    adapter: str = "ema_trend_v1",
    dataset_exists: bool = True,
    max_attempts: int = 3,
) -> tuple[ResearchStore, ExperimentQueue, ResearchEvidenceStore, ResearchBacktestWorker, str]:
    dataset_path, start_ms, end_ms = _dataset(tmp_path)
    if not dataset_exists:
        dataset_path.unlink()

    store = ResearchStore(tmp_path / "research.db")
    store.register_strategy_version(
        strategy_id="STR-W",
        name="Worker Test",
        version=1,
        spec={
            "adapter": adapter,
            "fixed": {"initial_cash": 1_000.0},
            "dataset": {
                "symbol": "BTCUSDT",
                "interval": "15m",
                "start_ms": start_ms,
                "end_ms": end_ms,
            },
        },
    )
    queue = ExperimentQueue(store)
    experiment_id = queue.enqueue(
        strategy_id="STR-W",
        strategy_version=1,
        stage="development_backtest",
        parameters={
            "fast_ema": 3,
            "slow_ema": 8,
            "fee_bps": 1.0,
            "slippage_bps": 1.0,
        },
        dataset_ref="btc.csv",
        max_attempts=max_attempts,
    )
    evidence_store = ResearchEvidenceStore(store, tmp_path / "evidence")
    worker = ResearchBacktestWorker(
        store=store,
        queue=queue,
        evidence_store=evidence_store,
        dataset_resolver=lambda ref: tmp_path / ref,
        source_provenance_provider=_provenance,
    )
    return store, queue, evidence_store, worker, experiment_id


def test_worker_runs_adapter_persists_evidence_and_passes_queue(tmp_path: Path) -> None:
    store, _, evidence_store, worker, experiment_id = _build_worker(tmp_path)

    result = worker.run_once(
        worker_id="worker-a",
        stages=("development_backtest",),
        now_ms=1_000,
    )

    assert result.outcome is WorkerOutcome.PASSED
    assert result.experiment_id == experiment_id
    assert result.evidence_id is not None

    experiment = store.list_experiments(strategy_id="STR-W", strategy_version=1)[0]
    assert experiment["status"] == ExperimentStatus.PASSED.value
    assert experiment["evidence_ref"] == f"evidence:{result.evidence_id}"
    assert experiment["metrics"]["trade_count"] >= 1

    evidence = evidence_store.list_for_experiment(experiment_id)
    assert len(evidence) == 1
    manifest = evidence[0]["manifest"]
    assert manifest["strategy"]["strategy_id"] == "STR-W"
    assert manifest["dataset"]["ref"] == "btc.csv"
    assert len(manifest["dataset"]["sha256"]) == 64
    assert manifest["source"]["git_commit"] == "test-commit-123"
    assert "eba_trader/backtest.py" in manifest["source"]["source_files_sha256"]


def test_missing_dataset_is_retried_then_failed_at_attempt_limit(tmp_path: Path) -> None:
    store, _, _, worker, experiment_id = _build_worker(
        tmp_path,
        dataset_exists=False,
        max_attempts=2,
    )

    first = worker.run_once(
        worker_id="worker-a",
        retry_delay_seconds=5,
        now_ms=1_000,
    )
    assert first.outcome is WorkerOutcome.REQUEUED

    second = worker.run_once(
        worker_id="worker-b",
        retry_delay_seconds=5,
        now_ms=6_000,
    )
    assert second.outcome is WorkerOutcome.FAILED

    experiment = store.list_experiments(strategy_id="STR-W", strategy_version=1)[0]
    assert experiment["experiment_id"] == experiment_id
    assert experiment["status"] == ExperimentStatus.FAILED.value
    assert experiment["attempt_count"] == 2
    assert "dataset missing" in experiment["last_error"]


def test_unknown_adapter_fails_without_retry(tmp_path: Path) -> None:
    store, _, _, worker, experiment_id = _build_worker(tmp_path, adapter="unknown_adapter")

    result = worker.run_once(worker_id="worker-a", now_ms=1_000)

    assert result.outcome is WorkerOutcome.FAILED
    assert result.experiment_id == experiment_id
    experiment = store.list_experiments(strategy_id="STR-W", strategy_version=1)[0]
    assert experiment["status"] == ExperimentStatus.FAILED.value
    assert experiment["attempt_count"] == 1
    assert "Unsupported backtest adapter" in experiment["last_error"]


def test_worker_stage_filter_can_leave_other_work_queued(tmp_path: Path) -> None:
    store, _, _, worker, experiment_id = _build_worker(tmp_path)

    result = worker.run_once(worker_id="worker-a", stages=("oos",), now_ms=1_000)

    assert result.outcome is WorkerOutcome.IDLE
    experiment = store.list_experiments(strategy_id="STR-W", strategy_version=1)[0]
    assert experiment["experiment_id"] == experiment_id
    assert experiment["status"] == ExperimentStatus.QUEUED.value
