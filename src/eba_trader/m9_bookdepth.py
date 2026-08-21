from __future__ import annotations

import argparse
import hashlib
import json
import math
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from statistics import NormalDist, mean, median, stdev
from typing import Any

from .data_policy import allowed_source_close_times, allowed_source_gap_ranges
from .history import Candle, load_csv, parse_utc, validate_interval_window
from .holdout_guard import assert_not_first_cycle_oos_overlap
from .m8_alt_data_audit import _csv_rows_from_zip, _download_verified_archive, _parse_timestamp
from .m8_alt_data_policy import BINANCE_VISION_BASE
from .m9_bookdepth_policy import (
    BASE_ROUND_TRIP_COST_BPS,
    BASELINE_UPLIFT,
    BOOKDEPTH_EXPECTED_DAYS,
    CHALLENGE_END_EXCLUSIVE,
    CHALLENGE_START,
    CHANGE_LAG_BARS,
    DISCOVERY_END_EXCLUSIVE,
    DISCOVERY_START,
    EVENT_COOLDOWN_BARS,
    FDR_Q_THRESHOLD,
    FEATURE_BASELINE_BARS,
    HORIZONS_BARS,
    M9_CANDIDATES,
    MAX_SNAPSHOT_STALENESS_MS,
    MIN_CHALLENGE_DAYS,
    MIN_CHALLENGE_EVENTS,
    MIN_CHALLENGE_EVENTS_PER_QUARTER,
    MIN_CHALLENGE_POSITIVE_QUARTERS,
    MIN_DISCOVERY_DAYS,
    MIN_DISCOVERY_EVENTS,
    MIN_DISCOVERY_EVENTS_PER_PASSING_QUARTER,
    MIN_DISCOVERY_PASSING_QUARTERS,
    MIN_SNAPSHOTS_PER_15M,
    SEVERE_ROUND_TRIP_COST_BPS,
    SPOT_CHALLENGE_SHA256,
    SPOT_RESEARCH_SHA256,
    Z_THRESHOLD,
    M9CandidateSpec,
    sha256_file,
    verify_m9_freeze,
)
from .provenance import collect_source_provenance
from .study_policy import FIRST_CYCLE_INTERVAL, FIRST_CYCLE_SYMBOL

FIFTEEN_MIN_MS = 15 * 60 * 1000
DAY_MS = 24 * 60 * 60 * 1000
EXPECTED_PERCENTAGES = {-5, -4, -3, -2, -1, 1, 2, 3, 4, 5}


@dataclass(frozen=True, slots=True)
class RawFeatureBar:
    signal_time_ms: int
    notional_1: float
    notional_5: float
    depth_1: float
    snapshot_count: int
    latest_staleness_ms: int


@dataclass(frozen=True, slots=True)
class FeatureBar:
    signal_time_ms: int
    notional_1_z: float
    notional_5_z: float
    depth_1_z: float
    notional_1_change_4bar_z: float


@dataclass(frozen=True, slots=True)
class DayFeatureResult:
    date: str
    exists: bool
    checksum_verified: bool
    parse_error: bool
    invalid_rows: int
    exact_duplicate_rows: int
    conflicting_rows: int
    complete_snapshots: int
    usable_snapshots: int
    feature_bars: tuple[RawFeatureBar, ...]


@dataclass(frozen=True, slots=True)
class EventOutcome:
    signal_time_ms: int
    horizon_bars: int
    gross_signed_return: float
    base_net_signed_return: float
    severe_net_signed_return: float


@dataclass(frozen=True, slots=True)
class QuarterStats:
    quarter: str
    event_count: int
    mean_base_net: float | None
    baseline_mean_base_net: float | None
    baseline_uplift: float | None


@dataclass(frozen=True, slots=True)
class HorizonStats:
    event_count: int
    distinct_days: int
    mean_gross_signed_return: float | None
    mean_base_net_signed_return: float | None
    mean_severe_net_signed_return: float | None
    median_base_net_signed_return: float | None
    base_net_win_rate: float | None
    baseline_mean_base_net: float | None
    baseline_uplift: float | None
    daily_mean_p_value: float
    fdr_q_value: float
    quarterly: tuple[QuarterStats, ...]
    discovery_pass: bool
    challenge_pass: bool


@dataclass(frozen=True, slots=True)
class CandidateResult:
    candidate: M9CandidateSpec
    classification: str
    passing_horizons: tuple[int, ...]
    discovery: dict[int, HorizonStats]
    challenge: dict[int, HorizonStats]


def _date_strings(start_text: str, end_text: str) -> tuple[str, ...]:
    start = datetime.fromtimestamp(parse_utc(start_text) / 1000.0, tz=UTC).date()
    end = datetime.fromtimestamp(parse_utc(end_text) / 1000.0, tz=UTC).date()
    result: list[str] = []
    current = start
    while current < end:
        result.append(current.isoformat())
        current = current.fromordinal(current.toordinal() + 1)
    return tuple(result)


