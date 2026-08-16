from eba_trader.data_health import MarketDataHealth
from eba_trader.domain import Decision, MarketRegime, TradeProposal
from eba_trader.risk import RiskContext, RiskEngine, RiskStatus
from eba_trader.safety import apply_market_data_health


def _context() -> RiskContext:
    return RiskContext(
        equity=1_000.0,
        start_of_day_equity=1_000.0,
        peak_equity=1_000.0,
    )


def _buy() -> TradeProposal:
    return TradeProposal(
        strategy="trend",
        decision=Decision.BUY,
        regime=MarketRegime.BULL_TREND,
        confidence=0.8,
        entry_price=100.0,
        stop_price=95.0,
    )


def test_starting_data_feed_halts_trade() -> None:
    health = MarketDataHealth(max_age_ms=1_000)
    snapshot = health.snapshot(now_ns=1_000_000_000)
    context = apply_market_data_health(_context(), snapshot)

    assessment = RiskEngine().evaluate(_buy(), context)

    assert assessment.status is RiskStatus.HALT
    assert "STALE_MARKET_DATA" in assessment.reason_codes


def test_stale_data_feed_halts_trade() -> None:
    health = MarketDataHealth(max_age_ms=1_000)
    health.mark_event(received_ns=1_000_000_000)
    snapshot = health.snapshot(now_ns=2_000_000_001)
    context = apply_market_data_health(_context(), snapshot)

    assessment = RiskEngine().evaluate(_buy(), context)

    assert assessment.status is RiskStatus.HALT
    assert "STALE_MARKET_DATA" in assessment.reason_codes


def test_healthy_data_feed_can_reach_normal_risk_checks() -> None:
    health = MarketDataHealth(max_age_ms=1_000)
    health.mark_event(received_ns=1_000_000_000)
    snapshot = health.snapshot(now_ns=1_500_000_000)
    context = apply_market_data_health(_context(), snapshot)

    assessment = RiskEngine().evaluate(_buy(), context)

    assert assessment.status is RiskStatus.ALLOW
