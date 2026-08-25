from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any

from .m5_factory import ParameterFamily
from .m5_hypothesis import StrategyHypothesis


@dataclass(frozen=True, slots=True)
class CheapScreenPolicy:
    max_features: int = 8
    max_entry_conditions: int = 6
    max_exit_conditions: int = 4
    max_parameter_variants: int = 200

    def __post_init__(self) -> None:
        if min(
            self.max_features,
            self.max_entry_conditions,
            self.max_exit_conditions,
            self.max_parameter_variants,
        ) < 1:
            raise ValueError("cheap-screen limits must be positive")


@dataclass(frozen=True, slots=True)
class CheapScreenVerdict:
    passed: bool
    reasons: tuple[str, ...]


def cheap_screen(
    hypothesis: StrategyHypothesis,
    parameters: ParameterFamily,
    *,
    policy: CheapScreenPolicy | None = None,
) -> CheapScreenVerdict:
    resolved_policy = policy or CheapScreenPolicy()
    hypothesis.validate()
    reasons: list[str] = []
    if len(hypothesis.features) > resolved_policy.max_features:
        reasons.append("too_many_features")
    if len(hypothesis.entry_all) > resolved_policy.max_entry_conditions:
        reasons.append("too_many_entry_conditions")
    if len(hypothesis.exit_all) > resolved_policy.max_exit_conditions:
        reasons.append("too_many_exit_conditions")
    if parameters.variant_count > resolved_policy.max_parameter_variants:
        reasons.append("too_many_parameter_variants")

    order_flow_features = tuple(
        name for name in hypothesis.features if name.startswith("of_")
    )
    if "orderflow" in hypothesis.family and not order_flow_features:
        reasons.append("orderflow_family_without_orderflow_feature")

    return CheapScreenVerdict(passed=not reasons, reasons=tuple(reasons))


@dataclass(frozen=True, slots=True)
class RankedSurvivor:
    experiment_id: str
    score: float
    metrics: dict[str, float]


def rank_survivors(
    experiments: list[dict[str, Any]],
    *,
    limit: int = 20,
) -> tuple[RankedSurvivor, ...]:
    if limit < 1:
        raise ValueError("limit must be >= 1")
    survivors: list[RankedSurvivor] = []
    for experiment in experiments:
        if experiment.get("status") != "passed":
            continue
        metrics = experiment.get("metrics")
        if not isinstance(metrics, dict):
            continue
        required = ("profit_factor", "expectancy", "max_drawdown", "trade_count")
        if any(name not in metrics for name in required):
            continue
        numeric: dict[str, float] = {}
        valid = True
        for name in required:
            value = metrics[name]
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                valid = False
                break
            number = float(value)
            if not math.isfinite(number):
                valid = False
                break
            numeric[name] = number
        if not valid or numeric["trade_count"] < 1:
            continue

        drawdown_penalty = abs(min(numeric["max_drawdown"], 0.0))
        score = (
            numeric["profit_factor"]
            + numeric["expectancy"] * 0.25
            - drawdown_penalty * 2.0
            + min(numeric["trade_count"], 200.0) / 1000.0
        )
        survivors.append(
            RankedSurvivor(
                experiment_id=str(experiment.get("experiment_id", "")),
                score=score,
                metrics=numeric,
            )
        )

    survivors.sort(key=lambda item: (-item.score, item.experiment_id))
    return tuple(survivors[:limit])
