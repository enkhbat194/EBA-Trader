from eba_trader.domain import Decision, ExecutionMode, MarketRegime, TradeProposal
from eba_trader.risk import RiskContext, RiskEngine, RiskStatus


def _long() -> TradeProposal:
    return TradeProposal(
        strategy="trend",
        decision=Decision.LONG,
        regime=MarketRegime.BULL_TREND,
        confidence=0.8,
        entry_price=100.0,
        stop_price=95.0,
    )


def _short() -> TradeProposal:
    return TradeProposal(
        strategy="trend-short",
        decision=Decision.SHORT,
        regime=MarketRegime.BEAR_TREND,
        confidence=0.8,
        entry_price=100.0,
        stop_price=105.0,
    )


def test_live_execution_is_locked_by_default() -> None:
    assessment = RiskEngine().evaluate(
        _long(),
        RiskContext(
            equity=1_000.0,
            start_of_day_equity=1_000.0,
            peak_equity=1_000.0,
            execution_mode=ExecutionMode.LIVE,
        ),
    )
    assert assessment.status is RiskStatus.HALT
    assert "LIVE_EXECUTION_LOCKED" in assessment.reason_codes


def test_stale_data_halts_trading() -> None:
    assessment = RiskEngine().evaluate(
        _long(),
        RiskContext(
            equity=1_000.0,
            start_of_day_equity=1_000.0,
            peak_equity=1_000.0,
            data_fresh=False,
        ),
    )
    assert assessment.status is RiskStatus.HALT
    assert "STALE_MARKET_DATA" in assessment.reason_codes


def test_position_size_respects_risk_budget_and_notional_cap() -> None:
    assessment = RiskEngine().evaluate(
        _long(),
        RiskContext(
            equity=1_000.0,
            start_of_day_equity=1_000.0,
            peak_equity=1_000.0,
        ),
    )

    # 0.5% of $1,000 = $5 risk. Entry-stop distance = $5 -> 1 BTC by risk.
    assert assessment.status is RiskStatus.ALLOW
    assert assessment.risk_budget == 5.0
    assert assessment.approved_quantity == 1.0


def test_short_uses_same_stop_distance_risk_budget() -> None:
    assessment = RiskEngine().evaluate(
        _short(),
        RiskContext(
            equity=1_000.0,
            start_of_day_equity=1_000.0,
            peak_equity=1_000.0,
        ),
    )
    assert assessment.status is RiskStatus.ALLOW
    assert assessment.risk_budget == 5.0
    assert assessment.approved_quantity == 1.0


def test_daily_loss_limit_halts() -> None:
    assessment = RiskEngine().evaluate(
        _long(),
        RiskContext(
            equity=970.0,
            start_of_day_equity=1_000.0,
            peak_equity=1_000.0,
            realized_pnl_today=-20.0,
        ),
    )
    assert assessment.status is RiskStatus.HALT
    assert "DAILY_LOSS_LIMIT" in assessment.reason_codes


def test_no_trade_is_always_safe_when_system_health_is_good() -> None:
    proposal = TradeProposal(
        strategy="no_trade",
        decision=Decision.NO_TRADE,
        regime=MarketRegime.UNKNOWN,
        confidence=1.0,
    )
    assessment = RiskEngine().evaluate(
        proposal,
        RiskContext(
            equity=1_000.0,
            start_of_day_equity=1_000.0,
            peak_equity=1_000.0,
        ),
    )
    assert assessment.status is RiskStatus.ALLOW
    assert assessment.approved_quantity == 0.0
