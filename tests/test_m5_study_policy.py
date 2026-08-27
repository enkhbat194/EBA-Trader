from __future__ import annotations

import pytest

from eba_trader.holdout_guard import assert_not_first_cycle_oos_overlap
from eba_trader.history import parse_utc
from eba_trader.m5_study_policy import (
    DEFAULT_M5_DEVELOPMENT_CORPUS,
    DEFAULT_M5_STUDY_POLICY,
    M5_DEVELOPMENT_END_EXCLUSIVE,
    M5_DEVELOPMENT_START,
    M5_FROZEN_OOS_END_EXCLUSIVE,
    M5_FROZEN_OOS_START,
    M5_FORWARD_START,
    M5_INTERVAL,
    M5_SYMBOL,
    M5_VENUE,
    assert_m5_development_range,
    assert_not_m5_frozen_oos_overlap,
    overlaps_m5_frozen_oos,
)


def test_default_m5_policy_is_chronological_and_hashed() -> None:
    policy = DEFAULT_M5_STUDY_POLICY

    assert policy.development_start_ms == parse_utc(M5_DEVELOPMENT_START)
    assert policy.development_end_ms == parse_utc(M5_DEVELOPMENT_END_EXCLUSIVE)
    assert policy.frozen_oos_start_ms == parse_utc(M5_FROZEN_OOS_START)
    assert policy.frozen_oos_end_ms == parse_utc(M5_FROZEN_OOS_END_EXCLUSIVE)
    assert policy.forward_start_ms == parse_utc(M5_FORWARD_START)
    assert policy.development_end_ms == policy.frozen_oos_start_ms
    assert policy.frozen_oos_end_ms == policy.forward_start_ms
    assert policy.policy_id.startswith("m5policy_")
    assert policy.policy_id == DEFAULT_M5_STUDY_POLICY.policy_id


def test_pre_registered_corpus_is_fresh_bounded_and_non_overlapping() -> None:
    corpus = DEFAULT_M5_DEVELOPMENT_CORPUS

    assert corpus.policy_id == DEFAULT_M5_STUDY_POLICY.policy_id
    assert corpus.corpus_id.startswith("m5corpus_")
    assert len(corpus.windows) == 12
    assert corpus.corpus_id == DEFAULT_M5_DEVELOPMENT_CORPUS.corpus_id

    inspected_proof_start = parse_utc("2026-08-01T00:00:00Z")
    previous_end = None
    for window in corpus.windows:
        assert window.start_ms != inspected_proof_start
        assert DEFAULT_M5_STUDY_POLICY.development_start_ms <= window.start_ms
        assert window.end_ms <= DEFAULT_M5_STUDY_POLICY.development_end_ms
        if previous_end is not None:
            assert previous_end <= window.start_ms
        previous_end = window.end_ms


def test_m5_frozen_oos_boundaries_are_fail_closed() -> None:
    oos_start = DEFAULT_M5_STUDY_POLICY.frozen_oos_start_ms
    oos_end = DEFAULT_M5_STUDY_POLICY.frozen_oos_end_ms
    minute = 60_000

    assert not overlaps_m5_frozen_oos(
        symbol=M5_SYMBOL,
        venue=M5_VENUE,
        interval=M5_INTERVAL,
        start_ms=oos_start - minute,
        end_ms=oos_start,
    )
    assert overlaps_m5_frozen_oos(
        symbol=M5_SYMBOL,
        venue=M5_VENUE,
        interval=M5_INTERVAL,
        start_ms=oos_start,
        end_ms=oos_start + minute,
    )
    assert overlaps_m5_frozen_oos(
        symbol=M5_SYMBOL,
        venue=M5_VENUE,
        interval=M5_INTERVAL,
        start_ms=oos_end - minute,
        end_ms=oos_end,
    )
    assert not overlaps_m5_frozen_oos(
        symbol=M5_SYMBOL,
        venue=M5_VENUE,
        interval=M5_INTERVAL,
        start_ms=oos_end,
        end_ms=oos_end + minute,
    )

    with pytest.raises(RuntimeError, match="sealed M5 frozen OOS"):
        assert_not_m5_frozen_oos_overlap(
            symbol=M5_SYMBOL,
            venue=M5_VENUE,
            interval=M5_INTERVAL,
            start_ms=oos_start,
            end_ms=oos_start + minute,
            context="test",
        )


def test_m5_development_guard_rejects_wrong_domain_and_outside_range() -> None:
    start_ms = parse_utc("2026-08-01T00:00:00Z")
    end_ms = parse_utc("2026-08-01T04:00:00Z")

    assert_m5_development_range(
        symbol=M5_SYMBOL,
        venue=M5_VENUE,
        interval=M5_INTERVAL,
        start_ms=start_ms,
        end_ms=end_ms,
        context="test",
    )

    with pytest.raises(ValueError, match="requires symbol BTCUSDT"):
        assert_m5_development_range(
            symbol="ETHUSDT",
            venue=M5_VENUE,
            interval=M5_INTERVAL,
            start_ms=start_ms,
            end_ms=end_ms,
            context="test",
        )
    with pytest.raises(ValueError, match="requires venue usd_m_futures"):
        assert_m5_development_range(
            symbol=M5_SYMBOL,
            venue="spot",
            interval=M5_INTERVAL,
            start_ms=start_ms,
            end_ms=end_ms,
            context="test",
        )
    with pytest.raises(ValueError, match="requires interval 1m"):
        assert_m5_development_range(
            symbol=M5_SYMBOL,
            venue=M5_VENUE,
            interval="5m",
            start_ms=start_ms,
            end_ms=end_ms,
            context="test",
        )
    with pytest.raises(RuntimeError, match="sealed M5 frozen OOS"):
        assert_m5_development_range(
            symbol=M5_SYMBOL,
            venue=M5_VENUE,
            interval=M5_INTERVAL,
            start_ms=DEFAULT_M5_STUDY_POLICY.frozen_oos_start_ms,
            end_ms=DEFAULT_M5_STUDY_POLICY.frozen_oos_start_ms + 60_000,
            context="test",
        )


def test_legacy_2025_oos_and_m5_2026_oos_are_independent_locks() -> None:
    legacy_start = parse_utc("2025-06-01T00:00:00Z")
    legacy_end = parse_utc("2025-06-01T01:00:00Z")

    assert_not_m5_frozen_oos_overlap(
        symbol=M5_SYMBOL,
        venue=M5_VENUE,
        interval=M5_INTERVAL,
        start_ms=legacy_start,
        end_ms=legacy_end,
        context="legacy independence",
    )
    with pytest.raises(RuntimeError, match="frozen first-cycle 2025 OOS"):
        assert_not_first_cycle_oos_overlap(
            symbol=M5_SYMBOL,
            interval=M5_INTERVAL,
            start_ms=legacy_start,
            end_ms=legacy_end,
            context="legacy independence",
        )