def _bookdepth_url(date_text: str) -> str:
    name = f"{FIRST_CYCLE_SYMBOL}-bookDepth-{date_text}.zip"
    return f"{BINANCE_VISION_BASE}/bookDepth/{FIRST_CYCLE_SYMBOL}/{name}"


def _finalize_snapshot(
    timestamp_ms: int,
    values: dict[int, tuple[float, float]],
) -> tuple[float, float, float] | None:
    if set(values) != EXPECTED_PERCENTAGES:
        return None
    neg_1_depth, neg_1_notional = values[-1]
    pos_1_depth, pos_1_notional = values[1]
    _, neg_5_notional = values[-5]
    _, pos_5_notional = values[5]
    required = (
        neg_1_depth,
        pos_1_depth,
        neg_1_notional,
        pos_1_notional,
        neg_5_notional,
        pos_5_notional,
    )
    if timestamp_ms < 0 or any(not math.isfinite(value) or value <= 0 for value in required):
        return None
    return (
        math.log(neg_1_notional / pos_1_notional),
        math.log(neg_5_notional / pos_5_notional),
        math.log(neg_1_depth / pos_1_depth),
    )


def parse_bookdepth_day_to_features(
    rows: list[list[str]],
    date_text: str,
) -> DayFeatureResult:
    if not rows:
        raise RuntimeError("Empty bookDepth archive")
    header = [value.strip().lower() for value in rows[0]]
    has_header = "timestamp" in header and "percentage" in header
    data = rows[1:] if has_header else rows
    if has_header:
        indices = {
            name: header.index(name) for name in ("timestamp", "percentage", "depth", "notional")
        }
    else:
        indices = {"timestamp": 0, "percentage": 1, "depth": 2, "notional": 3}

    day_start = parse_utc(f"{date_text}T00:00:00Z")
    day_end = day_start + DAY_MS
    snapshots: dict[int, dict[int, tuple[float, float]]] = {}
    exact_duplicates = 0
    conflicts = 0
    invalid_rows = 0

    for row in data:
        try:
            timestamp = _parse_timestamp(row[indices["timestamp"]])
            percentage = int(float(row[indices["percentage"]]))
            depth = float(row[indices["depth"]])
            notional = float(row[indices["notional"]])
            if (
                not day_start <= timestamp < day_end
                or percentage not in EXPECTED_PERCENTAGES
                or not math.isfinite(depth)
                or not math.isfinite(notional)
                or depth < 0
                or notional < 0
            ):
                raise ValueError
        except (ValueError, IndexError, TypeError):
            invalid_rows += 1
            continue

        bucket = snapshots.setdefault(timestamp, {})
        incoming = (depth, notional)
        previous = bucket.get(percentage)
        if previous is None:
            bucket[percentage] = incoming
        elif previous == incoming:
            exact_duplicates += 1
        else:
            conflicts += 1

    complete_snapshots = 0
    usable: list[tuple[int, float, float, float]] = []
    for timestamp in sorted(snapshots):
        values = snapshots[timestamp]
        if set(values) == EXPECTED_PERCENTAGES:
            complete_snapshots += 1
        feature = _finalize_snapshot(timestamp, values)
        if feature is not None:
            usable.append((timestamp, *feature))

    bars: list[RawFeatureBar] = []
    cursor = 0
    for slot in range(96):
        interval_start = day_start + slot * FIFTEEN_MIN_MS
        interval_end = interval_start + FIFTEEN_MIN_MS
        selected: list[tuple[int, float, float, float]] = []
        while cursor < len(usable) and usable[cursor][0] <= interval_start:
            cursor += 1
        scan = cursor
        while scan < len(usable) and usable[scan][0] <= interval_end:
            selected.append(usable[scan])
            scan += 1
        cursor = scan
        if len(selected) < MIN_SNAPSHOTS_PER_15M:
            continue
        staleness = interval_end - selected[-1][0]
        if staleness < 0 or staleness > MAX_SNAPSHOT_STALENESS_MS:
            continue
        bars.append(
            RawFeatureBar(
                signal_time_ms=interval_start,
                notional_1=median(item[1] for item in selected),
                notional_5=median(item[2] for item in selected),
                depth_1=median(item[3] for item in selected),
                snapshot_count=len(selected),
                latest_staleness_ms=staleness,
            )
        )

    return DayFeatureResult(
        date=date_text,
        exists=True,
        checksum_verified=True,
        parse_error=False,
        invalid_rows=invalid_rows,
        exact_duplicate_rows=exact_duplicates,
        conflicting_rows=conflicts,
        complete_snapshots=complete_snapshots,
        usable_snapshots=len(usable),
        feature_bars=tuple(bars),
    )


