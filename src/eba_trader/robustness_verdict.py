from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from .experiment_queue import ExperimentStatus
from .research_evidence import canonical_json, sha256_text
from .research_gates import GateEvaluation, GateSet, evaluate_gate_set
from .research_store import ResearchStore
from .robustness_fanout import RobustnessFanoutPlanner


@dataclass(frozen=True, slots=True)
class RobustnessVerdict:
    verdict_id: str
    batch_id: str
    gate_set_id: str
    passed: bool
    experiment_count: int
    failed_experiment_ids: tuple[str, ...]


class RobustnessVerdictEngine:
    """Aggregate completed robustness experiments without changing lifecycle state.

    M4 deliberately stops at an immutable robustness verdict. OOS authorization and any
    later lifecycle promotion remain separate gates so this engine cannot unlock frozen OOS
    or live execution.
    """

    def __init__(self, store: ResearchStore) -> None:
        self.store = store
        self.planner = RobustnessFanoutPlanner(store, queue=_NoQueue())
        self._initialize()

    def _initialize(self) -> None:
        with self.store._connection() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS robustness_verdicts (
                    verdict_id TEXT PRIMARY KEY,
                    batch_id TEXT NOT NULL,
                    gate_set_id TEXT NOT NULL,
                    gate_set_sha256 TEXT NOT NULL,
                    passed INTEGER NOT NULL CHECK (passed IN (0, 1)),
                    experiment_count INTEGER NOT NULL,
                    results_json TEXT NOT NULL,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY(batch_id) REFERENCES robustness_batches(batch_id)
                        ON DELETE CASCADE,
                    UNIQUE(batch_id, gate_set_id)
                );

                CREATE INDEX IF NOT EXISTS idx_robustness_verdict_batch
                    ON robustness_verdicts(batch_id, created_at);
                """
            )

    def evaluate(self, *, batch_id: str, gate_set: GateSet) -> RobustnessVerdict:
        batch = self.planner.get_batch(batch_id)
        if batch is None:
            raise KeyError(f"Unknown robustness batch {batch_id}")
        experiments = batch["experiments"]
        if not experiments:
            raise RuntimeError("robustness batch has no experiments")

        per_experiment: list[dict[str, Any]] = []
        failed_ids: list[str] = []
        for experiment in experiments:
            status = str(experiment["status"])
            experiment_id = str(experiment["experiment_id"])
            if status != ExperimentStatus.PASSED.value:
                raise RuntimeError(
                    f"robustness experiment {experiment_id} is not PASSED: {status}"
                )
            evidence_ref = str(experiment.get("evidence_ref") or "")
            if not evidence_ref.startswith("evidence:"):
                raise RuntimeError(
                    f"robustness experiment {experiment_id} is missing immutable evidence"
                )
            metrics = experiment.get("metrics")
            if not isinstance(metrics, Mapping):
                raise RuntimeError(f"robustness experiment {experiment_id} metrics are invalid")

            evaluation: GateEvaluation = evaluate_gate_set(gate_set, metrics)
            if not evaluation.passed:
                failed_ids.append(experiment_id)
            per_experiment.append(
                {
                    "experiment_id": experiment_id,
                    "scenario_kind": experiment["scenario_kind"],
                    "scenario_name": experiment["scenario_name"],
                    "evidence_ref": evidence_ref,
                    "evaluation": evaluation.as_dict(),
                }
            )

        payload = {
            "batch_id": batch_id,
            "plan_id": batch["plan_id"],
            "plan_sha256": batch["plan_sha256"],
            "strategy_id": batch["strategy_id"],
            "strategy_version": batch["strategy_version"],
            "gate_set_id": gate_set.gate_set_id,
            "gate_set_sha256": gate_set.definition_sha256,
            "experiments": per_experiment,
            "passed": not failed_ids,
        }
        verdict_id = f"rver_{sha256_text(canonical_json(payload))[:24]}"
        results_json = canonical_json(payload)

        with self.store._connection() as connection:
            existing_policy = connection.execute(
                """
                SELECT gate_set_sha256, verdict_id, results_json
                FROM robustness_verdicts
                WHERE batch_id = ? AND gate_set_id = ?
                """,
                (batch_id, gate_set.gate_set_id),
            ).fetchone()
            if existing_policy is not None:
                if (
                    existing_policy["gate_set_sha256"] != gate_set.definition_sha256
                    or existing_policy["results_json"] != results_json
                    or existing_policy["verdict_id"] != verdict_id
                ):
                    raise RuntimeError("immutable robustness verdict collision")
            else:
                connection.execute(
                    """
                    INSERT INTO robustness_verdicts(
                        verdict_id, batch_id, gate_set_id, gate_set_sha256,
                        passed, experiment_count, results_json
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        verdict_id,
                        batch_id,
                        gate_set.gate_set_id,
                        gate_set.definition_sha256,
                        0 if failed_ids else 1,
                        len(experiments),
                        results_json,
                    ),
                )

        return RobustnessVerdict(
            verdict_id=verdict_id,
            batch_id=batch_id,
            gate_set_id=gate_set.gate_set_id,
            passed=not failed_ids,
            experiment_count=len(experiments),
            failed_experiment_ids=tuple(failed_ids),
        )

    def list_verdicts(self, batch_id: str) -> list[dict[str, Any]]:
        with self.store._connection() as connection:
            rows = connection.execute(
                """
                SELECT * FROM robustness_verdicts
                WHERE batch_id = ?
                ORDER BY created_at, verdict_id
                """,
                (batch_id,),
            ).fetchall()
        result: list[dict[str, Any]] = []
        for row in rows:
            item = dict(row)
            item["passed"] = bool(item["passed"])
            item["results"] = json.loads(item.pop("results_json"))
            result.append(item)
        return result


class _NoQueue:
    """Sentinel used only because the planner owns read helpers and requires a queue."""

    def enqueue(self, **_: Any) -> str:  # pragma: no cover - verdict path never enqueues
        raise RuntimeError("robustness verdict engine cannot enqueue experiments")
