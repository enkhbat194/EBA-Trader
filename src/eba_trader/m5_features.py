from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class FeatureFamily(StrEnum):
    CANDLE = "candle"
    ORDER_FLOW = "order_flow"
    ORDER_BOOK = "order_book"


@dataclass(frozen=True, slots=True)
class FeatureDefinition:
    name: str
    family: FeatureFamily
    enabled: bool = True


class FeatureRegistry:
    def __init__(self, definitions: tuple[FeatureDefinition, ...]) -> None:
        names = [definition.name for definition in definitions]
        if len(names) != len(set(names)):
            raise ValueError("feature names must be unique")
        self._definitions = {definition.name: definition for definition in definitions}

    def require(self, name: str) -> FeatureDefinition:
        try:
            feature = self._definitions[name]
        except KeyError as exc:
            raise ValueError(f"unsupported feature: {name}") from exc
        if not feature.enabled:
            raise ValueError(f"feature is not enabled: {name}")
        return feature

    def validate(self, names: tuple[str, ...]) -> tuple[FeatureDefinition, ...]:
        if not names:
            raise ValueError("at least one feature is required")
        if len(names) != len(set(names)):
            raise ValueError("feature list contains duplicates")
        return tuple(self.require(name) for name in names)


DEFAULT_FEATURE_REGISTRY = FeatureRegistry(
    (
        FeatureDefinition("close", FeatureFamily.CANDLE),
        FeatureDefinition("ema_fast", FeatureFamily.CANDLE),
        FeatureDefinition("ema_slow", FeatureFamily.CANDLE),
        FeatureDefinition("rsi", FeatureFamily.CANDLE),
        FeatureDefinition("atr", FeatureFamily.CANDLE),
        FeatureDefinition("volume", FeatureFamily.CANDLE),
        FeatureDefinition("of_buy_volume", FeatureFamily.ORDER_FLOW),
        FeatureDefinition("of_sell_volume", FeatureFamily.ORDER_FLOW),
        FeatureDefinition("of_delta", FeatureFamily.ORDER_FLOW),
        FeatureDefinition("of_delta_ratio", FeatureFamily.ORDER_FLOW),
        FeatureDefinition("of_cvd", FeatureFamily.ORDER_FLOW),
        FeatureDefinition("of_poc_price", FeatureFamily.ORDER_FLOW),
        FeatureDefinition("of_stacked_imbalance", FeatureFamily.ORDER_FLOW),
        FeatureDefinition("of_absorption", FeatureFamily.ORDER_FLOW, enabled=False),
        FeatureDefinition("of_exhaustion", FeatureFamily.ORDER_FLOW, enabled=False),
        FeatureDefinition("lob_depth_imbalance", FeatureFamily.ORDER_BOOK, enabled=False),
    )
)