def _download_bookdepth_day(date_text: str) -> DayFeatureResult:
    downloaded = _download_verified_archive(_bookdepth_url(date_text))
    if downloaded is None:
        return DayFeatureResult(
            date=date_text,
            exists=False,
            checksum_verified=False,
            parse_error=False,
            invalid_rows=0,
            exact_duplicate_rows=0,
            conflicting_rows=0,
            complete_snapshots=0,
            usable_snapshots=0,
            feature_bars=(),
        )
    payload, _ = downloaded
    try:
        return parse_bookdepth_day_to_features(_csv_rows_from_zip(payload), date_text)
    except (RuntimeError, ValueError, IndexError, KeyError):
        return DayFeatureResult(
            date=date_text,
            exists=True,
            checksum_verified=True,
            parse_error=True,
            invalid_rows=0,
            exact_duplicate_rows=0,
            conflicting_rows=0,
            complete_snapshots=0,
            usable_snapshots=0,
            feature_bars=(),
        )


def fetch_bookdepth_features(*, workers: int = 12) -> tuple[list[RawFeatureBar], dict[str, object]]:
    if workers < 1 or workers > 16:
        raise ValueError("workers must be between 1 and 16")
    start_ms = parse_utc(DISCOVERY_START)
    end_ms = parse_utc(CHALLENGE_END_EXCLUSIVE)
    assert_not_first_cycle_oos_overlap(
        symbol=FIRST_CYCLE_SYMBOL,
        interval=FIRST_CYCLE_INTERVAL,
        start_ms=start_ms,
        end_ms=end_ms,
        context="M9 Binance bookDepth acquisition",
    )
    dates = _date_strings(DISCOVERY_START, CHALLENGE_END_EXCLUSIVE)
    if len(dates) != BOOKDEPTH_EXPECTED_DAYS:
        raise RuntimeError("M9 frozen bookDepth day count mismatch")

    results: list[DayFeatureResult] = []
    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = {executor.submit(_download_bookdepth_day, date): date for date in dates}
        for future in as_completed(futures):
            results.append(future.result())
    results.sort(key=lambda item: item.date)

    existing = sum(item.exists for item in results)
    verified = sum(item.checksum_verified for item in results)
    parse_errors = sum(item.parse_error for item in results)
    invalid_rows = sum(item.invalid_rows for item in results)
    conflicts = sum(item.conflicting_rows for item in results)
    exact_duplicates = sum(item.exact_duplicate_rows for item in results)
    complete_snapshots = sum(item.complete_snapshots for item in results)
    usable_snapshots = sum(item.usable_snapshots for item in results)
    missing_dates = [item.date for item in results if not item.exists]
    bars = sorted(
        (bar for item in results for bar in item.feature_bars),
        key=lambda item: item.signal_time_ms,
    )
    if len({bar.signal_time_ms for bar in bars}) != len(bars):
        raise RuntimeError("M9 bookDepth feature bars contain duplicate signal timestamps")
    file_coverage = existing / len(dates)
    source_pass = (
        file_coverage >= 0.99
        and verified == existing
        and parse_errors == 0
        and invalid_rows == 0
        and conflicts == 0
    )
    metadata: dict[str, object] = {
        "status": "PASS" if source_pass else "FAIL",
        "expected_daily_files": len(dates),
        "existing_daily_files": existing,
        "checksum_verified_files": verified,
        "daily_file_coverage": file_coverage,
        "missing_daily_files": len(missing_dates),
        "missing_dates": missing_dates,
        "parse_error_files": parse_errors,
        "invalid_rows": invalid_rows,
        "exact_duplicate_rows": exact_duplicates,
        "conflicting_rows": conflicts,
        "complete_snapshots": complete_snapshots,
        "usable_snapshots": usable_snapshots,
        "raw_15m_feature_bars": len(bars),
    }
    return bars, metadata


def _contiguous(times: list[int], start: int, end: int) -> bool:
    if end - start <= 1:
        return True
    return all(
        times[index] - times[index - 1] == FIFTEEN_MIN_MS for index in range(start + 1, end)
    )


def _zscore(current: float, prior: list[float]) -> float | None:
    if len(prior) != FEATURE_BASELINE_BARS:
        return None
    deviation = stdev(prior)
    if deviation <= 0 or not math.isfinite(deviation):
        return None
    value = (current - mean(prior)) / deviation
    return value if math.isfinite(value) else None


