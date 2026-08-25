import pytest

from eba_trader.lifecycle import (
    LifecycleTransition,
    StrategyLifecycle,
    allowed_transitions,
)


def test_generated_can_promote_to_backtested() -> None:
    transition = LifecycleTransition(
        previous=StrategyLifecycle.GENERATED,
        current=StrategyLifecycle.BACKTESTED,
        reason="Development backtest completed",
        evidence_ref="experiment:42",
    )
    assert transition.current is StrategyLifecycle.BACKTESTED


def test_promotion_requires_evidence_reference() -> None:
    with pytest.raises(ValueError, match="evidence_ref"):
        LifecycleTransition(
            previous=StrategyLifecycle.BACKTESTED,
            current=StrategyLifecycle.OOS_VERIFIED,
            reason="Frozen OOS passed",
        )


def test_cannot_skip_lifecycle_gates() -> None:
    with pytest.raises(ValueError, match="not allowed"):
        LifecycleTransition(
            previous=StrategyLifecycle.GENERATED,
            current=StrategyLifecycle.PAPER_VERIFIED,
            reason="Trying to skip gates",
            evidence_ref="paper:1",
        )


def test_verified_strategy_can_be_quarantined() -> None:
    assert StrategyLifecycle.QUARANTINED in allowed_transitions(
        StrategyLifecycle.PAPER_VERIFIED
    )


def test_quarantine_must_retest_before_reentering_promotion_path() -> None:
    assert allowed_transitions(StrategyLifecycle.QUARANTINED) == frozenset(
        {
            StrategyLifecycle.RETEST_REQUIRED,
            StrategyLifecycle.RETIRED,
        }
    )
