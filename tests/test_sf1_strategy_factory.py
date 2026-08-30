from __future__ import annotations

from pathlib import Path

from eba_trader.sf1_strategy_factory import load_sf1_candidates

ROOT = Path(__file__).resolve().parents[1]
CANDIDATES = ROOT / "config/sf1_candidate_set_v1.json"


def test_sf1_candidate_set_uses_36_of_48_preregistered_slots() -> None:
    budget, warmup, candidates = load_sf1_candidates(CANDIDATES)

    assert budget == 48
    assert warmup == 64
    assert len(candidates) == 36
    assert len({candidate.candidate_id for candidate in candidates}) == 36

    families: dict[str, int] = {}
    for candidate in candidates:
        families[candidate.family] = families.get(candidate.family, 0) + 1

    assert families == {
        "atr_trailing_v1": 12,
        "donchian_breakout_v1": 12,
        "mean_reversion_z_v1": 12,
    }


def test_sf1_candidate_parameters_are_normalized_by_family() -> None:
    _, _, candidates = load_sf1_candidates(CANDIDATES)
    by_id = {candidate.candidate_id: candidate for candidate in candidates}

    assert by_id["atr_07x150"].parameters == {
        "atr_period": 7,
        "atr_multiplier": 1.5,
    }
    assert by_id["brk_32x16"].parameters == {
        "entry_lookback": 32,
        "exit_lookback": 16,
    }
    assert by_id["mr_48z20x05"].parameters == {
        "lookback": 48,
        "entry_z": 2.0,
        "exit_z": 0.5,
    }
