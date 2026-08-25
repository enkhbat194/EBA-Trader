from __future__ import annotations

import json
from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Any

from .backtest_adapter import BacktestAdapterRegistry
from .experiment_queue import ExperimentStatus
from .provenance import collect_source_provenance
from .research_evidence import (
    EVIDENCE_SCHEMA,
    ResearchEvidenceStore,
    canonical_json,
    sha256_file,
    sha256_text,
    source_file_hashes,
)
from .research_queue import ExperimentQueue
from .research_store import ResearchStore


class WorkerOutcome(StrEnum):
    IDLE = "idle"
    PASSED = "passed"
    REQUEUED = "requeued"
    FAILED = "failed"


@dataclass(frozen=True, slots=True)
class WorkerRunResult:
    outcome: WorkerOutcome
    experiment_id: str | None = None
    evidence_id: str | None = None
    error: str | None = None


DatasetResolver = Callable[[str], Path]
SourceProvenanceProvider = Callable[[], Mapping[str, Any]]


def _default_source_provenance() -> Mapping[str, Any]:
    return collect_source_provenance(require_clean=True)


class ResearchBacktestWorker:
    """Claim one research experiment, execute its adapter, and publish immutable evidence."""

    def __init__(
        self,
        *,
        store: ResearchStore,
        queue: ExperimentQueue,
        evidence_store: ResearchEvidenceStore,
        dataset_resolver: DatasetResolver,
        adapter_registry: BacktestAdapterRegistry | None = None,
        source_provenance_provider: SourceProvenanceProvider = _default_source_provenance,
    ) -> None:
        self.store = store
        self.queue = queue
        self.evidence_store = evidence_store
        self.dataset_resolver = dataset_resolver
        self.adapter_registry = adapter_registry or BacktestAdapterRegistry.default()
        self.source_provenance_provider = source_provenance_provider

    def run_once(
        self,
        *,
        worker_id: str,
        stages: Iterable[str] | None = None,
        lease_seconds: int = 900,
        retry_delay_seconds: int = 30,
        now_ms: int | None = None,
    ) -> WorkerRunResult:
        claim = self.queue.claim_next(
            worker_id=worker_id,
            stages=stages,
            lease_seconds=lease_seconds,
            now_ms=now_ms,
        )
        if claim is None:
            return WorkerRunResult(WorkerOutcome.IDLE)

        experiment_id = claim.experiment_id
        try:
            experiment = self._load_experiment(experiment_id)
            strategy = self.store.get_strategy_version(
                str(experiment["strategy_id"]),
                int(experiment["strategy_version"]),
            )
            if strategy is None:
                raise ValueError("strategy version no longer exists")
            strategy_spec = strategy["spec"]
            if not isinstance(strategy_spec, Mapping):
                raise ValueError("strategy spec is not an object")

            adapter_name = str(strategy_spec.get("adapter", "")).strip()
            if not adapter_name:
                raise ValueError("strategy spec adapter is required")
            adapter = self.adapter_registry.get(adapter_name)

            dataset_ref = str(experiment.get("dataset_ref") or "").strip()
            if not dataset_ref:
                raise ValueError("experiment dataset_ref is required")
            dataset_path = self.dataset_resolver(dataset_ref)
            if not dataset_path.is_file():
                raise FileNotFoundError(dataset_path)

            parameters = experiment["parameters"]
            if not isinstance(parameters, Mapping):
                raise ValueError("experiment parameters are not an object")

            execution = adapter.run(
                dataset_path=dataset_path,
                strategy_spec=strategy_spec,
                experiment_parameters=parameters,
                stage=str(experiment["stage"]),
                allow_frozen_oos=False,
            )
            provenance = dict(self.source_provenance_provider())
            git_commit = str(provenance.get("git_commit", "")).strip()
            if not git_commit:
                raise RuntimeError("source provenance is missing git_commit")
            if provenance.get("tracked_working_tree_clean") is False:
                raise RuntimeError("source provenance reports a dirty tracked working tree")

            dataset_sha256 = sha256_file(dataset_path)
            manifest = {
                "schema": EVIDENCE_SCHEMA,
                "experiment_id": experiment_id,
                "strategy": {
                    "strategy_id": strategy["strategy_id"],
                    "version": strategy["version"],
                    "spec_sha256": strategy["spec_sha256"],
                },
                "stage": experiment["stage"],
                "adapter": {
                    "name": execution.adapter_name,
                    "version": execution.adapter_version,
                },
                "experiment_parameters": dict(parameters),
                "experiment_parameters_sha256": sha256_text(canonical_json(parameters)),
                "resolved_config": execution.resolved_config,
                "dataset": {
                    "ref": dataset_ref,
                    "sha256": dataset_sha256,
                    "size_bytes": dataset_path.stat().st_size,
                    **execution.dataset_metadata,
                },
                "source": {
                    **provenance,
                    "source_files_sha256": source_file_hashes(execution.source_files),
                },
                "metrics": execution.metrics,
            }
            evidence = self.evidence_store.persist_backtest_manifest(manifest)
            self.queue.pass_experiment(
                experiment_id=experiment_id,
                worker_id=worker_id,
                metrics=execution.metrics,
                evidence_ref=f"evidence:{evidence.evidence_id}",
                now_ms=now_ms,
            )
            return WorkerRunResult(
                outcome=WorkerOutcome.PASSED,
                experiment_id=experiment_id,
                evidence_id=evidence.evidence_id,
            )
        except (ValueError, KeyError) as exc:
            return self._record_failure(
                experiment_id=experiment_id,
                worker_id=worker_id,
                error=str(exc),
                retryable=False,
                retry_delay_seconds=retry_delay_seconds,
                now_ms=now_ms,
            )
        except FileNotFoundError as exc:
            return self._record_failure(
                experiment_id=experiment_id,
                worker_id=worker_id,
                error=f"dataset missing: {exc}",
                retryable=True,
                retry_delay_seconds=retry_delay_seconds,
                now_ms=now_ms,
            )
        except Exception as exc:
            return self._record_failure(
                experiment_id=experiment_id,
                worker_id=worker_id,
                error=f"{type(exc).__name__}: {exc}",
                retryable=True,
                retry_delay_seconds=retry_delay_seconds,
                now_ms=now_ms,
            )

    def _record_failure(
        self,
        *,
        experiment_id: str,
        worker_id: str,
        error: str,
        retryable: bool,
        retry_delay_seconds: int,
        now_ms: int | None,
    ) -> WorkerRunResult:
        status = self.queue.fail_experiment(
            experiment_id=experiment_id,
            worker_id=worker_id,
            error=error,
            retryable=retryable,
            retry_delay_seconds=retry_delay_seconds,
            now_ms=now_ms,
        )
        outcome = (
            WorkerOutcome.REQUEUED
            if status is ExperimentStatus.QUEUED
            else WorkerOutcome.FAILED
        )
        return WorkerRunResult(
            outcome=outcome,
            experiment_id=experiment_id,
            error=error,
        )

    def _load_experiment(self, experiment_id: str) -> dict[str, Any]:
        with self.store._connection() as connection:
            row = connection.execute(
                "SELECT * FROM experiment_runs WHERE experiment_id = ?",
                (experiment_id,),
            ).fetchone()
        if row is None:
            raise KeyError(f"unknown experiment: {experiment_id}")
        result = dict(row)
        result["parameters"] = json.loads(result.pop("parameters_json") or "{}")
        result["metrics"] = json.loads(result.pop("metrics_json") or "{}")
        return result
