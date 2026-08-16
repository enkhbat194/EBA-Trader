"""EBA Trader domain package.

V1 is research-only by default. Real-money execution is intentionally not exposed here.
"""

from .domain import Decision, ExecutionMode, MarketRegime, TradeProposal

__all__ = [
    "Decision",
    "ExecutionMode",
    "MarketRegime",
    "TradeProposal",
]
