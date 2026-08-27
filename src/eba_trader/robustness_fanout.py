from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from .lifecycle import CURRENT_LIFECYCLE_POLICY_VERSION, StrategyLifecycle
from .research_evidence import canonical_json, sha256_text
from .research_queue import ExperimentQueue
from .research_store import ResearchStore

MAX_ROBUSTNESS_JOBS = 250
COST_KEYS = frozenset({"fee_bps", "slippage_bps"})


@dataclass(frozen=True, slots=True)
class RobustnessScenario:
    name: str
    overrides: Mapping[str, Any]

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise ValueError("robustness scenario name is required")
        if not self.overrides:
            raise ValueError("robustness scenario overrides cannot be empty")

    def as_dict(self) -> dict[str, Any]:
        return {"name": self.name, "overrides": dict(self.overrides)}


@dataclass(frozen=True, slots=True)
class RobustnessPlan:
    name: str
    version: int
    base_parameters: Mapping[str, Any]
    parameter_scenarios: tuple[RobustnessScenario, ...] = ()
    cost_scenarios: tuple[RobustnessScenario, ...] = ()
    max_attempts: int = 3

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise ValueError("robustness plan name is required")
        if self.version < 1:
            raise ValueError("robustness plan version must be >= 1")
        if self.max_attempts < 1:
            raise ValueError("max_attempts must be >= 1")
        if not self.parameter_scenarios and not self.cost_scenarios:
            raise ValueError("robustness plan requires at least one scenario")

        parameter_names = [scenario.name for scenario in self.parameter_scenarios]
        cost_names = [scenario.name for scenario in self.cost_scenarios]
        if len(set(parameter_names)) != len(parameter_names):
            raise ValueError("parameter scenario names must be unique")
        if len(set(cost_names)) != len(cost_names):
            raise ValueError("cost scenario names must be unique")
        for scenario in self.cost_scenarios:
            unknown = sorted(set(scenario.overrides) - COST_KEYS)
            if unknown:
                raise ValueError(
                    "cost scenarios may override only fee_bps/slippage_bps; "
                    f"unsupported: {', '.join(unknown)}"
                )

        if self.job_count > MAX_ROBUSTNESS_JOBS:
            raise ValueError(
                f"robustness plan exceeds hard job cap {MAX_ROBUSTNESS_JOBS}: {self.job_count}"
            )

    @property
    def job_count(self) -> int:
        return len(self.parameter_scenarios) + len(self.cost_scenarios)

    def as_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "version": self.version,
            "base_parameters": dict(self.base_parameters),
            "parameter_scenarios": [item.as_dict() for item in self.parameter_scenarios],
            "cost_scenarios": [item.as_dict() for item in self.cost_scenarios],
            "max_attempts": self.max_attempts,
        }

    @property
    def definition_sha256(self) -> str:
        return sha256_text(canonical_json(self.as_dict()))

    @property
    def plan_id(self) -> str:
        return f"rplan_{self.definition_sha256[:24]}"


@dataclass(frozen=True, slots=True)
class RobustnessBatch:
    batch_id: str
    plan_id: str
    strategy_id: str
    strategy_version: int
    dataset_ref: str
    experiment_ids: tuple[str, ...]


