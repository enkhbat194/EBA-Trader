from __future__ import annotations

import pytest

from eba_trader.holdout_guard import (
    FIRST_CYCLE_OOS_END_MS,
    FIRST_CYCLE_OOS_START_MS,
    assert_not_first_cycle_oos_overlap,
    overlaps_first_cycle_oos,
)


def test_exact_oos_range_is_detected() -> None:
    assert overlaps_first_cycle_oos(
        symbol="BTCUSDT",
        interval="15m",
        start_ms=FIRST_CYCLE_OOS_START_MS,
        end_ms=FIRST_CYCLE_OOS_END_MS,
    )


def test_partial_overlap_is_detected() -> None:
    day_ms = 24 * 60 * 60 * 1000
    assert overlaps_first_cycle_oos(
        symbol="btcusdt",
        interval="15m",
        start_ms=FIRST_CYCLE_OOS_START_MS - day_ms,
        end_ms=FIRST_CYCLE_OOS_START_MS + day_ms,
    )


def test_touching_boundary_without_overlap_is_allowed() -> None:
    day_ms = 24 * 60 * 60 * 1000
    assert not overlaps_first_cycle_oos(
        symbol="BTCUSDT",
        interval="15m",
        start_ms=FIRST_CYCLE_OOS_START_MS - day_ms,
        end_ms=FIRST_CYCLE_OOS_START_MS,
    )
    assert not overlaps_first_cycle_oos(
        symbol="BTCUSDT",
        interval="15m",
        start_ms=FIRST_CYCLE_OOS_END_MS,
        end_ms=FIRST_CYCLE_OOS_END_MS + day_ms,
    )


def test_other_symbol_or_interval_is_not_first_cycle_holdout() -> None:
    assert not overlaps_first_cycle_oos(
        symbol="ETHUSDT",
        interval="15m",
        start_ms=FIRST_CYCLE_OOS_START_MS,
        end_ms=FIRST_CYCLE_OOS_END_MS,
    )
    assert not overlaps_first_cycle_oos(
        symbol="BTCUSDT",
        interval="1h",
        start_ms=FIRST_CYCLE_OOS_START_MS,
        end_ms=FIRST_CYCLE_OOS_END_MS,
    )


def test_guard_raises_with_authorized_path_message() -> None:
    with pytest.raises(RuntimeError, match="authorized frozen OOS path"):
        assert_not_first_cycle_oos_overlap(
            symbol="BTCUSDT",
            interval="15m",
            start_ms=FIRST_CYCLE_OOS_START_MS,
            end_ms=FIRST_CYCLE_OOS_END_MS,
            context="generic downloader",
        )