def standardize_feature_bars(
    rows: list[RawFeatureBar] | tuple[RawFeatureBar, ...],
) -> tuple[FeatureBar, ...]:
    raw = list(rows)
    if not raw:
        return ()
    times = [item.signal_time_ms for item in raw]
    if any(right <= left for left, right in zip(times, times[1:], strict=False)):
        raise ValueError("M9 raw feature bars must be strictly increasing")

    change: list[float | None] = [None] * len(raw)
    for index in range(CHANGE_LAG_BARS, len(raw)):
        if not _contiguous(times, index - CHANGE_LAG_BARS, index + 1):
            continue
        change[index] = raw[index].notional_1 - raw[index - CHANGE_LAG_BARS].notional_1

    result: list[FeatureBar] = []
    for index in range(FEATURE_BASELINE_BARS, len(raw)):
        prior_start = index - FEATURE_BASELINE_BARS
        if not _contiguous(times, prior_start, index + 1):
            continue
        n1 = _zscore(raw[index].notional_1, [item.notional_1 for item in raw[prior_start:index]])
        n5 = _zscore(raw[index].notional_5, [item.notional_5 for item in raw[prior_start:index]])
        d1 = _zscore(raw[index].depth_1, [item.depth_1 for item in raw[prior_start:index]])
        current_change = change[index]
        if current_change is None:
            continue
        prior_changes = change[prior_start:index]
        if any(value is None for value in prior_changes):
            continue
        change_z = _zscore(
            current_change,
            [float(value) for value in prior_changes if value is not None],
        )
        if None in {n1, n5, d1, change_z}:
            continue
        result.append(
            FeatureBar(
                signal_time_ms=raw[index].signal_time_ms,
                notional_1_z=float(n1),
                notional_5_z=float(n5),
                depth_1_z=float(d1),
                notional_1_change_4bar_z=float(change_z),
            )
        )
    return tuple(result)


def candidate_signal_times(
    candidate: M9CandidateSpec,
    features: tuple[FeatureBar, ...],
    *,
    start_ms: int,
    end_ms: int,
) -> tuple[int, ...]:
    accepted: list[int] = []
    last_time: int | None = None
    minimum_gap = EVENT_COOLDOWN_BARS * FIFTEEN_MIN_MS
    for row in features:
        if not start_ms <= row.signal_time_ms < end_ms:
            continue
        value = float(getattr(row, candidate.feature))
        triggered = value >= Z_THRESHOLD if candidate.threshold_side > 0 else value <= -Z_THRESHOLD
        if not triggered:
            continue
        if last_time is not None and row.signal_time_ms - last_time < minimum_gap:
            continue
        accepted.append(row.signal_time_ms)
        last_time = row.signal_time_ms
    return tuple(accepted)


def _spot_outcome(
    spot: list[Candle] | tuple[Candle, ...],
    index_by_time: dict[int, int],
    signal_time_ms: int,
    horizon_bars: int,
    direction: int,
    *,
    window_end_exclusive_ms: int,
) -> EventOutcome | None:
    signal_index = index_by_time.get(signal_time_ms)
    if signal_index is None:
        return None
    entry_index = signal_index + 1
    exit_index = signal_index + horizon_bars
    if exit_index >= len(spot):
        return None
    signal = spot[signal_index]
    entry = spot[entry_index]
    exit_bar = spot[exit_index]
    if entry.open_time_ms - signal.open_time_ms != FIFTEEN_MIN_MS:
        return None
    if exit_bar.open_time_ms - signal.open_time_ms != horizon_bars * FIFTEEN_MIN_MS:
        return None
    if exit_bar.open_time_ms >= window_end_exclusive_ms:
        return None
    gross = direction * (exit_bar.close / entry.open - 1.0)
    return EventOutcome(
        signal_time_ms=signal_time_ms,
        horizon_bars=horizon_bars,
        gross_signed_return=gross,
        base_net_signed_return=gross - BASE_ROUND_TRIP_COST_BPS / 10_000.0,
        severe_net_signed_return=gross - SEVERE_ROUND_TRIP_COST_BPS / 10_000.0,
    )


def collect_outcomes(
    signal_times: tuple[int, ...],
    spot: list[Candle] | tuple[Candle, ...],
    *,
    horizon_bars: int,
    direction: int,
    window_end_exclusive_ms: int,
) -> tuple[EventOutcome, ...]:
    index_by_time = {bar.open_time_ms: index for index, bar in enumerate(spot)}
    result: list[EventOutcome] = []
    for signal_time in signal_times:
        outcome = _spot_outcome(
            spot,
            index_by_time,
            signal_time,
            horizon_bars,
            direction,
            window_end_exclusive_ms=window_end_exclusive_ms,
        )
        if outcome is not None:
            result.append(outcome)
    return tuple(result)


def baseline_outcomes(
    eligible_times: tuple[int, ...],
    spot: list[Candle] | tuple[Candle, ...],
    *,
    start_ms: int,
    end_ms: int,
    horizon_bars: int,
    direction: int,
) -> tuple[EventOutcome, ...]:
    selected = tuple(time for time in eligible_times if start_ms <= time < end_ms)
    return collect_outcomes(
        selected,
        spot,
        horizon_bars=horizon_bars,
        direction=direction,
        window_end_exclusive_ms=end_ms,
    )


def _utc_day(timestamp_ms: int):
    return datetime.fromtimestamp(timestamp_ms / 1000.0, tz=UTC).date()


