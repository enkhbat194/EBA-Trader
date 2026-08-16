from eba_trader.domain import MarketRegime
from eba_trader.regime import RegimeDetector, RegimeFeatures


def test_chaos_has_priority() -> None:
    features = RegimeFeatures(
        trend_direction=0.9,
        trend_strength=0.9,
        range_score=0.1,
        breakout_score=0.9,
        volatility_score=0.9,
        chaos_score=0.95,
    )
    assert RegimeDetector().classify(features) is MarketRegime.CHAOS


def test_bull_trend_classification() -> None:
    features = RegimeFeatures(
        trend_direction=0.8,
        trend_strength=0.8,
        range_score=0.1,
        breakout_score=0.2,
        volatility_score=0.3,
        chaos_score=0.1,
    )
    assert RegimeDetector().classify(features) is MarketRegime.BULL_TREND


def test_range_classification() -> None:
    features = RegimeFeatures(
        trend_direction=0.0,
        trend_strength=0.3,
        range_score=0.8,
        breakout_score=0.1,
        volatility_score=0.2,
        chaos_score=0.1,
    )
    assert RegimeDetector().classify(features) is MarketRegime.RANGE


def test_ambiguous_market_is_unknown() -> None:
    features = RegimeFeatures(
        trend_direction=0.1,
        trend_strength=0.5,
        range_score=0.5,
        breakout_score=0.4,
        volatility_score=0.4,
        chaos_score=0.2,
    )
    assert RegimeDetector().classify(features) is MarketRegime.UNKNOWN
