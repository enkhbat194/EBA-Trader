from pathlib import Path

import pytest

from eba_trader.experiment_queue import ExperimentStatus
from eba_trader.research_queue import ExperimentQueue
from eba_trader.research_store import ResearchStore


def _queue(tmp_path: Path) -> tuple[ResearchStore, ExperimentQueue]:
    store = ResearchStore(tmp_path / "research.db")
    store.register_strategy_version(
        strategy_id="STR-Q",
        name="Queue Test",
        version=1,
        spec={"kind": "test"},
    )
    return store, ExperimentQueue(store)


def _enqueue(queue: ExperimentQueue, **overrides: object) -> str:
    values: dict[str, object] = {
        "strategy_id": "STR-Q",
        "strategy_version": 1,
        "stage": "development_backtest",
        "parameters": {"fast": 8, "slow": 21},
        "dataset_ref": "btc-1m-research",
    }
    values.update(overrides)
    return queue.enqueue(**values)  # type: ignore[arg-type]


def test_enqueue_is_idempotent_and_only_one_worker_claims(tmp_path: Path) -> None:
    store, queue = _queue(tmp_path)
    experiment_id = _enqueue(queue)
    assert _enqueue(queue) == experiment_id

    first = queue.claim_next(worker_id="worker-a", lease_seconds=30, now_ms=1_000)
    second = queue.claim_next(worker_id="worker-b", lease_seconds=30, now_ms=1_000)

    assert first is not None
    assert first.experiment_id == experiment_id
    assert first.worker_id == "worker-a"
    assert first.attempt_count == 1
    assert second is None

    rows = store.list_experiments(strategy_id="STR-Q", strategy_version=1)
    assert len(rows) == 1
    assert rows[0]["status"] == ExperimentStatus.RUNNING.value
    assert rows[0]["worker_id"] == "worker-a"


def test_claim_can_filter_by_stage(tmp_path: Path) -> None:
    _, queue = _queue(tmp_path)
    _enqueue(queue, stage="development_backtest", parameters={"variant": 1})
    target = _enqueue(queue, stage="oos", parameters={"variant": 2})

    claim = queue.claim_next(
        worker_id="oos-worker",
        stages=("oos",),
        now_ms=1_000,
    )

    assert claim is not None
    assert claim.experiment_id == target


def test_lease_renewal_requires_current_owner(tmp_path: Path) -> None:
    _, queue = _queue(tmp_path)
    experiment_id = _enqueue(queue)
    claim = queue.claim_next(worker_id="worker-a", lease_seconds=10, now_ms=1_000)
    assert claim is not None

    renewed = queue.renew_lease(
        experiment_id=experiment_id,
        worker_id="worker-a",
        lease_seconds=20,
        now_ms=5_000,
    )
    assert renewed.lease_expires_at_ms == 25_000

    with pytest.raises(RuntimeError, match="owned by another worker"):
        queue.renew_lease(
            experiment_id=experiment_id,
            worker_id="worker-b",
            now_ms=6_000,
        )


def test_retryable_failure_requeues_with_delay(tmp_path: Path) -> None:
    store, queue = _queue(tmp_path)
    experiment_id = _enqueue(queue, max_attempts=3)
    first = queue.claim_next(worker_id="worker-a", lease_seconds=30, now_ms=1_000)
    assert first is not None

    status = queue.fail_experiment(
        experiment_id=experiment_id,
        worker_id="worker-a",
        error="temporary data source failure",
        retry_delay_seconds=5,
        now_ms=2_000,
    )
    assert status is ExperimentStatus.QUEUED
    assert queue.claim_next(worker_id="worker-b", now_ms=6_999) is None

    second = queue.claim_next(worker_id="worker-b", now_ms=7_000)
    assert second is not None
    assert second.experiment_id == experiment_id
    assert second.attempt_count == 2

    row = store.list_experiments(strategy_id="STR-Q", strategy_version=1)[0]
    assert row["last_error"] is None


def test_retry_exhaustion_becomes_terminal_failure(tmp_path: Path) -> None:
    store, queue = _queue(tmp_path)
    experiment_id = _enqueue(queue, max_attempts=2)

    first = queue.claim_next(worker_id="worker-a", now_ms=1_000)
    assert first is not None
    assert (
        queue.fail_experiment(
            experiment_id=experiment_id,
            worker_id="worker-a",
            error="first failure",
            now_ms=2_000,
        )
        is ExperimentStatus.QUEUED
    )

    second = queue.claim_next(worker_id="worker-b", now_ms=2_000)
    assert second is not None
    assert second.attempt_count == 2
    assert (
        queue.fail_experiment(
            experiment_id=experiment_id,
            worker_id="worker-b",
            error="second failure",
            now_ms=3_000,
        )
        is ExperimentStatus.FAILED
    )

    row = store.list_experiments(strategy_id="STR-Q", strategy_version=1)[0]
    assert row["status"] == ExperimentStatus.FAILED.value
    assert row["last_error"] == "second failure"
    assert row["completed_at"] is not None


def test_expired_lease_is_requeued_then_failed_at_attempt_limit(tmp_path: Path) -> None:
    store, queue = _queue(tmp_path)
    experiment_id = _enqueue(queue, max_attempts=2)

    first = queue.claim_next(worker_id="worker-a", lease_seconds=1, now_ms=1_000)
    assert first is not None
    assert queue.recover_expired(now_ms=2_000) == {"requeued": 1, "failed": 0}

    second = queue.claim_next(worker_id="worker-b", lease_seconds=1, now_ms=2_000)
    assert second is not None
    assert second.attempt_count == 2
    assert queue.recover_expired(now_ms=3_000) == {"requeued": 0, "failed": 1}

    row = store.list_experiments(strategy_id="STR-Q", strategy_version=1)[0]
    assert row["experiment_id"] == experiment_id
    assert row["status"] == ExperimentStatus.FAILED.value
    assert row["last_error"] == "lease_expired_max_attempts"


def test_expired_worker_cannot_publish_result(tmp_path: Path) -> None:
    _, queue = _queue(tmp_path)
    experiment_id = _enqueue(queue)
    claim = queue.claim_next(worker_id="worker-a", lease_seconds=1, now_ms=1_000)
    assert claim is not None

    with pytest.raises(RuntimeError, match="lease has expired"):
        queue.pass_experiment(
            experiment_id=experiment_id,
            worker_id="worker-a",
            metrics={"profit_factor": 1.4},
            evidence_ref="artifact:late-result",
            now_ms=2_000,
        )


def test_passed_experiment_persists_metrics_and_evidence(tmp_path: Path) -> None:
    store, queue = _queue(tmp_path)
    experiment_id = _enqueue(queue)
    claim = queue.claim_next(worker_id="worker-a", lease_seconds=30, now_ms=1_000)
    assert claim is not None

    queue.pass_experiment(
        experiment_id=experiment_id,
        worker_id="worker-a",
        metrics={"profit_factor": 1.42, "expectancy": 0.18},
        evidence_ref="artifact:experiment-001",
        now_ms=2_000,
    )

    row = store.list_experiments(strategy_id="STR-Q", strategy_version=1)[0]
    assert row["status"] == ExperimentStatus.PASSED.value
    assert row["metrics"]["profit_factor"] == 1.42
    assert row["evidence_ref"] == "artifact:experiment-001"
    assert row["worker_id"] is None
    assert row["lease_expires_at_ms"] is None
