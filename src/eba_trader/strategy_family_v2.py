from __future__ import annotations

import itertools
import math
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from enum import StrEnum

from .research_evidence import canonical_json, sha256_text
from .strategy_discovery_v2 import MAX_CANDIDATES_PER_FAMILY, DiscoveryCandidate

MAX_DECLARED_PARAMETER_COMBINATIONS = 100_000


class StrategyDataPlane(StrEnum):
    PRICE_VOLUME = "price_volume"
    EXECUTED_ORDER_FLOW = "executed_order_flow"
    FUNDING_BASIS = "funding_basis"
    CROSS_MARKET = "cross_market"
    HYBRID = "hybrid"


@dataclass(frozen=True, slots=True)
class ParameterAxis:
    name: str
    values: tuple[object, ...]

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise ValueError("parameter axis name is required")
        if not self.values:
            raise ValueError("parameter axis values cannot be empty")
        stable = tuple(canonical_json({"value": value}) for value in self.values)
        if len(stable) != len(set(stable)):
            raise ValueError(f"duplicate values in parameter axis: {self.name}")

    def as_dict(self) -> dict[str, object]:
        return {"name": self.name, "values": list(self.values)}


@dataclass(frozen=True, slots=True)
class StrategyFamilyV2:
    family_id: str
    economic_mechanism: str
    data_plane: StrategyDataPlane
    timeframe: str
    features: tuple[str, ...]
    parameter_axes: tuple[ParameterAxis, ...]
    version: int = 1

    def __post_init__(self) -> None:
        if not self.family_id.strip():
            raise ValueError("family_id is required")
        if not self.economic_mechanism.strip():
            raise ValueError("economic_mechanism is required")
        if not self.timeframe.strip():
            raise ValueError("timeframe is required")
        if self.version < 1:
            raise ValueError("family version must be positive")
        if not self.features:
            raise ValueError("family features cannot be empty")
        if len(self.features) != len(set(self.features)):
            raise ValueError("family features must be unique")
        if not self.parameter_axes:
            raise ValueError("family parameter axes cannot be empty")
        axis_names = tuple(axis.name for axis in self.parameter_axes)
        if len(axis_names) != len(set(axis_names)):
            raise ValueError("parameter axis names must be unique")
        if self.parameter_combination_count > MAX_DECLARED_PARAMETER_COMBINATIONS:
            raise ValueError(
                "declared parameter space exceeds hard combination cap "
                f"{MAX_DECLARED_PARAMETER_COMBINATIONS}"
            )

    @property
    def parameter_combination_count(self) -> int:
        return math.prod(len(axis.values) for axis in self.parameter_axes)

    @property
    def definition(self) -> dict[str, object]:
        return {
            "data_plane": self.data_plane.value,
            "economic_mechanism": self.economic_mechanism.strip(),
            "family_id": self.family_id,
            "features": list(self.features),
            "parameter_axes": [axis.as_dict() for axis in self.parameter_axes],
            "timeframe": self.timeframe,
            "version": self.version,
        }

    @property
    def fingerprint(self) -> str:
        return f"fam_{sha256_text(canonical_json(self.definition))[:24]}"


class StrategyFamilyRegistryV2:
    def __init__(self) -> None:
        self._families: dict[str, StrategyFamilyV2] = {}

    def register(self, family: StrategyFamilyV2) -> None:
        existing = self._families.get(family.family_id)
        if existing is not None:
            if existing.fingerprint != family.fingerprint:
                raise ValueError("family_id is immutable; create a new family version/id")
            return
        self._families[family.family_id] = family

    def require(self, family_id: str) -> StrategyFamilyV2:
        try:
            return self._families[family_id]
        except KeyError as exc:
            raise KeyError(f"unknown Strategy Factory v2 family: {family_id}") from exc

    def families(self) -> tuple[StrategyFamilyV2, ...]:
        return tuple(self._families[name] for name in sorted(self._families))


def deterministic_quasi_random_candidates(
    family: StrategyFamilyV2,
    *,
    count: int,
    seed: str,
) -> tuple[DiscoveryCandidate, ...]:
    """Sample a discrete parameter space deterministically without adaptive feedback.

    A Halton-style low-discrepancy sequence chooses one value from each declared axis. If the
    discrete projection collides, probing continues. A deterministic hash-ranked fallback over the
    bounded Cartesian space guarantees completion without using observed performance.
    """

    if not 1 <= count <= MAX_CANDIDATES_PER_FAMILY:
        raise ValueError(f"count must be between 1 and {MAX_CANDIDATES_PER_FAMILY}")
    if not seed.strip():
        raise ValueError("seed is required")
    target = min(count, family.parameter_combination_count)
    offset = int(sha256_text(f"{family.fingerprint}:{seed}")[:12], 16) % 10_000 + 1
    bases = _prime_bases(len(family.parameter_axes))
    seen: set[str] = set()
    parameters: list[dict[str, object]] = []
    probe_limit = max(2_000, target * 200)

    for probe in range(probe_limit):
        point = offset + probe
        parameter_set: dict[str, object] = {}
        for axis, base in zip(family.parameter_axes, bases, strict=True):
            coordinate = _radical_inverse(point, base)
            index = min(int(coordinate * len(axis.values)), len(axis.values) - 1)
            parameter_set[axis.name] = axis.values[index]
        key = canonical_json(parameter_set)
        if key in seen:
            continue
        seen.add(key)
        parameters.append(parameter_set)
        if len(parameters) == target:
            break

    if len(parameters) < target:
        parameters = _hash_ranked_parameter_fallback(
            family,
            seed=seed,
            existing=parameters,
            target=target,
        )

    return tuple(
        DiscoveryCandidate(
            family_id=family.family_id,
            hypothesis_fingerprint=family.fingerprint,
            parameters=parameter_set,
        )
        for parameter_set in parameters
    )


def _hash_ranked_parameter_fallback(
    family: StrategyFamilyV2,
    *,
    seed: str,
    existing: Iterable[Mapping[str, object]],
    target: int,
) -> list[dict[str, object]]:
    names = tuple(axis.name for axis in family.parameter_axes)
    value_lists = tuple(axis.values for axis in family.parameter_axes)
    ranked: list[tuple[str, dict[str, object]]] = []
    for combination in itertools.product(*value_lists):
        parameter_set = dict(zip(names, combination, strict=True))
        key = sha256_text(f"{seed}:{canonical_json(parameter_set)}")
        ranked.append((key, parameter_set))
    ranked.sort(key=lambda item: item[0])

    output = [dict(item) for item in existing]
    seen = {canonical_json(item) for item in output}
    for _, parameter_set in ranked:
        stable = canonical_json(parameter_set)
        if stable in seen:
            continue
        output.append(parameter_set)
        seen.add(stable)
        if len(output) == target:
            break
    return output


def _radical_inverse(index: int, base: int) -> float:
    inverse = 0.0
    factor = 1.0 / base
    while index > 0:
        index, remainder = divmod(index, base)
        inverse += remainder * factor
        factor /= base
    return inverse


def _prime_bases(count: int) -> tuple[int, ...]:
    if count < 1:
        raise ValueError("at least one parameter axis is required")
    primes: list[int] = []
    candidate = 2
    while len(primes) < count:
        if all(candidate % prime for prime in primes if prime * prime <= candidate):
            primes.append(candidate)
        candidate += 1
    return tuple(primes)
