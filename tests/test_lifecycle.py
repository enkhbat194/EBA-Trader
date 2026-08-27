import pytest

from eba_trader.lifecycle import (
    CURRENT_LIFECYCLE_POLICY_VERSION,
    LEGACY_LIFECYCLE_POLICY_VERSION,
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
    assert transition.policy_version == CURRENT_LIFECYCLE_POLICY_VERSION


def test_v2_requires_robustness_before_frozen_oos() -> None:
    assert allowed_transitions(StrategyLifecycle.BACKTESTED) == frozenset(
        {
            StrategyLifecycle.ROBUSTNESS_VERIFIED,
            StrategyLifecycle.REJECTED,
            StrategyLifecycle.QUARANTINED,
        }
    )
    with pytest.raises(ValueError, match="not allowed under policy v2"):
        LifecycleTransition(
            previous=StrategyLifecycle.BACKTESTED,
            current=StrategyLifecycle.OOS_VERIFIED,
            reason="Trying to open frozen OOS early",
            evidence_ref="oos:too-early",
        )


def test_robustness_then_oos_promotions_require_evidence() -> None:
    robustness = LifecycleTransition(
        previous=StrategyLifecycle.BACKTESTED,
        current=StrategyLifecycle.ROBUSTNESS_VERIFIED,
        reason="Robustness passed",
        evidence_ref="robustness-verdict:1",
    )
    assert robustness.current is StrategyLifecycle.ROBUSTNESS_VERIFIED

    with pytest.raises(ValueError, match="evidence_ref"):
        LifecycleTransition(
            previous=StrategyLifecycle.ROBUSTNESS_VERIFIED,
            current=StrategyLifecycle.OOS_VERIFIED,
            reason="Frozen OOS passed",
        )


def test_legacy_policy_is_readable_but_promotion_frozen() -> None:
    transitions = allowed_transitions(
        StrategyLifecycle.OOS_VERIFIED,
        policy_version=LEGACY_LIFECYCLE_POLICY_VERSION,
    )
    assert StrategyLifecycle.ROBUSTNESS_VERIFIED not in transitions
    assert StrategyLifecycle.RETEST_REQUIRED in transitions
    assert StrategyLifecycle.REJECTED in transitions


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
