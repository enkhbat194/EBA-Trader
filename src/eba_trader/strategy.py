from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from .domain import Decision, MarketRegime, TradeProposal


@dataclass(frozen=True, slots=True)
class StrategyContext:
    symbol: str
    regime: MarketRegime
    reference_price: float


class Strategy(Protocol):
    name: str
    compatible_regimes: frozenset[MarketRegime]

    def evaluate(self, context: StrategyContext) -> TradeProposal:
        """Return a proposal only; strategies never submit orders directly."""
        ...


class NoTradeStrategy:
    name = "no_trade"
    compatible_regimes = frozenset(MarketRegime)

    def evaluate(self, context: StrategyContext) -> TradeProposal:
        return TradeProposal(
            strategy=self.name,
            decision=Decision.NO_TRADE,
            regime=context.regime,
            confidence=1.0,
            reason_codes=("NO_VALIDATED_EDGE",),
            explanation="No validated trade is available for the current state.",
        )
