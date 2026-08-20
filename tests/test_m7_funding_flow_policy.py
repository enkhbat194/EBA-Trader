from eba_trader.m7_funding_flow_policy import (
    BASELINE_UPLIFT,
    FDR_Q_THRESHOLD,
    HORIZONS_BARS,
    M7_CANDIDATES,
    verify_m7_freeze,
)


def test_m7_freeze_verifies_and_oos_stays_locked() -> None:
    manifest = verify_m7_freeze()
    assert manifest["oos_2025"] == "LOCKED_NOT_ACCESSED"
    assert manifest["parameter_changes_after_first_run"] == "forbidden"
    assert manifest["strategy_generation"] == "forbidden"
    assert manifest["ai_module"] == "excluded"


def test_m7_search_space_is_exactly_frozen() -> None:
    assert len(M7_CANDIDATES) == 12
    assert len({candidate.name for candidate in M7_CANDIDATES}) == 12
    assert HORIZONS_BARS == (4, 16, 48)
    assert len(M7_CANDIDATES) * len(HORIZONS_BARS) == 36
    assert BASELINE_UPLIFT == 0.001
    assert FDR_Q_THRESHOLD == 0.10


def test_m7_negative_direction_never_implies_short_authority() -> None:
    negative = [candidate for candidate in M7_CANDIDATES if candidate.direction < 0]
    assert negative
    assert all(candidate.direction == -1 for candidate in negative)
