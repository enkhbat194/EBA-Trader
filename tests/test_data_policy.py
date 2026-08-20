from __future__ import annotations

from eba_trader.data_policy import allowed_source_gap_ranges


def test_first_cycle_source_gap_allowlist_is_exact_and_scoped() -> None:
    gaps = allowed_source_gap_ranges("BTCUSDT", "15m")
    missing = sum((end - start) // (15 * 60 * 1000) for start, end in gaps)

    assert len(gaps) == 7
    assert missing == 70
    assert allowed_source_gap_ranges("ETHUSDT", "15m") == ()
    assert allowed_source_gap_ranges("BTCUSDT", "1h") == ()
