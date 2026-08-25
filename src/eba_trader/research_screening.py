from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .experiment_queue import ExperimentStatus
from .lifecycle import StrategyLifecycle
from .research_evidence import EVIDENCE_SCHEMA, canonical_json, sha256_file, sha256_text
from .research_gates import GateEvaluation, GateSet, evaluate_gate_set
from .research_store import ResearchStore


@dataclass(frozen=True, slots=True)
class ScreeningVerdict:
    verdict_id: str
    gate_set_id: str
    experiment_id: str
    evidence_id: str
    passed: bool
    promoted: bool
    evaluation: GateEvaluation


class DevelopmentScreeningOrchestrator:
    """Evaluate immutable development evidence and promote only on complete gate success."""

    def __init__(self, store: ResearchStore) -> None:
        self.store = store
        self._initialize()

    def _initialize(self) -> None:
        with self.store._connection() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS screening_gate_sets (
                    gate_set_id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    version INTEGER NOT NULL,
                    definition_sha256 TEXT NOT NULL,
                    definition_json TEXT NOT NULL,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(name, version)
                );

                CREATE TABLE IF NOT EXISTS screening_verdicts (
                    verdict_id TEXT PRIMARY KEY,
                    strategy_id TEXT NOT NULL,
                    strategy_version INTEGER NOT NULL,
                    experiment_id TEXT NOT NULL,
                    evidence_id TEXT NOT NULL,
                    gate_set_id TEXT NOT NULL,
                    evidence_artifact_sha256 TEXT NOT NULL,
                    strategy_spec_sha256 TEXT NOT NULL,
                    metrics_sha256 TEXT NOT NULL,
                    passed INTEGER NOT NULL CHECK (passed IN (0, 1)),
                    results_json TEXT NOT NULL,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY(strategy_id, strategy_version)
                        REFERENCES strategy_versions(strategy_id, version)
                        ON DELETE CASCADE,
                    FOREIGN KEY(experiment_id) REFERENCES experiment_runs(experiment_id)
                        ON DELETE CASCADE,
                    FOREIGN KEY(evidence_id) REFERENCES evidence_records(evidence_id)
                        ON DELETE RESTRICT,
                    FOREIGN KEY(gate_set_id) REFERENCES screening_gate_sets(gate_set_id)
                        ON DELETE RESTRICT,
                    UNIQUE(experiment_id, evidence_id, gate_set_id)
                );

                CREATE INDEX IF NOT EXISTS idx_screening_verdict_strategy
                    ON screening_verdicts(strategy_id, strategy_version, created_at);
                """
            )

    def screen(
        self,
        *,
        strategy_id: str,
        strategy_version: int,
        experiment_id: str,
        gate_set: GateSet,
    ) -> ScreeningVerdict:
        strategy = self.store.get_strategy_version(strategy_id, strategy_version)
        if strategy is None:
            raise KeyError(f"Unknown strategy version {strategy_id} v{strategy_version}")
        if strategy["lifecycle_state"] not in {
            StrategyLifecycle.GENERATED,
            StrategyLifecycle.BACKTESTED,
        }:
            raise RuntimeError(
                "development screening requires GENERATED state or an idempotent BACKTESTED replay"
            )

        experiment = self._load_experiment(experiment_id)
        if experiment["strategy_id"] != strategy_id or int(experiment["strategy_version"]) != strategy_version:
            raise ValueError("experiment does not belong to the requested strategy version")
        if experiment["stage"] != "development_backtest":
            raise ValueError("development screening requires stage='development_backtest'")
        if experiment["status"] != ExperimentStatus.PASSED.value:
            raise RuntimeError("development experiment must be PASSED before screening")

        evidence_ref = str(experiment.get("evidence_ref") or "")
        if not evidence_ref.startswith("evidence:"):
            raise RuntimeError("passed experiment is missing an evidence:<id> reference")
        evidence_id = evidence_ref.removeprefix("evidence:").strip()
        if not evidence_id:
            raise RuntimeError("passed experiment evidence reference is empty")

        evidence = self._load_and_verify_evidence(
            evidence_id=evidence_id,
            experiment_id=experiment_id,
            strategy=strategy,
        )
        manifest = evidence["manifest"]
        metrics = manifest.get("metrics")
        if not isinstance(metrics, Mapping):
            raise RuntimeError("evidence manifest metrics are missing or invalid")
        experiment_metrics = experiment["metrics"]
        if canonical_json(dict(metrics)) != canonical_json(dict(experiment_metrics)):
            raise RuntimeError("experiment metrics do not match immutable evidence metrics")

        self._persist_gate_set(gate_set)
        evaluation = evaluate_gate_set(gate_set, metrics)
        metrics_sha256 = sha256_text(canonical_json(dict(metrics)))
        verdict_payload = {
            "strategy_id": strategy_id,
            "strategy_version": strategy_version,
            "strategy_spec_sha256": strategy["spec_sha256"],
            "experiment_id": experiment_id,
            "evidence_id": evidence_id,
            "evidence_artifact_sha256": evidence["artifact_sha256"],
            "gate_set_id": gate_set.gate_set_id,
            "gate_set_definition_sha256": gate_set.definition_sha256,
            "metrics_sha256": metrics_sha256,
            "evaluation": evaluation.as_dict(),
        }
        verdict_id = f"ver_{sha256_text(canonical_json(verdict_payload))[:24]}"
        self._persist_verdict(
            verdict_id=verdict_id,
            strategy_id=strategy_id,
            strategy_version=strategy_version,
            experiment_id=experiment_id,
            evidence_id=evidence_id,
            gate_set=gate_set,
            evidence_artifact_sha256=str(evidence["artifact_sha256"]),
            strategy_spec_sha256=str(strategy["spec_sha256"]),
            metrics_sha256=metrics_sha256,
            evaluation=evaluation,
        )

        promoted = False
        if evaluation.passed:
            current = strategy["lifecycle_state"]
            evidence_reference = f"verdict:{verdict_id}"
            if current is StrategyLifecycle.GENERATED:
                self.store.record_transition(
                    strategy_id=strategy_id,
                    strategy_version=strategy_version,
                    current=StrategyLifecycle.BACKTESTED,
                    reason="Declared development screening gates passed",
                    evidence_ref=evidence_reference,
                )
                promoted = True
            else:
                self._assert_idempotent_backtested_transition(
                    strategy_id=strategy_id,
                    strategy_version=strategy_version,
                    evidence_ref=evidence_reference,
                )

        return ScreeningVerdict(
            verdict_id=verdict_id,
            gate_set_id=gate_set.gate_set_id,
            experiment_id=experiment_id,
            evidence_id=evidence_id,
            passed=evaluation.passed,
            promoted=promoted,
            evaluation=evaluation,
        )

    def list_verdicts(self, strategy_id: str, strategy_version: int) -> list[dict[str, Any]]:
        with self.store._connection() as connection:
            rows = connection.execute(
                """
                SELECT * FROM screening_verdicts
                WHERE strategy_id = ? AND strategy_version = ?
                ORDER BY created_at, verdict_id
                """,
                (strategy_id, strategy_version),
            ).fetchall()
        result: list[dict[str, Any]] = []
        for row in rows:
            item = dict(row)
            item["passed"] = bool(item["passed"])
            item["results"] = json.loads(item.pop("results_json"))
            result.append(item)
        return result

    def _load_experiment(self, experiment_id: str) -> dict[str, Any]:
        with self.store._connection() as connection:
            row = connection.execute(
                "SELECT * FROM experiment_runs WHERE experiment_id = ?",
                (experiment_id,),
            ).fetchone()
        if row is None:
            raise KeyError(f"Unknown experiment {experiment_id}")
        item = dict(row)
        item["parameters"] = json.loads(item.pop("parameters_json") or "{}")
        item["metrics"] = json.loads(item.pop("metrics_json") or "{}")
        return item

    def _load_and_verify_evidence(
        self,
        *,
        evidence_id: str,
        experiment_id: str,
        strategy: Mapping[str, Any],
    ) -> dict[str, Any]:
        with self.store._connection() as connection:
            row = connection.execute(
                """
                SELECT * FROM evidence_records
                WHERE evidence_id = ? AND experiment_id = ?
                """,
                (evidence_id, experiment_id),
            ).fetchone()
        if row is None:
            raise RuntimeError("referenced evidence record does not exist for this experiment")

        item = dict(row)
        artifact_path = Path(str(item["artifact_path"]))
        if not artifact_path.is_file():
            raise RuntimeError("referenced evidence artifact file is missing")
        actual_sha256 = sha256_file(artifact_path)
        if actual_sha256 != item["artifact_sha256"]:
            raise RuntimeError("evidence artifact SHA-256 mismatch")

        artifact_text = artifact_path.read_text(encoding="utf-8")
        manifest = json.loads(artifact_text)
        if canonical_json(manifest) != artifact_text:
            raise RuntimeError("evidence artifact is not canonical immutable JSON")
        if manifest.get("schema") != EVIDENCE_SCHEMA:
            raise RuntimeError("unsupported evidence schema")
        if manifest.get("experiment_id") != experiment_id:
            raise RuntimeError("evidence manifest experiment mismatch")

        manifest_strategy = manifest.get("strategy")
        if not isinstance(manifest_strategy, Mapping):
            raise RuntimeError("evidence strategy metadata is invalid")
        if manifest_strategy.get("strategy_id") != strategy["strategy_id"]:
            raise RuntimeError("evidence strategy_id mismatch")
        if int(manifest_strategy.get("version", -1)) != int(strategy["version"]):
            raise RuntimeError("evidence strategy version mismatch")
        if manifest_strategy.get("spec_sha256") != strategy["spec_sha256"]:
            raise RuntimeError("evidence strategy specification hash mismatch")

        item["manifest"] = manifest
        return item

    def _persist_gate_set(self, gate_set: GateSet) -> None:
        definition_json = canonical_json(gate_set.as_dict())
        with self.store._connection() as connection:
            same_version = connection.execute(
                """
                SELECT * FROM screening_gate_sets
                WHERE name = ? AND version = ?
                """,
                (gate_set.name, gate_set.version),
            ).fetchone()
            if same_version is not None:
                if same_version["definition_sha256"] != gate_set.definition_sha256:
                    raise ValueError(
                        "gate set name/version is immutable; increment version for changed rules"
                    )
                return
            connection.execute(
                """
                INSERT INTO screening_gate_sets(
                    gate_set_id, name, version, definition_sha256, definition_json
                ) VALUES (?, ?, ?, ?, ?)
                """,
                (
                    gate_set.gate_set_id,
                    gate_set.name,
                    gate_set.version,
                    gate_set.definition_sha256,
                    definition_json,
                ),
            )

    def _persist_verdict(
        self,
        *,
        verdict_id: str,
        strategy_id: str,
        strategy_version: int,
        experiment_id: str,
        evidence_id: str,
        gate_set: GateSet,
        evidence_artifact_sha256: str,
        strategy_spec_sha256: str,
        metrics_sha256: str,
        evaluation: GateEvaluation,
    ) -> None:
        results_json = canonical_json(evaluation.as_dict())
        with self.store._connection() as connection:
            existing = connection.execute(
                "SELECT * FROM screening_verdicts WHERE verdict_id = ?",
                (verdict_id,),
            ).fetchone()
            if existing is not None:
                if existing["results_json"] != results_json:
                    raise RuntimeError("immutable screening verdict collision")
                return
            connection.execute(
                """
                INSERT INTO screening_verdicts(
                    verdict_id, strategy_id, strategy_version, experiment_id,
                    evidence_id, gate_set_id, evidence_artifact_sha256,
                    strategy_spec_sha256, metrics_sha256, passed, results_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    verdict_id,
                    strategy_id,
                    strategy_version,
                    experiment_id,
                    evidence_id,
                    gate_set.gate_set_id,
                    evidence_artifact_sha256,
                    strategy_spec_sha256,
                    metrics_sha256,
                    1 if evaluation.passed else 0,
                    results_json,
                ),
            )

    def _assert_idempotent_backtested_transition(
        self,
        *,
        strategy_id: str,
        strategy_version: int,
        evidence_ref: str,
    ) -> None:
        with self.store._connection() as connection:
            row = connection.execute(
                """
                SELECT 1 FROM lifecycle_history
                WHERE strategy_id = ? AND strategy_version = ?
                  AND current_state = ? AND evidence_ref = ?
                LIMIT 1
                """,
                (
                    strategy_id,
                    strategy_version,
                    StrategyLifecycle.BACKTESTED.value,
                    evidence_ref,
                ),
            ).fetchone()
        if row is None:
            raise RuntimeError(
                "strategy is already BACKTESTED under different evidence; create a new version "
                "or explicit retest workflow instead of silently replacing authority"
            )
