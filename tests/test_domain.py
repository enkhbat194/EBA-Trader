import pytest

from eba_trader.domain import Decision, MarketRegime, TradeProposal


def test_long_requires_stop_below_entry() -> None:
    with pytest.raises(ValueError):
        TradeProposal(
            strategy="trend",
            decision=Decision.LONG,
            regime=MarketRegime.BULL_TREND,
            confidence=0.8,
            entry_price=100.0,
            stop_price=101.0,
        )


def test_short_requires_stop_above_entry() -> None:
    with pytest.raises(ValueError):
        TradeProposal(
            strategy="trend-short",
            decision=Decision.SHORT,
            regime=MarketRegime.BEAR_TREND,
            confidence=0.8,
            entry_price=100.0,
            stop_price=99.0,
        )


def test_valid_short_proposal() -> None:
    proposal = TradeProposal(
        strategy="trend-short",
        decision=Decision.SHORT,
        regime=MarketRegime.BEAR_TREND,
        confidence=0.8,
        entry_price=100.0,
        stop_price=102.0,
    )
    assert proposal.decision is Decision.SHORT


def test_legacy_buy_alias_maps_to_long() -> None:
    assert Decision.BUY is Decision.LONG
    assert Decision("buy") is Decision.LONG


def test_no_trade_does_not_require_prices() -> None:
    proposal = TradeProposal(
        strategy="no_trade",
        decision=Decision.NO_TRADE,
        regime=MarketRegime.UNKNOWN,
        confidence=1.0,
    )
    assert proposal.decision is Decision.NO_TRADE