def _quarter(timestamp_ms: int) -> str:
    dt = datetime.fromtimestamp(timestamp_ms / 1000.0, tz=UTC)
    return f"{dt.year}Q{(dt.month - 1) // 3 + 1}"


def _one_sided_daily_mean_p_value(outcomes: tuple[EventOutcome, ...]) -> tuple[int, float]:
    grouped: dict[object, list[float]] = defaultdict(list)
    for outcome in outcomes:
        grouped[_utc_day(outcome.signal_time_ms)].append(outcome.base_net_signed_return)
    daily_means = [mean(values) for values in grouped.values()]
    if len(daily_means) < 2:
        return len(daily_means), 1.0
    average = mean(daily_means)
    sample_std = stdev(daily_means)
    if sample_std == 0:
        return len(daily_means), 0.0 if average > 0 else 1.0
    z_score = average / (sample_std / math.sqrt(len(daily_means)))
    p_value = 1.0 - NormalDist().cdf(z_score)
    return len(daily_means), min(max(p_value, 0.0), 1.0)


def benjamini_hochberg(
    p_values: dict[tuple[str, int], float],
) -> dict[tuple[str, int], float]:
    if not p_values:
        return {}
    ordered = sorted(p_values.items(), key=lambda item: (item[1], item[0]))
    total = len(ordered)
    adjusted: dict[tuple[str, int], float] = {}
    running = 1.0
    for reverse_index in range(total - 1, -1, -1):
        key, p_value = ordered[reverse_index]
        rank = reverse_index + 1
        running = min(running, p_value * total / rank)
        adjusted[key] = min(max(running, 0.0), 1.0)
    return adjusted


def _mean_base(outcomes: tuple[EventOutcome, ...]) -> float | None:
    return mean(item.base_net_signed_return for item in outcomes) if outcomes else None


def _quarter_stats(
    outcomes: tuple[EventOutcome, ...],
    baseline: tuple[EventOutcome, ...],
    year: int,
) -> tuple[QuarterStats, ...]:
    result: list[QuarterStats] = []
    for quarter_number in range(1, 5):
        label = f"{year}Q{quarter_number}"
        selected = tuple(item for item in outcomes if _quarter(item.signal_time_ms) == label)
        control = tuple(item for item in baseline if _quarter(item.signal_time_ms) == label)
        selected_mean = _mean_base(selected)
        control_mean = _mean_base(control)
        result.append(
            QuarterStats(
                quarter=label,
                event_count=len(selected),
                mean_base_net=selected_mean,
                baseline_mean_base_net=control_mean,
                baseline_uplift=(
                    selected_mean - control_mean
                    if selected_mean is not None and control_mean is not None
                    else None
                ),
            )
        )
    return tuple(result)


def summarize_outcomes(
    outcomes: tuple[EventOutcome, ...],
    baseline: tuple[EventOutcome, ...],
    *,
    year: int,
    q_value: float = 1.0,
    discovery_pass: bool = False,
    challenge_pass: bool = False,
) -> HorizonStats:
    distinct_days, p_value = _one_sided_daily_mean_p_value(outcomes)
    gross = [item.gross_signed_return for item in outcomes]
    base = [item.base_net_signed_return for item in outcomes]
    severe = [item.severe_net_signed_return for item in outcomes]
    candidate_mean = mean(base) if base else None
    baseline_mean = _mean_base(baseline)
    return HorizonStats(
        event_count=len(outcomes),
        distinct_days=distinct_days,
        mean_gross_signed_return=mean(gross) if gross else None,
        mean_base_net_signed_return=candidate_mean,
        mean_severe_net_signed_return=mean(severe) if severe else None,
        median_base_net_signed_return=median(base) if base else None,
        base_net_win_rate=(sum(value > 0 for value in base) / len(base) if base else None),
        baseline_mean_base_net=baseline_mean,
        baseline_uplift=(
            candidate_mean - baseline_mean
            if candidate_mean is not None and baseline_mean is not None
            else None
        ),
        daily_mean_p_value=p_value,
        fdr_q_value=q_value,
        quarterly=_quarter_stats(outcomes, baseline, year),
        discovery_pass=discovery_pass,
        challenge_pass=challenge_pass,
    )


def _passes_discovery(stats: HorizonStats) -> bool:
    if stats.event_count < MIN_DISCOVERY_EVENTS or stats.distinct_days < MIN_DISCOVERY_DAYS:
        return False
    if stats.mean_base_net_signed_return is None or stats.mean_base_net_signed_return <= 0:
        return False
    if stats.mean_severe_net_signed_return is None or stats.mean_severe_net_signed_return <= 0:
        return False
    if stats.median_base_net_signed_return is None or stats.median_base_net_signed_return <= 0:
        return False
    if stats.baseline_uplift is None or stats.baseline_uplift < BASELINE_UPLIFT:
        return False
    if stats.fdr_q_value > FDR_Q_THRESHOLD:
        return False
    passing_quarters = sum(
        item.event_count >= MIN_DISCOVERY_EVENTS_PER_PASSING_QUARTER
        and item.mean_base_net is not None
        and item.mean_base_net > 0
        and item.baseline_uplift is not None
        and item.baseline_uplift >= BASELINE_UPLIFT
        for item in stats.quarterly
    )
    return passing_quarters >= MIN_DISCOVERY_PASSING_QUARTERS


