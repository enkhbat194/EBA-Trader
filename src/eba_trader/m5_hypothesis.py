from __future__ import annotations

import math
from dataclasses import dataclass
from enum import StrEnum

from .m5_features import DEFAULT_FEATURE_REGISTRY, FeatureRegistry
from .research_evidence import canonical_json, sha256_text


class ComparisonOperator(StrEnum):
    GT = "gt"
    GTE = "gte"
    LT = "lt"
    LTE = "lte"


class TradeDirection(StrEnum):
    LONG = "long"
    SHORT = "short"


@dataclass(frozen=True, slots=True)
class Condition:
    feature: str
    operator: ComparisonOperator
    value: float

    def __post_init__(self) -> None:
        if not self.feature.strip():
            raise ValueError("condition feature is required")
        if not math.isfinite(self.value):
            raise ValueError("condition value must be finite")

    def as_dict(self) -> dict[str, object]:
        return {
            "feature": self.feature,
            "operator": self.operator.value,
            "value": self.value,
        }


@dataclass(frozen=True, slots=True)
class StrategyHypothesis:
    family: str
    version: int
    direction: TradeDirection
    timeframe: str
    features: tuple[str, ...]
    entry_all: tuple[Condition, ...]
    exit_all: tuple[Condition, ...] = ()
    rationale: str = ""

    def __post_init__(self) -> None:
        if not self.family.strip():
            raise ValueError("strategy family is required")
        if self.version < 1:
            raise ValueError("strategy version must be >= 1")
        if not self.timeframe.strip():
            raise ValueError("timeframe is required")
        if not self.entry_all:
            raise ValueError("at least one entry condition is required")

    def validate(self, registry: FeatureRegistry = DEFAULT_FEATURE_REGISTRY) -> None:
        approved = registry.validate(self.features)
        approved_names = {item.name for item in approved}
        for condition in (*self.entry_all, *self.exit_all):
            if condition.feature not in approved_names:
                raise ValueError(
                    f"condition uses feature not declared by hypothesis: {condition.feature}"
                )
            registry.require(condition.feature)

    def as_dict(self) -> dict[str, object]:
        return {
            "family": self.family,
            "version": self.version,
            "direction": self.direction.value,
            "timeframe": self.timeframe,
            "features": list(self.features),
            "entry_all": [condition.as_dict() for condition in self.entry_all],
            "exit_all": [condition.as_dict() for condition in self.exit_all],
            "rationale": self.rationale.strip(),
        }

    @property
    def fingerprint(self) -> str:
        payload = self.as_dict()
        payload["rationale"] = ""
        return f"hyp_{sha256_text(canonical_json(payload))[:24]}"


def hypothesis_from_mapping(
    payload: dict[str, object],
    registry: FeatureRegistry = DEFAULT_FEATURE_REGISTRY,
) -> StrategyHypothesis:
    allowed = {
        "family",
        "version",
        "direction",
        "timeframe",
        "features",
        "entry_all",
        "exit_all",
        "rationale",
    }
    unknown = sorted(set(payload) - allowed)
    if unknown:
        raise ValueError(f"unsupported hypothesis fields: {', '.join(unknown)}")

    def parse_conditions(name: str) -> tuple[Condition, ...]:
        raw = payload.get(name, [])
        if not isinstance(raw, list):
            raise ValueError(f"{name} must be an array")
        parsed: list[Condition] = []
        for item in raw:
            if not isinstance(item, dict):
                raise ValueError(f"{name} entries must be objects")
            if set(item) - {"feature", "operator", "value"}:
                raise ValueError(f"unsupported {name} condition field")
            value = item.get("value")
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                raise ValueError("condition value must be numeric")
            try:
                operator = ComparisonOperator(str(item.get("operator", "")))
            except ValueError as exc:
                raise ValueError("unsupported condition operator") from exc
            parsed.append(
                Condition(
                    feature=str(item.get("feature", "")),
                    operator=operator,
                    value=float(value),
                )
            )
        return tuple(parsed)

    raw_features = payload.get("features")
    if not isinstance(raw_features, list) or not all(
        isinstance(item, str) for item in raw_features
    ):
        raise ValueError("features must be an array of strings")
    version = payload.get("version")
    if isinstance(version, bool) or not isinstance(version, int):
        raise ValueError("version must be an integer")
    try:
        direction = TradeDirection(str(payload.get("direction", "")))
    except ValueError as exc:
        raise ValueError("unsupported trade direction") from exc

    hypothesis = StrategyHypothesis(
        family=str(payload.get("family", "")),
        version=version,
        direction=direction,
        timeframe=str(payload.get("timeframe", "")),
        features=tuple(raw_features),
        entry_all=parse_conditions("entry_all"),
        exit_all=parse_conditions("exit_all"),
        rationale=str(payload.get("rationale", "")),
    )
    hypothesis.validate(registry)
    return hypothesis
