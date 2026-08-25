from __future__ import annotations

from dataclasses import dataclass

from .m5_factory import ParameterFamily
from .m5_hypothesis import (
    ComparisonOperator,
    Condition,
    StrategyHypothesis,
    TradeDirection,
)


@dataclass(frozen=True, slots=True)
class StrategyFamilyTemplate:
    name: str
    features: tuple[str, ...]
    parameter_family: ParameterFamily

    def build(
        self,
        *,
        version: int,
        direction: TradeDirection,
        timeframe: str,
    ) -> StrategyHypothesis:
        if self.name == "ema_momentum":
            return StrategyHypothesis(
                family=self.name,
                version=version,
                direction=direction,
                timeframe=timeframe,
                features=self.features,
                entry_all=(
                    Condition("ema_fast", ComparisonOperator.GT, 0.0),
                    Condition("rsi", ComparisonOperator.GT, 50.0),
                ),
                rationale="bounded candle momentum family",
            )
        if self.name == "ema_orderflow_momentum":
            return StrategyHypothesis(
                family=self.name,
                version=version,
                direction=direction,
                timeframe=timeframe,
                features=self.features,
                entry_all=(
                    Condition("ema_fast", ComparisonOperator.GT, 0.0),
                    Condition("of_delta_ratio", ComparisonOperator.GT, 0.0),
                ),
                rationale="bounded EMA plus executed order-flow family",
            )
        raise ValueError(f"unsupported strategy family template: {self.name}")


EMA_MOMENTUM = StrategyFamilyTemplate(
    name="ema_momentum",
    features=("ema_fast", "ema_slow", "rsi"),
    parameter_family=ParameterFamily(
        {
            "ema_fast": (8, 13, 21),
            "ema_slow": (34, 55),
            "rsi_threshold": (50.0, 55.0, 60.0),
        }
    ),
)

EMA_ORDERFLOW_MOMENTUM = StrategyFamilyTemplate(
    name="ema_orderflow_momentum",
    features=("ema_fast", "ema_slow", "of_delta_ratio", "of_cvd"),
    parameter_family=ParameterFamily(
        {
            "ema_fast": (8, 13, 21),
            "ema_slow": (34, 55),
            "delta_ratio_threshold": (0.05, 0.1, 0.2),
        }
    ),
)

APPROVED_FAMILY_TEMPLATES = {
    EMA_MOMENTUM.name: EMA_MOMENTUM,
    EMA_ORDERFLOW_MOMENTUM.name: EMA_ORDERFLOW_MOMENTUM,
}