def _passes_challenge(stats: HorizonStats, *, discovery_pass: bool) -> bool:
    if not discovery_pass:
        return False
    if stats.event_count < MIN_CHALLENGE_EVENTS or stats.distinct_days < MIN_CHALLENGE_DAYS:
        return False
    if stats.mean_base_net_signed_return is None or stats.mean_base_net_signed_return <= 0:
        return False
    if stats.mean_severe_net_signed_return is None or stats.mean_severe_net_signed_return <= 0:
        return False
    if stats.median_base_net_signed_return is None or stats.median_base_net_signed_return <= 0:
        return False
    if stats.baseline_uplift is None or stats.baseline_uplift < BASELINE_UPLIFT:
        return False
    positive_mean_quarters = sum(
        item.event_count >= MIN_CHALLENGE_EVENTS_PER_QUARTER
        and item.mean_base_net is not None
        and item.mean_base_net > 0
        for item in stats.quarterly
    )
    positive_uplift_quarters = sum(
        item.event_count >= MIN_CHALLENGE_EVENTS_PER_QUARTER
        and item.baseline_uplift is not None
        and item.baseline_uplift > 0
        for item in stats.quarterly
    )
    return (
        positive_mean_quarters >= MIN_CHALLENGE_POSITIVE_QUARTERS
        and positive_uplift_quarters >= MIN_CHALLENGE_POSITIVE_QUARTERS
    )


def _with_flags(
    stats: HorizonStats,
    *,
    q_value: float | None = None,
    discovery_pass: bool | None = None,
    challenge_pass: bool | None = None,
) -> HorizonStats:
    return HorizonStats(
        event_count=stats.event_count,
        distinct_days=stats.distinct_days,
        mean_gross_signed_return=stats.mean_gross_signed_return,
        mean_base_net_signed_return=stats.mean_base_net_signed_return,
        mean_severe_net_signed_return=stats.mean_severe_net_signed_return,
        median_base_net_signed_return=stats.median_base_net_signed_return,
        base_net_win_rate=stats.base_net_win_rate,
        baseline_mean_base_net=stats.baseline_mean_base_net,
        baseline_uplift=stats.baseline_uplift,
        daily_mean_p_value=stats.daily_mean_p_value,
        fdr_q_value=stats.fdr_q_value if q_value is None else q_value,
        quarterly=stats.quarterly,
        discovery_pass=stats.discovery_pass if discovery_pass is None else discovery_pass,
        challenge_pass=stats.challenge_pass if challenge_pass is None else challenge_pass,
    )