class RobustnessFanoutPlanner:
    """Create bounded pre-OOS parameter-neighborhood and cost-stress queue work."""

    def __init__(self, store: ResearchStore, queue: ExperimentQueue) -> None:
        self.store = store
        self.queue = queue
        self._initialize()

    def _initialize(self) -> None:
        with self.store._connection() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS robustness_batches (
                    batch_id TEXT PRIMARY KEY,
                    strategy_id TEXT NOT NULL,
                    strategy_version INTEGER NOT NULL,
                    plan_id TEXT NOT NULL,
                    plan_sha256 TEXT NOT NULL,
                    plan_json TEXT NOT NULL,
                    dataset_ref TEXT NOT NULL,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY(strategy_id, strategy_version)
                        REFERENCES strategy_versions(strategy_id, version)
                        ON DELETE CASCADE
                );

                CREATE TABLE IF NOT EXISTS robustness_batch_experiments (
                    batch_id TEXT NOT NULL,
                    experiment_id TEXT NOT NULL,
                    scenario_kind TEXT NOT NULL,
                    scenario_name TEXT NOT NULL,
                    ordinal INTEGER NOT NULL,
                    PRIMARY KEY(batch_id, experiment_id),
                    UNIQUE(batch_id, scenario_kind, scenario_name),
                    FOREIGN KEY(batch_id) REFERENCES robustness_batches(batch_id)
                        ON DELETE CASCADE,
                    FOREIGN KEY(experiment_id) REFERENCES experiment_runs(experiment_id)
                        ON DELETE RESTRICT
                );

                CREATE INDEX IF NOT EXISTS idx_robustness_batch_strategy
                    ON robustness_batches(strategy_id, strategy_version, created_at);
                """
            )

    def create_batch(
        self,
        *,
        strategy_id: str,
        strategy_version: int,
        dataset_ref: str,
        plan: RobustnessPlan,
    ) -> RobustnessBatch:
        dataset_ref = dataset_ref.strip()
        if not dataset_ref:
            raise ValueError("dataset_ref is required")

        strategy = self.store.get_strategy_version(strategy_id, strategy_version)
        if strategy is None:
            raise KeyError(f"Unknown strategy version {strategy_id} v{strategy_version}")
        if strategy["lifecycle_policy_version"] != CURRENT_LIFECYCLE_POLICY_VERSION:
            raise RuntimeError("robustness fan-out requires current lifecycle policy v2")
        if strategy["lifecycle_state"] is not StrategyLifecycle.BACKTESTED:
            raise RuntimeError(
                "robustness fan-out requires BACKTESTED before frozen OOS is reachable"
            )

        spec = strategy["spec"]
        if not isinstance(spec, Mapping):
            raise RuntimeError("strategy spec is not an object")
        fixed = spec.get("fixed", {})
        if not isinstance(fixed, Mapping):
            raise RuntimeError("strategy fixed config is not an object")
        fixed_keys = set(fixed)

        plan_json = canonical_json(plan.as_dict())
        batch_payload = {
            "strategy_id": strategy_id,
            "strategy_version": strategy_version,
            "strategy_spec_sha256": strategy["spec_sha256"],
            "lifecycle_policy_version": strategy["lifecycle_policy_version"],
            "dataset_ref": dataset_ref,
            "plan_id": plan.plan_id,
            "plan_sha256": plan.definition_sha256,
        }
        batch_id = f"rbatch_{sha256_text(canonical_json(batch_payload))[:24]}"

        with self.store._connection() as connection:
            existing = connection.execute(
                "SELECT * FROM robustness_batches WHERE batch_id = ?",
                (batch_id,),
            ).fetchone()
            if existing is None:
                connection.execute(
                    """
                    INSERT INTO robustness_batches(
                        batch_id, strategy_id, strategy_version, plan_id,
                        plan_sha256, plan_json, dataset_ref
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        batch_id,
                        strategy_id,
                        strategy_version,
                        plan.plan_id,
                        plan.definition_sha256,
                        plan_json,
                        dataset_ref,
                    ),
                )
            elif existing["plan_sha256"] != plan.definition_sha256:
                raise RuntimeError("immutable robustness batch collision")

        experiment_ids: list[str] = []
        ordinal = 0
        scenario_groups = (
            ("parameter", "robustness_parameter", plan.parameter_scenarios),
            ("cost", "robustness_cost", plan.cost_scenarios),
        )
        for scenario_kind, stage, scenarios in scenario_groups:
            for scenario in scenarios:
                parameters = {**plan.base_parameters, **scenario.overrides}
                forbidden = sorted(set(parameters) & fixed_keys)
                if forbidden:
                    raise ValueError(
                        "robustness parameters cannot override immutable strategy fixed fields: "
                        + ", ".join(forbidden)
                    )
                experiment_id = self.queue.enqueue(
                    strategy_id=strategy_id,
                    strategy_version=strategy_version,
                    stage=stage,
                    parameters=parameters,
                    dataset_ref=dataset_ref,
                    max_attempts=plan.max_attempts,
                )
                experiment_ids.append(experiment_id)
                with self.store._connection() as connection:
                    connection.execute(
                        """
                        INSERT OR IGNORE INTO robustness_batch_experiments(
                            batch_id, experiment_id, scenario_kind, scenario_name, ordinal
                        ) VALUES (?, ?, ?, ?, ?)
                        """,
                        (
                            batch_id,
                            experiment_id,
                            scenario_kind,
                            scenario.name,
                            ordinal,
                        ),
                    )
                ordinal += 1

        return RobustnessBatch(
            batch_id=batch_id,
            plan_id=plan.plan_id,
            strategy_id=strategy_id,
            strategy_version=strategy_version,
            dataset_ref=dataset_ref,
            experiment_ids=tuple(experiment_ids),
        )

    def get_batch(self, batch_id: str) -> dict[str, Any] | None:
        with self.store._connection() as connection:
            batch = connection.execute(
                "SELECT * FROM robustness_batches WHERE batch_id = ?",
                (batch_id,),
            ).fetchone()
            if batch is None:
                return None
            experiments = connection.execute(
                """
                SELECT rbe.scenario_kind, rbe.scenario_name, rbe.ordinal,
                       er.experiment_id, er.stage, er.status, er.parameters_json,
                       er.evidence_ref, er.metrics_json, er.attempt_count, er.max_attempts
                FROM robustness_batch_experiments AS rbe
                JOIN experiment_runs AS er USING(experiment_id)
                WHERE rbe.batch_id = ?
                ORDER BY rbe.ordinal
                """,
                (batch_id,),
            ).fetchall()
        result = dict(batch)
        result["plan"] = json.loads(result.pop("plan_json"))
        result["experiments"] = []
        for row in experiments:
            item = dict(row)
            item["parameters"] = json.loads(item.pop("parameters_json") or "{}")
            item["metrics"] = json.loads(item.pop("metrics_json") or "{}")
            result["experiments"].append(item)
        return result
