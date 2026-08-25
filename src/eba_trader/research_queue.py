from __future__ import annotations

import time
from collections.abc import Iterable, Mapping
from typing import Any

from .experiment_queue import ExperimentClaim, ExperimentStatus
from .research_store import ResearchStore


def _clock_ms() -> int:
    return time.time_ns() // 1_000_000


class ExperimentQueue:
    """SQLite-backed claim/lease queue for restart-safe research workers.

    Experiment identity and metadata remain owned by ``ResearchStore``. This queue only
    adds worker scheduling state. Claims are serialized with ``BEGIN IMMEDIATE`` so one
    queued experiment cannot be leased to two workers concurrently.
    """

    _QUEUE_COLUMNS = {
        "attempt_count": "INTEGER NOT NULL DEFAULT 0",
        "max_attempts": "INTEGER NOT NULL DEFAULT 3",
        "worker_id": "TEXT",
        "lease_expires_at_ms": "INTEGER",
        "available_at_ms": "INTEGER NOT NULL DEFAULT 0",
        "last_error": "TEXT",
        "claimed_at": "TEXT",
    }

    def __init__(self, store: ResearchStore) -> None:
        self.store = store
        self._initialize()

    def _initialize(self) -> None:
        with self.store._connection() as connection:
            existing = {
                str(row["name"])
                for row in connection.execute("PRAGMA table_info(experiment_runs)").fetchall()
            }
            for name, definition in self._QUEUE_COLUMNS.items():
                if name not in existing:
                    connection.execute(
                        f"ALTER TABLE experiment_runs ADD COLUMN {name} {definition}"
                    )
            connection.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_experiment_queue_ready
                ON experiment_runs(status, available_at_ms, created_at, experiment_id)
                """
            )
            connection.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_experiment_queue_lease
                ON experiment_runs(status, lease_expires_at_ms)
                """
            )

    def enqueue(
        self,
        *,
        strategy_id: str,
        strategy_version: int,
        stage: str,
        parameters: Mapping[str, Any],
        dataset_ref: str | None = None,
        max_attempts: int = 3,
        available_at_ms: int = 0,
    ) -> str:
        if max_attempts < 1:
            raise ValueError("max_attempts must be >= 1")
        if available_at_ms < 0:
            raise ValueError("available_at_ms must be >= 0")

        experiment_id = self.store.create_experiment(
            strategy_id=strategy_id,
            strategy_version=strategy_version,
            stage=stage,
            parameters=parameters,
            dataset_ref=dataset_ref,
        )
        with self.store._connection() as connection:
            row = connection.execute(
                """
                SELECT status, attempt_count FROM experiment_runs
                WHERE experiment_id = ?
                """,
                (experiment_id,),
            ).fetchone()
            if row is None:  # pragma: no cover - defensive invariant
                raise RuntimeError("experiment disappeared after enqueue")
            if row["status"] == ExperimentStatus.QUEUED.value and row["attempt_count"] == 0:
                connection.execute(
                    """
                    UPDATE experiment_runs
                    SET max_attempts = ?, available_at_ms = ?
                    WHERE experiment_id = ?
                    """,
                    (max_attempts, available_at_ms, experiment_id),
                )
        return experiment_id

    def claim_next(
        self,
        *,
        worker_id: str,
        lease_seconds: int = 300,
        stages: Iterable[str] | None = None,
        now_ms: int | None = None,
    ) -> ExperimentClaim | None:
        worker_id = worker_id.strip()
        if not worker_id:
            raise ValueError("worker_id is required")
        if lease_seconds < 1:
            raise ValueError("lease_seconds must be >= 1")
        resolved_now = _clock_ms() if now_ms is None else now_ms
        if resolved_now < 0:
            raise ValueError("now_ms must be >= 0")

        stage_filter = tuple(dict.fromkeys(item.strip() for item in (stages or ()) if item.strip()))
        lease_expires = resolved_now + lease_seconds * 1000

        with self.store._connection() as connection:
            connection.execute("BEGIN IMMEDIATE")
            self._recover_expired_locked(connection, resolved_now)

            query = """
                SELECT experiment_id, attempt_count, max_attempts
                FROM experiment_runs
                WHERE status = ?
                  AND available_at_ms <= ?
                  AND attempt_count < max_attempts
            """
            params: list[Any] = [ExperimentStatus.QUEUED.value, resolved_now]
            if stage_filter:
                placeholders = ",".join("?" for _ in stage_filter)
                query += f" AND stage IN ({placeholders})"
                params.extend(stage_filter)
            query += " ORDER BY created_at, experiment_id LIMIT 1"

            row = connection.execute(query, tuple(params)).fetchone()
            if row is None:
                return None

            experiment_id = str(row["experiment_id"])
            cursor = connection.execute(
                """
                UPDATE experiment_runs
                SET status = ?, worker_id = ?, lease_expires_at_ms = ?,
                    attempt_count = attempt_count + 1,
                    claimed_at = CURRENT_TIMESTAMP,
                    last_error = NULL
                WHERE experiment_id = ?
                  AND status = ?
                  AND available_at_ms <= ?
                  AND attempt_count < max_attempts
                """,
                (
                    ExperimentStatus.RUNNING.value,
                    worker_id,
                    lease_expires,
                    experiment_id,
                    ExperimentStatus.QUEUED.value,
                    resolved_now,
                ),
            )
            if cursor.rowcount != 1:  # pragma: no cover - serialized defensive invariant
                return None

            claimed = connection.execute(
                """
                SELECT attempt_count, max_attempts FROM experiment_runs
                WHERE experiment_id = ?
                """,
                (experiment_id,),
            ).fetchone()
            if claimed is None:  # pragma: no cover
                raise RuntimeError("claimed experiment could not be reloaded")

            return ExperimentClaim(
                experiment_id=experiment_id,
                worker_id=worker_id,
                lease_expires_at_ms=lease_expires,
                attempt_count=int(claimed["attempt_count"]),
                max_attempts=int(claimed["max_attempts"]),
            )

    def renew_lease(
        self,
        *,
        experiment_id: str,
        worker_id: str,
        lease_seconds: int = 300,
        now_ms: int | None = None,
    ) -> ExperimentClaim:
        experiment_id = experiment_id.strip()
        worker_id = worker_id.strip()
        if not experiment_id or not worker_id:
            raise ValueError("experiment_id and worker_id are required")
        if lease_seconds < 1:
            raise ValueError("lease_seconds must be >= 1")
        resolved_now = _clock_ms() if now_ms is None else now_ms
        lease_expires = resolved_now + lease_seconds * 1000

        with self.store._connection() as connection:
            cursor = connection.execute(
                """
                UPDATE experiment_runs
                SET lease_expires_at_ms = ?
                WHERE experiment_id = ?
                  AND status = ?
                  AND worker_id = ?
                  AND lease_expires_at_ms > ?
                """,
                (
                    lease_expires,
                    experiment_id,
                    ExperimentStatus.RUNNING.value,
                    worker_id,
                    resolved_now,
                ),
            )
            if cursor.rowcount != 1:
                raise RuntimeError("lease is missing, expired, or owned by another worker")
            row = connection.execute(
                """
                SELECT attempt_count, max_attempts FROM experiment_runs
                WHERE experiment_id = ?
                """,
                (experiment_id,),
            ).fetchone()
            if row is None:  # pragma: no cover
                raise RuntimeError("renewed experiment could not be reloaded")

        return ExperimentClaim(
            experiment_id=experiment_id,
            worker_id=worker_id,
            lease_expires_at_ms=lease_expires,
            attempt_count=int(row["attempt_count"]),
            max_attempts=int(row["max_attempts"]),
        )

    def pass_experiment(
        self,
        *,
        experiment_id: str,
        worker_id: str,
        metrics: Mapping[str, Any],
        evidence_ref: str,
        now_ms: int | None = None,
    ) -> None:
        evidence_ref = evidence_ref.strip()
        if not evidence_ref:
            raise ValueError("evidence_ref is required")
        self._finish(
            experiment_id=experiment_id,
            worker_id=worker_id,
            status=ExperimentStatus.PASSED,
            metrics=metrics,
            evidence_ref=evidence_ref,
            error=None,
            retryable=False,
            retry_delay_seconds=0,
            now_ms=now_ms,
        )

    def fail_experiment(
        self,
        *,
        experiment_id: str,
        worker_id: str,
        error: str,
        metrics: Mapping[str, Any] | None = None,
        evidence_ref: str | None = None,
        retryable: bool = True,
        retry_delay_seconds: int = 0,
        now_ms: int | None = None,
    ) -> ExperimentStatus:
        error = error.strip()
        if not error:
            raise ValueError("error is required")
        if retry_delay_seconds < 0:
            raise ValueError("retry_delay_seconds must be >= 0")
        return self._finish(
            experiment_id=experiment_id,
            worker_id=worker_id,
            status=ExperimentStatus.FAILED,
            metrics=metrics or {},
            evidence_ref=evidence_ref.strip() if evidence_ref else None,
            error=error,
            retryable=retryable,
            retry_delay_seconds=retry_delay_seconds,
            now_ms=now_ms,
        )

    def recover_expired(self, *, now_ms: int | None = None) -> dict[str, int]:
        resolved_now = _clock_ms() if now_ms is None else now_ms
        with self.store._connection() as connection:
            connection.execute("BEGIN IMMEDIATE")
            return self._recover_expired_locked(connection, resolved_now)

    def _finish(
        self,
        *,
        experiment_id: str,
        worker_id: str,
        status: ExperimentStatus,
        metrics: Mapping[str, Any],
        evidence_ref: str | None,
        error: str | None,
        retryable: bool,
        retry_delay_seconds: int,
        now_ms: int | None,
    ) -> ExperimentStatus:
        experiment_id = experiment_id.strip()
        worker_id = worker_id.strip()
        if not experiment_id or not worker_id:
            raise ValueError("experiment_id and worker_id are required")
        resolved_now = _clock_ms() if now_ms is None else now_ms

        with self.store._connection() as connection:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(
                """
                SELECT attempt_count, max_attempts, lease_expires_at_ms
                FROM experiment_runs
                WHERE experiment_id = ? AND status = ? AND worker_id = ?
                """,
                (experiment_id, ExperimentStatus.RUNNING.value, worker_id),
            ).fetchone()
            if row is None or row["lease_expires_at_ms"] is None:
                raise RuntimeError("experiment is not leased by this worker")
            if int(row["lease_expires_at_ms"]) <= resolved_now:
                raise RuntimeError("experiment lease has expired")

            attempt_count = int(row["attempt_count"])
            max_attempts = int(row["max_attempts"])
            if status is ExperimentStatus.FAILED and retryable and attempt_count < max_attempts:
                available_at = resolved_now + retry_delay_seconds * 1000
                connection.execute(
                    """
                    UPDATE experiment_runs
                    SET status = ?, worker_id = NULL, lease_expires_at_ms = NULL,
                        available_at_ms = ?, last_error = ?, metrics_json = ?,
                        evidence_ref = ?
                    WHERE experiment_id = ?
                    """,
                    (
                        ExperimentStatus.QUEUED.value,
                        available_at,
                        error,
                        self.store_json(metrics),
                        evidence_ref,
                        experiment_id,
                    ),
                )
                return ExperimentStatus.QUEUED

            connection.execute(
                """
                UPDATE experiment_runs
                SET status = ?, worker_id = NULL, lease_expires_at_ms = NULL,
                    metrics_json = ?, evidence_ref = ?, last_error = ?,
                    completed_at = CURRENT_TIMESTAMP
                WHERE experiment_id = ?
                """,
                (
                    status.value,
                    self.store_json(metrics),
                    evidence_ref,
                    error,
                    experiment_id,
                ),
            )
            return status

    @staticmethod
    def store_json(value: Mapping[str, Any]) -> str:
        import json

        return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)

    @staticmethod
    def _recover_expired_locked(connection: Any, now_ms: int) -> dict[str, int]:
        rows = connection.execute(
            """
            SELECT experiment_id, attempt_count, max_attempts
            FROM experiment_runs
            WHERE status = ?
              AND lease_expires_at_ms IS NOT NULL
              AND lease_expires_at_ms <= ?
            ORDER BY experiment_id
            """,
            (ExperimentStatus.RUNNING.value, now_ms),
        ).fetchall()
        requeued = 0
        failed = 0
        for row in rows:
            if int(row["attempt_count"]) < int(row["max_attempts"]):
                connection.execute(
                    """
                    UPDATE experiment_runs
                    SET status = ?, worker_id = NULL, lease_expires_at_ms = NULL,
                        available_at_ms = ?, last_error = 'lease_expired'
                    WHERE experiment_id = ? AND status = ?
                    """,
                    (
                        ExperimentStatus.QUEUED.value,
                        now_ms,
                        row["experiment_id"],
                        ExperimentStatus.RUNNING.value,
                    ),
                )
                requeued += 1
            else:
                connection.execute(
                    """
                    UPDATE experiment_runs
                    SET status = ?, worker_id = NULL, lease_expires_at_ms = NULL,
                        last_error = 'lease_expired_max_attempts',
                        completed_at = CURRENT_TIMESTAMP
                    WHERE experiment_id = ? AND status = ?
                    """,
                    (
                        ExperimentStatus.FAILED.value,
                        row["experiment_id"],
                        ExperimentStatus.RUNNING.value,
                    ),
                )
                failed += 1
        return {"requeued": requeued, "failed": failed}
