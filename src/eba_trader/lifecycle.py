from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

LEGACY_LIFECYCLE_POLICY_VERSION = 1
CURRENT_LIFECYCLE_POLICY_VERSION = 2


class StrategyLifecycle(StrEnum):
    GENERATED = "generated"
    BACKTESTED = "backtested"
    ROBUSTNESS_VERIFIED = "robustness_verified"
    OOS_VERIFIED = "oos_verified"
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


# Policy v2 is the only promotion path for new/current research work. Robustness must be
# proven before the first frozen-OOS state is reachable.
PROMOTION_PATH = (
    StrategyLifecycle.GENERATED,
    StrategyLifecycle.BACKTESTED,
    StrategyLifecycle.ROBUSTNESS_VERIFIED,
    StrategyLifecycle.OOS_VERIFIED,
    StrategyLifecycle.PAPER_CANDIDATE,
    StrategyLifecycle.PAPER_VERIFIED,
    StrategyLifecycle.DEMO_CANDIDATE,
    StrategyLifecycle.DEMO_VERIFIED,
    StrategyLifecycle.SHADOW_VERIFIED,
    StrategyLifecycle.MICRO_LIVE_ELIGIBLE,
    StrategyLifecycle.LIVE_ELIGIBLE,
    StrategyLifecycle.LIVE_ACTIVE,
)

# Historical policy v1 opened OOS before robustness. Stored v1 rows remain readable, but
# promotion is frozen so an old state can never silently acquire v2 semantics.
LEGACY_PROMOTION_PATH = (
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
    policy_version: int = CURRENT_LIFECYCLE_POLICY_VERSION

    def __post_init__(self) -> None:
        if not self.reason.strip():
            raise ValueError("Lifecycle transition reason is required")
        if self.policy_version not in {
            LEGACY_LIFECYCLE_POLICY_VERSION,
            CURRENT_LIFECYCLE_POLICY_VERSION,
        }:
            raise ValueError(f"Unsupported lifecycle policy version {self.policy_version}")
        if (
            self.policy_version == CURRENT_LIFECYCLE_POLICY_VERSION
            and self.current in PROMOTION_PATH[1:]
            and not (self.evidence_ref or "").strip()
        ):
            raise ValueError("Promotion transitions require an evidence_ref")
        assert_transition_allowed(
            self.previous,
            self.current,
            policy_version=self.policy_version,
        )


def allowed_transitions(
    state: StrategyLifecycle,
    *,
    policy_version: int = CURRENT_LIFECYCLE_POLICY_VERSION,
) -> frozenset[StrategyLifecycle]:
    if policy_version not in {
        LEGACY_LIFECYCLE_POLICY_VERSION,
        CURRENT_LIFECYCLE_POLICY_VERSION,
    }:
        raise ValueError(f"Unsupported lifecycle policy version {policy_version}")

    transitions: set[StrategyLifecycle] = set()

    if policy_version == CURRENT_LIFECYCLE_POLICY_VERSION:
        next_state = _PROMOTION_NEXT.get(state)
        if next_state is not None:
            transitions.add(next_state)

        if state in PROMOTION_PATH:
            transitions.add(StrategyLifecycle.REJECTED)
            if state is not StrategyLifecycle.GENERATED:
                transitions.add(StrategyLifecycle.QUARANTINED)
            if state is StrategyLifecycle.LIVE_ACTIVE:
                transitions.add(StrategyLifecycle.RETIRED)
    else:
        # V1 promotion is deliberately frozen. Historical post-OOS rows must be marked
        # RETEST_REQUIRED and explicitly moved to policy v2 before re-entering promotion.
        if state in LEGACY_PROMOTION_PATH:
            transitions.update(
                {
                    StrategyLifecycle.REJECTED,
                    StrategyLifecycle.RETEST_REQUIRED,
                }
            )
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
        if policy_version == CURRENT_LIFECYCLE_POLICY_VERSION:
            transitions.update(
                {
                    StrategyLifecycle.BACKTESTED,
                    StrategyLifecycle.REJECTED,
                    StrategyLifecycle.RETIRED,
                }
            )
        else:
            transitions.update(
                {
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
    *,
    policy_version: int = CURRENT_LIFECYCLE_POLICY_VERSION,
) -> None:
    if current not in allowed_transitions(previous, policy_version=policy_version):
        raise ValueError(
            f"Lifecycle transition {previous.value} -> {current.value} "
            f"is not allowed under policy v{policy_version}"
        )
