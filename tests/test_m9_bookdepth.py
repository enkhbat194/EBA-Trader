from __future__ import annotations

import math
from dataclasses import replace

from eba_trader.history import Candle, parse_utc
from eba_trader.m9_bookdepth import (
    FeatureBar,
    HorizonStats,
    QuarterStats,
    RawFeatureBar,
    _passes_challenge,
    _passes_discovery,
    _spot_outcome,
    benjamini_hochberg,
    candidate_signal_times,
    parse_bookdepth_day_to_features,
    standardize_feature_bars,
)
from eba_trader.m9_bookdepth_policy import M9_CANDIDATES

BAR_MS = 15 * 60 * 1000


def _bookdepth_rows(
    *,
    count: int = 20,
    start_second: int = 30,
    conflicting: bool = False,
) -> list[list[str]]:
    rows = [["timestamp", "percentage", "depth", "notional"]]
    percentages = (-5, -4, -3, -2, -1, 1, 2, 3, 4, 5)
    for snapshot in range(count):
        minute = snapshot // 2
        second = start_second if snapshot % 2 == 0 else 45
        timestamp = f"2023-01-01 00:{minute:02d}:{second:02d}"
        for percentage in percentages:
            negative = percentage < 0
            depth = 200.0 if negative else 100.0
            if abs(percentage) == 5:
                notional = 300.0 if negative else 100.0
            else:
                notional = 200.0 if negative else 100.0
            rows.append([timestamp, str(percentage), str(depth), str(notional)])
    if conflicting:
        rows.append(["2023-01-01 00:00:30", "-1", "201", "200"])
    return rows


def _raw_bar(index: int, *, offset_bars: int = 0, spike: float = 0.0) -> RawFeatureBar:
    x = index + offset_bars
    return RawFeatureBar(
        signal_time_ms=x * BAR_MS,
        notional_1=math.sin(index / 4.0) + spike,
        notional_5=math.cos(index / 5.0) + spike * 0.5,
        depth_1=math.sin(index / 7.0) + spike * 0.25,
        snapshot_count=30,
        latest_staleness_ms=30_000,
    )


def _feature_bar(index: int, value: float) -> FeatureBar:
    return FeatureBar(
        signal_time_ms=index * BAR_MS,
        notional_1_z=value,
        notional_5_z=value,
        depth_1_z=value,
        notional_1_change_4bar_z=value,
    )


def _spot_bar(index: int, *, open_price: float = 100.0, close_price: float = 100.0) -> Candle:
    open_time = index * BAR_MS
    return Candle(
        open_time_ms=open_time,
        open=open_price,
        high=max(open_price, close_price) + 1.0,
        low=min(open_price, close_price) - 1.0,
        close=close_price,
        volume=100.0,
        close_time_ms=open_time + BAR_MS - 1,
        quote_volume=10_000.0,
        trade_count=100,
    )


def _candidate(name: str):
    return next(candidate for candidate in M9_CANDIDATES if candidate.name == name)


def test_bookdepth_day_builds_same_snapshot_signed_side_ratios() -> None:
    result = parse_bookdepth_day_to_features(_bookdepth_rows(), "2023-01-01")
    assert result.invalid_rows == 0
    assert result.conflicting_rows == 0
    assert result.complete_snapshots == 20
    assert result.usable_snapshots == 20
    assert len(result.feature_bars) == 1
    bar = result.feature_bars[0]
    assert bar.signal_time_ms == parse_utc("2023-01-01T00:00:00Z")
    assert round(bar.notional_1, 8) == round(math.log(2.0), 8)
    assert round(bar.notional_5, 8) == round(math.log(3.0), 8)
    assert round(bar.depth_1, 8) == round(math.log(2.0), 8)
    assert bar.snapshot_count == 20
    assert 0 <= bar.latest_staleness_ms <= 120_000


def test_bookdepth_day_requires_frozen_minimum_snapshot_support() -> None:
    result = parse_bookdepth_day_to_features(_bookdepth_rows(count=19), "2023-01-01")
    assert result.complete_snapshots == 19
    assert result.feature_bars == ()


def test_bookdepth_conflict_is_recorded_not_silently_overwritten() -> None:
    result = parse_bookdepth_day_to_features(
        _bookdepth_rows(conflicting=True),
        "2023-01-01",
    )
    assert result.conflicting_rows == 1


def test_standardization_uses_only_prior_contiguous_values() -> None:
    bars = [_raw_bar(index) for index in range(105)]
    bars[100] = _raw_bar(100, spike=8.0)
    features = standardize_feature_bars(bars)
    selected = next(item for item in features if item.signal_time_ms == 100 * BAR_MS)
    assert selected.notional_1_z > 5.0

    future_changed = list(bars)
    future_changed[104] = _raw_bar(104, spike=-50.0)
    second = standardize_feature_bars(future_changed)
    selected_second = next(item for item in second if item.signal_time_ms == 100 * BAR_MS)
    assert selected == selected_second


