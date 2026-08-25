"""EBA Trader domain package.

Research and paper validation are exposed here. Real-money execution remains intentionally
locked behind separately validated execution and lifecycle gates.
"""

from .domain import Decision, ExecutionMode, MarketRegime, TradeProposal
from .experiment_queue import ExperimentClaim, ExperimentStatus
from .lifecycle import LifecycleTransition, StrategyLifecycle

__all__ = [
    "Decision",
    "ExecutionMode",
    "ExperimentClaim",
    "ExperimentStatus",
    "LifecycleTransition",
    "MarketRegime",
    "StrategyLifecycle",
    "TradeProposal",
]