def evaluate_candidates(
    features: tuple[FeatureBar, ...],
    spot: list[Candle] | tuple[Candle, ...],
) -> tuple[CandidateResult, ...]:
    discovery_start = parse_utc(DISCOVERY_START)
    discovery_end = parse_utc(DISCOVERY_END_EXCLUSIVE)
    challenge_start = parse_utc(CHALLENGE_START)
    challenge_end = parse_utc(CHALLENGE_END_EXCLUSIVE)
    eligible_times = tuple(item.signal_time_ms for item in features)

    baselines: dict[tuple[str, int, int], tuple[EventOutcome, ...]] = {}
    for window_name, start_ms, end_ms in (
        ("discovery", discovery_start, discovery_end),
        ("challenge", challenge_start, challenge_end),
    ):
        for direction in (-1, 1):
            for horizon in HORIZONS_BARS:
                baselines[(window_name, direction, horizon)] = baseline_outcomes(
                    eligible_times,
                    spot,
                    start_ms=start_ms,
                    end_ms=end_ms,
                    horizon_bars=horizon,
                    direction=direction,
                )

    raw_discovery: dict[tuple[str, int], tuple[EventOutcome, ...]] = {}
    raw_challenge: dict[tuple[str, int], tuple[EventOutcome, ...]] = {}
    preliminary: dict[tuple[str, int], HorizonStats] = {}
    p_values: dict[tuple[str, int], float] = {}

    for candidate in M9_CANDIDATES:
        discovery_times = candidate_signal_times(
            candidate,
            features,
            start_ms=discovery_start,
            end_ms=discovery_end,
        )
        challenge_times = candidate_signal_times(
            candidate,
            features,
            start_ms=challenge_start,
            end_ms=challenge_end,
        )
        for horizon in HORIZONS_BARS:
            key = (candidate.name, horizon)
            discovery_outcomes = collect_outcomes(
                discovery_times,
                spot,
                horizon_bars=horizon,
                direction=candidate.direction,
                window_end_exclusive_ms=discovery_end,
            )
            challenge_outcomes = collect_outcomes(
                challenge_times,
                spot,
                horizon_bars=horizon,
                direction=candidate.direction,
                window_end_exclusive_ms=challenge_end,
            )
            raw_discovery[key] = discovery_outcomes
            raw_challenge[key] = challenge_outcomes
            stats = summarize_outcomes(
                discovery_outcomes,
                baselines[("discovery", candidate.direction, horizon)],
                year=2023,
            )
            preliminary[key] = stats
            p_values[key] = stats.daily_mean_p_value

    q_values = benjamini_hochberg(p_values)
    results: list[CandidateResult] = []
    for candidate in M9_CANDIDATES:
        discovery_stats: dict[int, HorizonStats] = {}
        challenge_stats: dict[int, HorizonStats] = {}
        passing: list[int] = []
        for horizon in HORIZONS_BARS:
            key = (candidate.name, horizon)
            with_q = _with_flags(preliminary[key], q_value=q_values[key])
            discovery_pass = _passes_discovery(with_q)
            final_discovery = _with_flags(with_q, discovery_pass=discovery_pass)
            challenge = summarize_outcomes(
                raw_challenge[key],
                baselines[("challenge", candidate.direction, horizon)],
                year=2024,
                discovery_pass=discovery_pass,
            )
            challenge_pass = _passes_challenge(challenge, discovery_pass=discovery_pass)
            final_challenge = _with_flags(
                challenge,
                discovery_pass=discovery_pass,
                challenge_pass=challenge_pass,
            )
            discovery_stats[horizon] = final_discovery
            challenge_stats[horizon] = final_challenge
            if discovery_pass and challenge_pass:
                passing.append(horizon)

        if passing:
            classification = (
                "LONG_EDGE_CANDIDATE" if candidate.direction > 0 else "NO_TRADE_VETO_CANDIDATE"
            )
        else:
            classification = "OBSERVATION_ONLY"
        results.append(
            CandidateResult(
                candidate=candidate,
                classification=classification,
                passing_horizons=tuple(passing),
                discovery=discovery_stats,
                challenge=challenge_stats,
            )
        )
    return tuple(results)


def _load_spot_inputs(spot_dir: Path) -> list[Candle]:
    research_path = spot_dir / "btcusdt_15m_research.csv"
    challenge_path = spot_dir / "btcusdt_15m_validation.csv"
    expected = {
        research_path: SPOT_RESEARCH_SHA256,
        challenge_path: SPOT_CHALLENGE_SHA256,
    }
    for path, expected_hash in expected.items():
        if not path.is_file():
            raise FileNotFoundError(path)
        if sha256_file(path) != expected_hash:
            raise RuntimeError(f"M9 frozen Spot input hash mismatch: {path}")

    discovery_start = parse_utc(DISCOVERY_START)
    discovery_end = parse_utc(DISCOVERY_END_EXCLUSIVE)
    challenge_start = parse_utc(CHALLENGE_START)
    challenge_end = parse_utc(CHALLENGE_END_EXCLUSIVE)
    for label, start_ms, end_ms in (
        ("M9 discovery", discovery_start, discovery_end),
        ("M9 challenge", challenge_start, challenge_end),
    ):
        assert_not_first_cycle_oos_overlap(
            symbol=FIRST_CYCLE_SYMBOL,
            interval=FIRST_CYCLE_INTERVAL,
            start_ms=start_ms,
            end_ms=end_ms,
            context=label,
        )

    research_all = load_csv(research_path)
    research_slice = [
        candle for candle in research_all if discovery_start <= candle.open_time_ms < discovery_end
    ]
    challenge_all = load_csv(challenge_path)
    challenge_slice = [
        candle for candle in challenge_all if challenge_start <= candle.open_time_ms < challenge_end
    ]
    gaps = allowed_source_gap_ranges(FIRST_CYCLE_SYMBOL, FIRST_CYCLE_INTERVAL)
    close_times = allowed_source_close_times(FIRST_CYCLE_SYMBOL, FIRST_CYCLE_INTERVAL)
    research = validate_interval_window(
        research_slice,
        FIRST_CYCLE_INTERVAL,
        discovery_start,
        discovery_end,
        allowed_missing_ranges=gaps,
        allowed_close_times=close_times,
    )
    challenge = validate_interval_window(
        challenge_slice,
        FIRST_CYCLE_INTERVAL,
        challenge_start,
        challenge_end,
        allowed_missing_ranges=gaps,
        allowed_close_times=close_times,
    )
    return [*research, *challenge]


def _feature_sha256(rows: tuple[FeatureBar, ...]) -> str:
    digest = hashlib.sha256()
    for row in rows:
        digest.update(
            json.dumps(
                asdict(row),
                sort_keys=True,
                separators=(",", ":"),
                allow_nan=False,
            ).encode("utf-8")
        )
        digest.update(b"\n")
    return digest.hexdigest()


