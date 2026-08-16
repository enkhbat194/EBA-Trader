from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from .domain import Decision, ExecutionMode, TradeProposal


class RiskStatus(StrEnum):
    ALLOW = "allow"
    DENY = "deny"
    HALT = "halt"


@dataclass(frozen=True, slots=True)
class RiskConfig:
    risk_per_trade: float = 0.005
    max_daily_loss: float = 0.02
    max_drawdown: float = 0.08
    max_open_positions: int = 1
    max_position_notional_pct: float = 1.0
    allow_live_execution: bool = False

    def __post_init__(self) -> None:
        for name, value in (
            ("risk_per_trade", self.risk_per_trade),
            ("max_daily_loss", self.max_daily_loss),
            ("max_drawdown", self.max_drawdown),
            ("max_position_notional_pct", self.max_position_notional_pct),
        ):
            if not 0 < value <= 1:
                raise ValueError(f"{name} must be in (0, 1]")

        if self.max_open_positions < 1:
            raise ValueError("max_open_positions must be >= 1")


@dataclass(frozen=True, slots=True)
class RiskContext:
    equity: float
    start_of_day_equity: float
    peak_equity: float
    realized_pnl_today: float = 0.0
    open_positions: int = 0
    data_fresh: bool = True
    account_reconciled: bool = True
    volatility_ok: bool = True
    execution_mode: ExecutionMode = ExecutionMode.PAPER


@dataclass(frozen=True, slots=True)
class RiskAssessment:
    status: RiskStatus
    reason_codes: tuple[str, ...]
    approved_quantity: float = 0.0
    risk_budget: float = 0.0

    @property
    def allowed(self) -> bool:
        return self.status is RiskStatus.ALLOW


class RiskEngine:
    """Deterministic V1 risk gate.

    This engine has veto authority over strategy and AI output. Real-money modes are
    locked unless `allow_live_execution` is deliberately changed in validated future code.
    """

    def __init__(self, config: RiskConfig | None = None) -> None:
        self.config = config or RiskConfig()

    def evaluate(self, proposal: TradeProposal, context: RiskContext) -> RiskAssessment:
        hard_halt_reasons = self._hard_halt_reasons(context)
        if hard_halt_reasons:
            return RiskAssessment(RiskStatus.HALT, tuple(hard_halt_reasons))

        if proposal.decision is Decision.NO_TRADE:
            return RiskAssessment(RiskStatus.ALLOW, ("NO_TRADE",))

        if proposal.decision is Decision.EXIT:
            return RiskAssessment(RiskStatus.ALLOW, ("EXIT_REDUCES_EXPOSURE",))

        deny_reasons: list[str] = []
        if context.open_positions >= self.config.max_open_positions:
            deny_reasons.append("MAX_OPEN_POSITIONS")

        if proposal.entry_price is None or proposal.stop_price is None:
            deny_reasons.append("MISSING_ENTRY_OR_STOP")

        if deny_reasons:
            return RiskAssessment(RiskStatus.DENY, tuple(deny_reasons))

        assert proposal.entry_price is not None
        assert proposal.stop_price is not None

        unit_risk = proposal.entry_price - proposal.stop_price
        if unit_risk <= 0:
            return RiskAssessment(RiskStatus.DENY, ("INVALID_UNIT_RISK",))

        risk_budget = context.equity * self.config.risk_per_trade
        risk_sized_quantity = risk_budget / unit_risk

        max_notional = context.equity * self.config.max_position_notional_pct
        cash_capped_quantity = max_notional / proposal.entry_price
        approved_quantity = min(risk_sized_quantity, cash_capped_quantity)

        if approved_quantity <= 0:
            return RiskAssessment(RiskStatus.DENY, ("NON_POSITIVE_QUANTITY",))

        return RiskAssessment(
            status=RiskStatus.ALLOW,
            reason_codes=("RISK_CHECKS_PASSED",),
            approved_quantity=approved_quantity,
            risk_budget=risk_budget,
        )

    def _hard_halt_reasons(self, context: RiskContext) -> list[str]:
        reasons: list[str] = []

        if context.execution_mode in {ExecutionMode.MICRO_LIVE, ExecutionMode.LIVE}:
            if not self.config.allow_live_execution:
                reasons.append("LIVE_EXECUTION_LOCKED")

        if not context.data_fresh:
            reasons.append("STALE_MARKET_DATA")
        if not context.account_reconciled:
            reasons.append("ACCOUNT_STATE_MISMATCH")
        if not context.volatility_ok:
            reasons.append("VOLATILITY_OUTSIDE_ENVELOPE")

        if context.equity <= 0 or context.start_of_day_equity <= 0 or context.peak_equity <= 0:
            reasons.append("INVALID_EQUITY_STATE")
            return reasons

        daily_loss_fraction = max(0.0, -context.realized_pnl_today) / context.start_of_day_equity
        if daily_loss_fraction >= self.config.max_daily_loss:
            reasons.append("DAILY_LOSS_LIMIT")

        drawdown_fraction = max(0.0, context.peak_equity - context.equity) / context.peak_equity
        if drawdown_fraction >= self.config.max_drawdown:
            reasons.append("MAX_DRAWDOWN_LIMIT")

        return reasons
