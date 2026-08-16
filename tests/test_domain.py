import pytest

from eba_trader.domain import Decision, MarketRegime, TradeProposal


def test_buy_requires_stop_below_entry() -> None:
    with pytest.raises(ValueError):
        TradeProposal(
            strategy="trend",
            decision=Decision.BUY,
            regime=MarketRegime.BULL_TREND,
            confidence=0.8,
            entry_price=100.0,
            stop_price=101.0,
        )


def test_no_trade_does_not_require_prices() -> None:
    proposal = TradeProposal(
        strategy="no_trade",
        decision=Decision.NO_TRADE,
        regime=MarketRegime.UNKNOWN,
        confidence=1.0,
    )
    assert proposal.decision is Decision.NO_TRADE
