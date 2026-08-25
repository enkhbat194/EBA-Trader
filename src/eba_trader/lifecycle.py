from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class StrategyLifecycle(StrEnum):
    GENERATED = "generated"
    BACKTESTED = "backtested"
    OOS_VERIFIED = "oos_verified"
    ROBUSTNESS_VERIFIED = "robustness_verified"
    PAPER_CANDIDATE = "paper_candidate"
    PAPER_VERIFIED = "paper_verified"
    DEMO_CANDIDATE = "demo_candidate"
    DEMO_VERIFIED = "demo_verified"
    SHADOW_VERIFIED = "shadow_verified"
    MICRO_LIVE_ELIGIBLE = "micro_live_eligible"
    LIVE_ELIGIBLE = "live_eligible"
    LIVE_ACTIVE = "live_active"
    REJECTED = "rejected"
    QUARANTINED = "quarantined"
    RETEST_REQUIRED = "retest_required"
    RETIRED = "retired"


PROMOTION_PATH = (
    StrategyLifecycle.GENERATED,
    StrategyLifecycle.BACKTESTED,
    StrategyLifecycle.OOS_VERIFIED,
    StrategyLifecycle.ROBUSTNESS_VERIFIED,
    StrategyLifecycle.PAPER_CANDIDATE,
    StrategyLifecycle.PAPER_VERIFIED,
    StrategyLifecycle.DEMO_CANDIDATE,
    StrategyLifecycle.DEMO_VERIFIED,
    StrategyLifecycle.SHADOW_VERIFIED,
    StrategyLifecycle.MICRO_LIVE_ELIGIBLE,
    StrategyLifecycle.LIVE_ELIGIBLE,
    StrategyLifecycle.LIVE_ACTIVE,
)

_PROMOTION_NEXT = dict(zip(PROMOTION_PATH[:-1], PROMOTION_PATH[1:], strict=True))


@dataclass(frozen=True, slots=True)
class LifecycleTransition:
    previous: StrategyLifecycle
    current: StrategyLifecycle
    reason: str
    evidence_ref: str | None = None

    def __post_init__(self) -> None:
        if not self.reason.strip():
            raise ValueError("Lifecycle transition reason is required")
        if self.current in PROMOTION_PATH[1:] and not (self.evidence_ref or "").strip():
            raise ValueError("Promotion transitions require an evidence_ref")
        assert_transition_allowed(self.previous, self.current)


def allowed_transitions(state: StrategyLifecycle) -> frozenset[StrategyLifecycle]:
    transitions: set[StrategyLifecycle] = set()

    next_state = _PROMOTION_NEXT.get(state)
    if next_state is not None:
        transitions.add(next_state)

    if state in PROMOTION_PATH:
        transitions.add(StrategyLifecycle.REJECTED)
        if state is not StrategyLifecycle.GENERATED:
            transitions.add(StrategyLifecycle.QUARANTINED)
        if state is StrategyLifecycle.LIVE_ACTIVE:
            transitions.add(StrategyLifecycle.RETIRED)

    if state is StrategyLifecycle.QUARANTINED:
        transitions.update(
            {
                StrategyLifecycle.RETEST_REQUIRED,
                StrategyLifecycle.RETIRED,
            }
        )
    elif state is StrategyLifecycle.RETEST_REQUIRED:
        transitions.update(
            {
                StrategyLifecycle.BACKTESTED,
                StrategyLifecycle.REJECTED,
                StrategyLifecycle.RETIRED,
            }
        )
    elif state is StrategyLifecycle.REJECTED:
        transitions.add(StrategyLifecycle.RETIRED)

    return frozenset(transitions)


def assert_transition_allowed(
    previous: StrategyLifecycle,
    current: StrategyLifecycle,
) -> None:
    if current not in allowed_transitions(previous):
        raise ValueError(f"Lifecycle transition {previous.value} -> {current.value} is not allowed")