def _json_safe(value: Any) -> Any:
    if isinstance(value, float) and not math.isfinite(value):
        return None
    if isinstance(value, dict):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(item) for item in value]
    return value


def _candidate_payload(result: CandidateResult) -> dict[str, Any]:
    return {
        "candidate": asdict(result.candidate),
        "classification": result.classification,
        "passing_horizons": list(result.passing_horizons),
        "discovery": {str(horizon): asdict(stats) for horizon, stats in result.discovery.items()},
        "challenge": {str(horizon): asdict(stats) for horizon, stats in result.challenge.items()},
    }


def _write_report_once(output: Path, payload: dict[str, Any]) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    try:
        with output.open("x", encoding="utf-8") as handle:
            handle.write(json.dumps(payload, indent=2, sort_keys=True, allow_nan=False))
    except FileExistsError as error:
        raise RuntimeError("M9 report already exists; preserve the first frozen result") from error


def run_m9_edge_discovery(
    *,
    spot_dir: str | Path = "data/cache/m2",
    report_path: str | Path = "artifacts/m9_bookdepth_microstructure_edge.json",
    workers: int = 12,
) -> dict[str, Any]:
    output = Path(report_path)
    if output.exists():
        raise RuntimeError("M9 report already exists; preserve the first frozen result")
    freeze = verify_m9_freeze()
    provenance = collect_source_provenance(require_clean=True)
    raw_features, source = fetch_bookdepth_features(workers=workers)
    if source.get("status") != "PASS":
        raise RuntimeError("M9 bookDepth source integrity changed from the frozen eligible state")
    features = standardize_feature_bars(raw_features)
    if not features:
        raise RuntimeError("M9 produced no standardized microstructure features")
    spot = _load_spot_inputs(Path(spot_dir))
    results = evaluate_candidates(features, spot)

    long_edges = [
        item.candidate.name for item in results if item.classification == "LONG_EDGE_CANDIDATE"
    ]
    veto_edges = [
        item.candidate.name
        for item in results
        if item.classification == "NO_TRADE_VETO_CANDIDATE"
    ]
    decision = (
        "MICROSTRUCTURE_EDGE_CANDIDATES_FOUND"
        if long_edges or veto_edges
        else "NO_STABLE_MICROSTRUCTURE_EDGE_FOUND"
    )
    report: dict[str, Any] = {
        "phase": "m9_bookdepth_microstructure_edge_discovery_development_only",
        "decision": decision,
        "policy_freeze": freeze,
        "source_provenance": provenance,
        "data_boundary": {
            "discovery": f"{DISCOVERY_START}/{DISCOVERY_END_EXCLUSIVE}",
            "challenge": f"{CHALLENGE_START}/{CHALLENGE_END_EXCLUSIVE}",
            "oos_2025": "LOCKED_NOT_ACCESSED",
        },
        "bookdepth_source_audit": source,
        "standardized_feature_bars": len(features),
        "feature_dataset_sha256": _feature_sha256(features),
        "spot_input_sha256": {
            "research": SPOT_RESEARCH_SHA256,
            "challenge": SPOT_CHALLENGE_SHA256,
        },
        "search": {
            "candidate_count": len(M9_CANDIDATES),
            "horizons_bars": list(HORIZONS_BARS),
            "hypothesis_test_count": len(M9_CANDIDATES) * len(HORIZONS_BARS),
            "long_edge_candidates": long_edges,
            "no_trade_veto_candidates": veto_edges,
        },
        "results": [_candidate_payload(item) for item in results],
        "strategy_generation": "NOT_RUN",
        "risk_sizing": "NOT_RUN",
        "ai_module": "EXCLUDED",
        "live_execution": "FORBIDDEN",
        "oos_2025": "LOCKED_NOT_ACCESSED",
    }
    safe = _json_safe(report)
    _write_report_once(output, safe)
    return safe


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run frozen M9 Binance bookDepth microstructure edge discovery"
    )
    parser.add_argument("--spot-dir", default="data/cache/m2")
    parser.add_argument("--report", default="artifacts/m9_bookdepth_microstructure_edge.json")
    parser.add_argument("--workers", type=int, default=12)
    args = parser.parse_args()
    report = run_m9_edge_discovery(
        spot_dir=args.spot_dir,
        report_path=args.report,
        workers=args.workers,
    )
    search = report["search"]
    if not isinstance(search, dict):
        raise RuntimeError("Invalid M9 report search section")
    print(f"M9 decision: {report['decision']}")
    print(f"LONG_EDGE_CANDIDATE: {len(search['long_edge_candidates'])}")
    print(f"NO_TRADE_VETO_CANDIDATE: {len(search['no_trade_veto_candidates'])}")
    print(f"standardized_feature_bars: {report['standardized_feature_bars']}")
    print("2025 OOS remains LOCKED_NOT_ACCESSED")


if __name__ == "__main__":
    main()
