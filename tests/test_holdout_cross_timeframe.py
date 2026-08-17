from __future__ import annotations

from eba_trader.holdout_guard import (
    FIRST_CYCLE_OOS_END_MS,
    FIRST_CYCLE_OOS_START_MS,
    overlaps_first_cycle_oos,
)


def test_btc_2025_holdout_is_protected_across_timeframes() -> None:
    for interval in ("1m", "5m", "15m", "1h", "1d"):
        assert overlaps_first_cycle_oos(
            symbol="BTCUSDT",
            interval=interval,
            start_ms=FIRST_CYCLE_OOS_START_MS,
            end_ms=FIRST_CYCLE_OOS_END_MS,
        )


def test_other_symbol_is_not_this_cycles_holdout() -> None:
    assert not overlaps_first_cycle_oos(
        symbol="ETHUSDT",
        interval="15m",
        start_ms=FIRST_CYCLE_OOS_START_MS,
        end_ms=FIRST_CYCLE_OOS_END_MS,
    )
