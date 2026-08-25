from __future__ import annotations

from dataclasses import dataclass

from .m5_factory import ParameterFamily, StrategyCandidateFactory
from .m5_hypothesis import StrategyHypothesis
from .research_queue import ExperimentQueue
from .research_store import ResearchStore


@dataclass(frozen=True, slots=True)
class EmittedExperimentFamily:
    strategy_id: str
    strategy_version: int
    hypothesis_fingerprint: str
    experiment_ids: tuple[str, ...]


class M5ExperimentEmitter:
    """Register one constrained hypothesis and emit deterministic M4 experiments."""

    def __init__(self, store: ResearchStore, queue: ExperimentQueue) -> None:
        self.store = store
        self.queue = queue

    def emit(
        self,
        *,
        hypothesis: StrategyHypothesis,
        parameter_family: ParameterFamily,
        dataset_ref: str,
        stage: str = "m5_candidate",
        max_attempts: int = 3,
    ) -> EmittedExperimentFamily:
        hypothesis.validate()
        dataset_ref = dataset_ref.strip()
        stage = stage.strip()
        if not dataset_ref:
            raise ValueError("dataset_ref is required")
        if not stage:
            raise ValueError("stage is required")

        strategy_id = f"M5-{hypothesis.fingerprint.removeprefix('hyp_').upper()}"
        spec = {
            "schema": "m5_hypothesis_v1",
            "hypothesis": hypothesis.as_dict(),
        }
        self.store.register_strategy_version(
            strategy_id=strategy_id,
            name=f"M5 {hypothesis.family}",
            version=hypothesis.version,
            family=hypothesis.family,
            spec=spec,
        )

        candidates = StrategyCandidateFactory().expand(hypothesis, parameter_family)
        experiment_ids = tuple(
            self.queue.enqueue(
                strategy_id=strategy_id,
                strategy_version=hypothesis.version,
                stage=stage,
                parameters={
                    "candidate_id": candidate.candidate_id,
                    **candidate.parameters,
                },
                dataset_ref=dataset_ref,
                max_attempts=max_attempts,
            )
            for candidate in candidates
        )
        return EmittedExperimentFamily(
            strategy_id=strategy_id,
            strategy_version=hypothesis.version,
            hypothesis_fingerprint=hypothesis.fingerprint,
            experiment_ids=experiment_ids,
        )
