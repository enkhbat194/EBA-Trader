from __future__ import annotations

import pytest

from eba_trader.m9_bookdepth_policy import (
    HORIZONS_BARS,
    M9_CANDIDATES,
    M9CandidateSpec,
    verify_m9_freeze,
)


def test_m9_frozen_policy_verifies_repo_contract() -> None:
    manifest = verify_m9_freeze()
    assert manifest["status"] == "FROZEN_PREDECLARED_NOT_RUN"
    assert manifest["candidate_count"] == 8
    assert manifest["hypothesis_test_count"] == 24
    assert manifest["horizons_bars"] == [4, 16, 48]
    assert manifest["oos_2025"] == "LOCKED_NOT_ACCESSED"
    assert manifest["parameter_changes_after_first_run"] == "forbidden"
    assert manifest["strategy_generation"] == "forbidden"
    assert manifest["ai_module"] == "excluded"


def test_m9_candidate_names_and_horizons_are_frozen_and_unique() -> None:
    assert len(M9_CANDIDATES) == 8
    assert len({candidate.name for candidate in M9_CANDIDATES}) == 8
    assert HORIZONS_BARS == (4, 16, 48)
    assert sum(candidate.direction > 0 for candidate in M9_CANDIDATES) == 4
    assert sum(candidate.direction < 0 for candidate in M9_CANDIDATES) == 4


def test_m9_candidate_spec_rejects_unknown_feature_and_direction() -> None:
    with pytest.raises(ValueError):
        M9CandidateSpec("bad", "unknown", 1, 1)
    with pytest.raises(ValueError):
        M9CandidateSpec("bad", "notional_1_z", 0, 1)
    with pytest.raises(ValueError):
        M9CandidateSpec("bad", "notional_1_z", 1, 0)
