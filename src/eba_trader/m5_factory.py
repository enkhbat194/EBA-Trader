from __future__ import annotations

import itertools
from dataclasses import dataclass
from typing import Any

from .m5_hypothesis import StrategyHypothesis
from .research_evidence import canonical_json, sha256_text

MAX_PARAMETER_VARIANTS = 500


@dataclass(frozen=True, slots=True)
class ParameterFamily:
    values: dict[str, tuple[object, ...]]

    def __post_init__(self) -> None:
        if not self.values:
            raise ValueError("parameter family cannot be empty")
        for name, candidates in self.values.items():
            if not name.strip():
                raise ValueError("parameter name is required")
            if not candidates:
                raise ValueError(f"parameter candidates cannot be empty: {name}")
            if len(candidates) != len(set(_stable_value(item) for item in candidates)):
                raise ValueError(f"duplicate parameter candidates: {name}")
        if self.variant_count > MAX_PARAMETER_VARIANTS:
            raise ValueError(
                f"parameter family exceeds hard cap {MAX_PARAMETER_VARIANTS}: {self.variant_count}"
            )

    @property
    def variant_count(self) -> int:
        count = 1
        for candidates in self.values.values():
            count *= len(candidates)
        return count

    def expand(self) -> tuple[dict[str, object], ...]:
        names = tuple(sorted(self.values))
        candidate_lists = tuple(self.values[name] for name in names)
        return tuple(
            dict(zip(names, combination, strict=True))
            for combination in itertools.product(*candidate_lists)
        )


@dataclass(frozen=True, slots=True)
class StrategyCandidate:
    candidate_id: str
    hypothesis_fingerprint: str
    parameters: dict[str, object]


class StrategyCandidateFactory:
    def expand(
        self,
        hypothesis: StrategyHypothesis,
        parameters: ParameterFamily,
    ) -> tuple[StrategyCandidate, ...]:
        hypothesis.validate()
        candidates: list[StrategyCandidate] = []
        for parameter_set in parameters.expand():
            payload: dict[str, Any] = {
                "hypothesis": hypothesis.fingerprint,
                "parameters": parameter_set,
            }
            candidate_id = f"cand_{sha256_text(canonical_json(payload))[:24]}"
            candidates.append(
                StrategyCandidate(
                    candidate_id=candidate_id,
                    hypothesis_fingerprint=hypothesis.fingerprint,
                    parameters=parameter_set,
                )
            )
        return tuple(candidates)


def deduplicate_hypotheses(
    hypotheses: tuple[StrategyHypothesis, ...],
) -> tuple[StrategyHypothesis, ...]:
    seen: set[str] = set()
    output: list[StrategyHypothesis] = []
    for hypothesis in hypotheses:
        hypothesis.validate()
        if hypothesis.fingerprint in seen:
            continue
        seen.add(hypothesis.fingerprint)
        output.append(hypothesis)
    return tuple(output)


def _stable_value(value: object) -> str:
    return canonical_json({"value": value})
