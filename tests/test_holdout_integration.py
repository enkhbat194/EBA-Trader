from __future__ import annotations

import inspect

import pytest

from eba_trader import history, research


def test_renamed_development_window_cannot_overlap_frozen_oos() -> None:
    disguised = research.StudyWindow("totally_not_oos", "2025-06-01", "2025-07-01")
    with pytest.raises(RuntimeError, match="frozen first-cycle 2025 OOS"):
        research._assert_development_window_allowed(
            disguised,
            symbol="BTCUSDT",
            interval="15m",
        )


def test_validation_window_touching_oos_boundary_is_allowed() -> None:
    validation = research.StudyWindow("validation", "2024-01-01", "2025-01-01")
    research._assert_development_window_allowed(
        validation,
        symbol="BTCUSDT",
        interval="15m",
    )


def test_generic_history_cli_calls_holdout_overlap_guard_before_fetch() -> None:
    source = inspect.getsource(history.download_history_cli)
    guard_position = source.index("assert_not_first_cycle_oos_overlap")
    fetch_position = source.index("fetch_binance_klines")
    assert guard_position < fetch_position
