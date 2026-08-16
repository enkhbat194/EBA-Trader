from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum


class MarketRegime(StrEnum):
    BULL_TREND = "bull_trend"
    BEAR_TREND = "bear_trend"
    RANGE = "range"
    BREAKOUT = "breakout"
    HIGH_VOLATILITY = "high_volatility"
    CHAOS = "chaos"
    UNKNOWN = "unknown"


class Decision(StrEnum):
    BUY = "buy"
    EXIT = "exit"
    NO_TRADE = "no_trade"


class ExecutionMode(StrEnum):
    BACKTEST = "backtest"
    PAPER = "paper"
    SHADOW = "shadow"
    MICRO_LIVE = "micro_live"
    LIVE = "live"


@dataclass(frozen=True, slots=True)
class TradeProposal:
    strategy: str
    decision: Decision
    regime: MarketRegime
    confidence: float
    entry_price: float | None = None
    stop_price: float | None = None
    target_price: float | None = None
    reason_codes: tuple[str, ...] = field(default_factory=tuple)
    explanation: str = ""

    def __post_init__(self) -> None:
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError("confidence must be between 0 and 1")

        if self.decision is Decision.BUY:
            if self.entry_price is None or self.entry_price <= 0:
                raise ValueError("BUY proposals require a positive entry_price")
            if self.stop_price is None or self.stop_price <= 0:
                raise ValueError("BUY proposals require a positive stop_price")
            if self.stop_price >= self.entry_price:
                raise ValueError("V1 long-only BUY requires stop_price < entry_price")

        for name, value in (
            ("entry_price", self.entry_price),
            ("stop_price", self.stop_price),
            ("target_price", self.target_price),
        ):
            if value is not None and value <= 0:
                raise ValueError(f"{name} must be positive when provided")
