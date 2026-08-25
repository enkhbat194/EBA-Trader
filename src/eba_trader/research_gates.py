from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from enum import StrEnum
from typing import Any

from .research_evidence import canonical_json, sha256_text


class GateOperator(StrEnum):
    GTE = "gte"
    LTE = "lte"
    GT = "gt"
    LT = "lt"
    EQ = "eq"


@dataclass(frozen=True, slots=True)
class GateRule:
    name: str
    metric: str
    operator: GateOperator
    threshold: float

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise ValueError("gate rule name is required")
        if not self.metric.strip():
            raise ValueError("gate rule metric is required")
        if not math.isfinite(self.threshold):
            raise ValueError("gate rule threshold must be finite")

    def as_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "metric": self.metric,
            "operator": self.operator.value,
            "threshold": self.threshold,
        }


@dataclass(frozen=True, slots=True)
class GateSet:
    name: str
    version: int
    rules: tuple[GateRule, ...]

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise ValueError("gate set name is required")
        if self.version < 1:
            raise ValueError("gate set version must be >= 1")
        if not self.rules:
            raise ValueError("gate set requires at least one rule")
        names = [rule.name for rule in self.rules]
        if len(set(names)) != len(names):
            raise ValueError("gate rule names must be unique")

    @classmethod
    def from_mapping(cls, payload: Mapping[str, Any]) -> GateSet:
        allowed = {"name", "version", "rules"}
        unknown = sorted(set(payload) - allowed)
        if unknown:
            raise ValueError(f"Unsupported gate set fields: {', '.join(unknown)}")
        raw_rules = payload.get("rules")
        if not isinstance(raw_rules, Sequence) or isinstance(raw_rules, (str, bytes)):
            raise ValueError("gate set rules must be an array")
        rules: list[GateRule] = []
        for item in raw_rules:
            if not isinstance(item, Mapping):
                raise ValueError("each gate rule must be an object")
            unknown_rule = sorted(set(item) - {"name", "metric", "operator", "threshold"})
            if unknown_rule:
                raise ValueError(f"Unsupported gate rule fields: {', '.join(unknown_rule)}")
            try:
                operator = GateOperator(str(item.get("operator", "")))
            except ValueError as exc:
                raise ValueError(f"Unsupported gate operator: {item.get('operator')!r}") from exc
            threshold = item.get("threshold")
            if isinstance(threshold, bool) or not isinstance(threshold, (int, float)):
                raise ValueError("gate rule threshold must be numeric")
            version = payload.get("version")
            if isinstance(version, bool) or not isinstance(version, int):
                raise ValueError("gate set version must be an integer")
            rules.append(
                GateRule(
                    name=str(item.get("name", "")),
                    metric=str(item.get("metric", "")),
                    operator=operator,
                    threshold=float(threshold),
                )
            )
        version = payload.get("version")
        if isinstance(version, bool) or not isinstance(version, int):
            raise ValueError("gate set version must be an integer")
        return cls(
            name=str(payload.get("name", "")),
            version=version,
            rules=tuple(rules),
        )

    def as_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "version": self.version,
            "rules": [rule.as_dict() for rule in self.rules],
        }

    @property
    def definition_sha256(self) -> str:
        return sha256_text(canonical_json(self.as_dict()))

    @property
    def gate_set_id(self) -> str:
        return f"gset_{self.definition_sha256[:24]}"


@dataclass(frozen=True, slots=True)
class GateResult:
    rule_name: str
    metric: str
    operator: GateOperator
    threshold: float
    actual: float | None
    passed: bool
    reason: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "rule_name": self.rule_name,
            "metric": self.metric,
            "operator": self.operator.value,
            "threshold": self.threshold,
            "actual": self.actual,
            "passed": self.passed,
            "reason": self.reason,
        }


@dataclass(frozen=True, slots=True)
class GateEvaluation:
    gate_set_id: str
    passed: bool
    results: tuple[GateResult, ...]

    def as_dict(self) -> dict[str, Any]:
        return {
            "gate_set_id": self.gate_set_id,
            "passed": self.passed,
            "results": [result.as_dict() for result in self.results],
        }


def _compare(actual: float, operator: GateOperator, threshold: float) -> bool:
    if operator is GateOperator.GTE:
        return actual >= threshold
    if operator is GateOperator.LTE:
        return actual <= threshold
    if operator is GateOperator.GT:
        return actual > threshold
    if operator is GateOperator.LT:
        return actual < threshold
    if operator is GateOperator.EQ:
        return actual == threshold
    raise AssertionError(f"Unhandled gate operator: {operator}")


def evaluate_gate_set(gate_set: GateSet, metrics: Mapping[str, Any]) -> GateEvaluation:
    results: list[GateResult] = []
    for rule in gate_set.rules:
        raw = metrics.get(rule.metric)
        if isinstance(raw, bool) or not isinstance(raw, (int, float)):
            results.append(
                GateResult(
                    rule_name=rule.name,
                    metric=rule.metric,
                    operator=rule.operator,
                    threshold=rule.threshold,
                    actual=None,
                    passed=False,
                    reason="metric_missing_or_non_numeric",
                )
            )
            continue
        actual = float(raw)
        if not math.isfinite(actual):
            results.append(
                GateResult(
                    rule_name=rule.name,
                    metric=rule.metric,
                    operator=rule.operator,
                    threshold=rule.threshold,
                    actual=None,
                    passed=False,
                    reason="metric_non_finite",
                )
            )
            continue
        passed = _compare(actual, rule.operator, rule.threshold)
        results.append(
            GateResult(
                rule_name=rule.name,
                metric=rule.metric,
                operator=rule.operator,
                threshold=rule.threshold,
                actual=actual,
                passed=passed,
                reason="passed" if passed else "threshold_not_met",
            )
        )
    return GateEvaluation(
        gate_set_id=gate_set.gate_set_id,
        passed=all(result.passed for result in results),
        results=tuple(results),
    )