def test_standardization_resets_after_feature_gap() -> None:
    bars = [_raw_bar(index) for index in range(105)]
    for index in range(50, 105):
        bars[index] = _raw_bar(index, offset_bars=1)
    assert standardize_feature_bars(bars) == ()


def test_candidate_event_cooldown_is_four_bars() -> None:
    features = tuple(_feature_bar(index, 2.0) for index in range(12))
    candidate = _candidate("notional_1_negative_side_dominant")
    times = candidate_signal_times(
        candidate,
        features,
        start_ms=0,
        end_ms=12 * BAR_MS,
    )
    assert times == (0, 4 * BAR_MS, 8 * BAR_MS)


def test_spot_outcome_enters_next_open_and_applies_frozen_costs() -> None:
    bars = [_spot_bar(index) for index in range(20)]
    bars[11] = _spot_bar(11, open_price=100.0, close_price=100.0)
    bars[14] = _spot_bar(14, open_price=109.0, close_price=110.0)
    index_by_time = {bar.open_time_ms: index for index, bar in enumerate(bars)}
    outcome = _spot_outcome(
        bars,
        index_by_time,
        10 * BAR_MS,
        4,
        1,
        window_end_exclusive_ms=20 * BAR_MS,
    )
    assert outcome is not None
    assert round(outcome.gross_signed_return, 8) == 0.10
    assert round(outcome.base_net_signed_return, 8) == 0.097
    assert round(outcome.severe_net_signed_return, 8) == 0.093


def test_spot_outcome_refuses_gap_crossing() -> None:
    bars = [_spot_bar(index) for index in range(10)]
    bars.pop(3)
    index_by_time = {bar.open_time_ms: index for index, bar in enumerate(bars)}
    assert (
        _spot_outcome(
            bars,
            index_by_time,
            2 * BAR_MS,
            4,
            1,
            window_end_exclusive_ms=10 * BAR_MS,
        )
        is None
    )


def test_benjamini_hochberg_is_monotone_and_bounded() -> None:
    adjusted = benjamini_hochberg({("a", 4): 0.001, ("b", 4): 0.02, ("c", 4): 0.20})
    assert 0.0 <= adjusted[("a", 4)] <= adjusted[("b", 4)] <= adjusted[("c", 4)] <= 1.0


def _quarter_stats(year: int, *, event_count: int = 20, uplift: float = 0.002):
    return tuple(
        QuarterStats(
            quarter=f"{year}Q{quarter}",
            event_count=event_count,
            mean_base_net=0.01,
            baseline_mean_base_net=0.01 - uplift,
            baseline_uplift=uplift,
        )
        for quarter in range(1, 5)
    )


def _passing_discovery_stats() -> HorizonStats:
    return HorizonStats(
        event_count=100,
        distinct_days=60,
        mean_gross_signed_return=0.015,
        mean_base_net_signed_return=0.012,
        mean_severe_net_signed_return=0.008,
        median_base_net_signed_return=0.010,
        base_net_win_rate=0.60,
        baseline_mean_base_net=0.010,
        baseline_uplift=0.002,
        daily_mean_p_value=0.01,
        fdr_q_value=0.05,
        quarterly=_quarter_stats(2023),
        discovery_pass=False,
        challenge_pass=False,
    )


def test_discovery_gate_requires_fdr_uplift_and_quarter_stability() -> None:
    passing = _passing_discovery_stats()
    assert _passes_discovery(passing)
    assert not _passes_discovery(replace(passing, fdr_q_value=0.11))
    assert not _passes_discovery(replace(passing, baseline_uplift=0.0009))
    weak_quarters = list(passing.quarterly)
    weak_quarters[0] = replace(weak_quarters[0], event_count=5)
    weak_quarters[1] = replace(weak_quarters[1], event_count=5)
    assert not _passes_discovery(replace(passing, quarterly=tuple(weak_quarters)))


def test_challenge_gate_requires_discovery_and_quarter_stability() -> None:
    stats = replace(
        _passing_discovery_stats(),
        event_count=80,
        distinct_days=50,
        quarterly=_quarter_stats(2024, event_count=15),
    )
    assert _passes_challenge(stats, discovery_pass=True)
    assert not _passes_challenge(stats, discovery_pass=False)
    weak = list(stats.quarterly)
    weak[0] = replace(weak[0], mean_base_net=-0.01, baseline_uplift=-0.01)
    weak[1] = replace(weak[1], mean_base_net=-0.01, baseline_uplift=-0.01)
    assert not _passes_challenge(replace(stats, quarterly=tuple(weak)), discovery_pass=True)
