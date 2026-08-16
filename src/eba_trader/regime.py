from __future__ import annotations

from dataclasses import dataclass

from .domain import MarketRegime


@dataclass(frozen=True, slots=True)
class RegimeFeatures:
    """Normalized regime features produced by a future feature engine.

    All strength/score values are expected in [0, 1]. `trend_direction` is in [-1, 1].
    This keeps the baseline classifier independent from any specific indicator library.
    """

    trend_direction: float
    trend_strength: float
    range_score: float
    breakout_score: float
    volatility_score: float
    chaos_score: float

    def __post_init__(self) -> None:
        if not -1.0 <= self.trend_direction <= 1.0:
            raise ValueError("trend_direction must be in [-1, 1]")

        for name in (
            "trend_strength",
            "range_score",
            "breakout_score",
            "volatility_score",
            "chaos_score",
        ):
            value = getattr(self, name)
            if not 0.0 <= value <= 1.0:
                raise ValueError(f"{name} must be in [0, 1]")


@dataclass(frozen=True, slots=True)
class RegimeConfig:
    chaos_threshold: float = 0.80
    high_volatility_threshold: float = 0.85
    breakout_threshold: float = 0.75
    trend_strength_threshold: float = 0.65
    trend_direction_threshold: float = 0.20
    range_threshold: float = 0.65
    max_trend_strength_for_range: float = 0.55


class RegimeDetector:
    """Deterministic baseline classifier.

    This is scaffolding, not a validated trading edge. Thresholds must be calibrated and
    tested under `BACKTEST_PROTOCOL.md` before they affect any capital-bearing mode.
    """

    def __init__(self, config: RegimeConfig | None = None) -> None:
        self.config = config or RegimeConfig()

    def classify(self, features: RegimeFeatures) -> MarketRegime:
        cfg = self.config

        if features.chaos_score >= cfg.chaos_threshold:
            return MarketRegime.CHAOS

        if features.volatility_score >= cfg.high_volatility_threshold:
            return MarketRegime.HIGH_VOLATILITY

        if features.breakout_score >= cfg.breakout_threshold:
            return MarketRegime.BREAKOUT

        if features.trend_strength >= cfg.trend_strength_threshold:
            if features.trend_direction >= cfg.trend_direction_threshold:
                return MarketRegime.BULL_TREND
            if features.trend_direction <= -cfg.trend_direction_threshold:
                return MarketRegime.BEAR_TREND

        if (
            features.range_score >= cfg.range_threshold
            and features.trend_strength <= cfg.max_trend_strength_for_range
        ):
            return MarketRegime.RANGE

        return MarketRegime.UNKNOWN
