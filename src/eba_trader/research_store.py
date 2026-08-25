from __future__ import annotations

import hashlib
import json
import sqlite3
from collections.abc import Iterator, Mapping
from contextlib import contextmanager
from pathlib import Path
from typing import Any

from .lifecycle import LifecycleTransition, StrategyLifecycle

DEFAULT_RESEARCH_DB_PATH = Path("artifacts/research/eba_research.db")


def _canonical_json(value: Mapping[str, Any]) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def make_experiment_id(
    *,
    strategy_id: str,
    strategy_version: int,
    stage: str,
    parameters: Mapping[str, Any],
    dataset_ref: str | None,
) -> str:
    payload = _canonical_json(
        {
            "dataset_ref": dataset_ref,
            "parameters": dict(parameters),
            "stage": stage,
            "strategy_id": strategy_id,
            "strategy_version": strategy_version,
        }
    )
    return f"exp_{_sha256_text(payload)[:24]}"


class ResearchStore:
    """Durable research metadata store for strategy versions and evidence.

    Runtime positions remain in ``TradeLedger``. This store is intentionally separate so
    mass research, experiment metadata and lifecycle transitions cannot mutate live/paper
    position state.
    """

    def __init__(self, path: str | Path = DEFAULT_RESEARCH_DB_PATH) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    @contextmanager
    def _connection(self) -> Iterator[sqlite3.Connection]:
        connection = sqlite3.connect(self.path, timeout=10)
        connection.row_factory = sqlite3.Row
        try:
            connection.execute("PRAGMA journal_mode=WAL")
            connection.execute("PRAGMA foreign_keys=ON")
            yield connection
            connection.commit()
        finally:
            connection.close()

    def _initialize(self) -> None:
        with self._connection() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS strategies (
                    strategy_id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    family TEXT,
                    active_version INTEGER,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                );

                CREATE TABLE IF NOT EXISTS strategy_versions (
                    strategy_id TEXT NOT NULL,
                    version INTEGER NOT NULL CHECK (version > 0),
                    lifecycle_state TEXT NOT NULL,
                    spec_json TEXT NOT NULL,
                    spec_sha256 TEXT NOT NULL,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY(strategy_id, version),
                    FOREIGN KEY(strategy_id) REFERENCES strategies(strategy_id)
                        ON DELETE CASCADE
                );

                CREATE TABLE IF NOT EXISTS experiment_runs (
                    experiment_id TEXT PRIMARY KEY,
                    strategy_id TEXT NOT NULL,
                    strategy_version INTEGER NOT NULL,
                    stage TEXT NOT NULL,
                    status TEXT NOT NULL,
                    parameters_json TEXT NOT NULL DEFAULT '{}',
                    dataset_ref TEXT,
                    evidence_ref TEXT,
                    metrics_json TEXT NOT NULL DEFAULT '{}',
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    completed_at TEXT,
                    FOREIGN KEY(strategy_id, strategy_version)
                        REFERENCES strategy_versions(strategy_id, version)
                        ON DELETE CASCADE
                );

                CREATE INDEX IF NOT EXISTS idx_experiments_strategy
                    ON experiment_runs(strategy_id, strategy_version, stage, status);

                CREATE TABLE IF NOT EXISTS lifecycle_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    strategy_id TEXT NOT NULL,
                    strategy_version INTEGER NOT NULL,
                    previous_state TEXT NOT NULL,
                    current_state TEXT NOT NULL,
                    reason TEXT NOT NULL,
                    evidence_ref TEXT,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY(strategy_id, strategy_version)
                        REFERENCES strategy_versions(strategy_id, version)
                        ON DELETE CASCADE
                );

                CREATE INDEX IF NOT EXISTS idx_lifecycle_strategy
                    ON lifecycle_history(strategy_id, strategy_version, id);
                """
            )

    def register_strategy_version(
        self,
        *,
        strategy_id: str,
        name: str,
        version: int,
        spec: Mapping[str, Any],
        family: str | None = None,
        activate: bool = True,
    ) -> dict[str, Any]:
        strategy_id = strategy_id.strip()
        name = name.strip()
        if not strategy_id:
            raise ValueError("strategy_id is required")
        if not name:
            raise ValueError("name is required")
        if version <= 0:
            raise ValueError("version must be positive")

        spec_json = _canonical_json(spec)
        spec_sha256 = _sha256_text(spec_json)

        with self._connection() as connection:
            strategy = connection.execute(
                "SELECT * FROM strategies WHERE strategy_id = ?",
                (strategy_id,),
            ).fetchone()
            if strategy is None:
                connection.execute(
                    """
                    INSERT INTO strategies(strategy_id, name, family, active_version)
                    VALUES (?, ?, ?, ?)
                    """,
                    (strategy_id, name, family, version if activate else None),
                )
            else:
                if strategy["name"] != name:
                    raise ValueError("strategy_id already exists with a different name")
                if activate:
                    connection.execute(
                        """
                        UPDATE strategies
                        SET active_version = ?, updated_at = CURRENT_TIMESTAMP
                        WHERE strategy_id = ?
                        """,
                        (version, strategy_id),
                    )

            existing = connection.execute(
                """
                SELECT * FROM strategy_versions
                WHERE strategy_id = ? AND version = ?
                """,
                (strategy_id, version),
            ).fetchone()
            if existing is not None:
                if existing["spec_sha256"] != spec_sha256:
                    raise ValueError(
                        "strategy version is immutable; create a new version for a changed spec"
                    )
                return self._strategy_version_row(existing)

            connection.execute(
                """
                INSERT INTO strategy_versions(
                    strategy_id, version, lifecycle_state, spec_json, spec_sha256
                ) VALUES (?, ?, ?, ?, ?)
                """,
                (
                    strategy_id,
                    version,
                    StrategyLifecycle.GENERATED.value,
                    spec_json,
                    spec_sha256,
                ),
            )

        record = self.get_strategy_version(strategy_id, version)
        if record is None:  # pragma: no cover - defensive invariant
            raise RuntimeError("registered strategy version could not be reloaded")
        return record

    def get_strategy_version(self, strategy_id: str, version: int) -> dict[str, Any] | None:
        with self._connection() as connection:
            row = connection.execute(
                """
                SELECT sv.*, s.name, s.family, s.active_version
                FROM strategy_versions AS sv
                JOIN strategies AS s USING(strategy_id)
                WHERE sv.strategy_id = ? AND sv.version = ?
                """,
                (strategy_id, version),
            ).fetchone()
        return self._strategy_version_row(row) if row is not None else None

    def record_transition(
        self,
        *,
        strategy_id: str,
        strategy_version: int,
        current: StrategyLifecycle,
        reason: str,
        evidence_ref: str | None = None,
    ) -> LifecycleTransition:
        with self._connection() as connection:
            row = connection.execute(
                """
                SELECT lifecycle_state FROM strategy_versions
                WHERE strategy_id = ? AND version = ?
                """,
                (strategy_id, strategy_version),
            ).fetchone()
            if row is None:
                raise KeyError(f"Unknown strategy version {strategy_id} v{strategy_version}")

            previous = StrategyLifecycle(row["lifecycle_state"])
            transition = LifecycleTransition(
                previous=previous,
                current=current,
                reason=reason,
                evidence_ref=evidence_ref,
            )
            connection.execute(
                """
                UPDATE strategy_versions
                SET lifecycle_state = ?, updated_at = CURRENT_TIMESTAMP
                WHERE strategy_id = ? AND version = ?
                """,
                (current.value, strategy_id, strategy_version),
            )
            connection.execute(
                """
                INSERT INTO lifecycle_history(
                    strategy_id, strategy_version, previous_state,
                    current_state, reason, evidence_ref
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    strategy_id,
                    strategy_version,
                    previous.value,
                    current.value,
                    reason,
                    evidence_ref,
                ),
            )
        return transition

    def create_experiment(
        self,
        *,
        strategy_id: str,
        strategy_version: int,
        stage: str,
        parameters: Mapping[str, Any],
        dataset_ref: str | None = None,
    ) -> str:
        stage = stage.strip()
        if not stage:
            raise ValueError("stage is required")
        experiment_id = make_experiment_id(
            strategy_id=strategy_id,
            strategy_version=strategy_version,
            stage=stage,
            parameters=parameters,
            dataset_ref=dataset_ref,
        )
        parameters_json = _canonical_json(parameters)

        with self._connection() as connection:
            existing = connection.execute(
                "SELECT * FROM experiment_runs WHERE experiment_id = ?",
                (experiment_id,),
            ).fetchone()
            if existing is not None:
                return experiment_id
            connection.execute(
                """
                INSERT INTO experiment_runs(
                    experiment_id, strategy_id, strategy_version, stage, status,
                    parameters_json, dataset_ref
                ) VALUES (?, ?, ?, ?, 'queued', ?, ?)
                """,
                (
                    experiment_id,
                    strategy_id,
                    strategy_version,
                    stage,
                    parameters_json,
                    dataset_ref,
                ),
            )
        return experiment_id

    def record_experiment_result(
        self,
        experiment_id: str,
        *,
        status: str,
        metrics: Mapping[str, Any],
        evidence_ref: str,
    ) -> None:
        status = status.strip()
        evidence_ref = evidence_ref.strip()
        if not status:
            raise ValueError("status is required")
        if not evidence_ref:
            raise ValueError("evidence_ref is required")
        with self._connection() as connection:
            cursor = connection.execute(
                """
                UPDATE experiment_runs
                SET status = ?, metrics_json = ?, evidence_ref = ?,
                    completed_at = CURRENT_TIMESTAMP
                WHERE experiment_id = ?
                """,
                (status, _canonical_json(metrics), evidence_ref, experiment_id),
            )
            if cursor.rowcount != 1:
                raise KeyError(f"Unknown experiment {experiment_id}")

    def list_experiments(
        self,
        *,
        strategy_id: str,
        strategy_version: int,
    ) -> list[dict[str, Any]]:
        with self._connection() as connection:
            rows = connection.execute(
                """
                SELECT * FROM experiment_runs
                WHERE strategy_id = ? AND strategy_version = ?
                ORDER BY created_at, experiment_id
                """,
                (strategy_id, strategy_version),
            ).fetchall()
        return [self._experiment_row(row) for row in rows]

    @staticmethod
    def _strategy_version_row(row: sqlite3.Row) -> dict[str, Any]:
        data = dict(row)
        data["spec"] = json.loads(data.pop("spec_json"))
        data["lifecycle_state"] = StrategyLifecycle(data["lifecycle_state"])
        return data

    @staticmethod
    def _experiment_row(row: sqlite3.Row) -> dict[str, Any]:
        data = dict(row)
        data["parameters"] = json.loads(data.pop("parameters_json") or "{}")
        data["metrics"] = json.loads(data.pop("metrics_json") or "{}")
        return data
