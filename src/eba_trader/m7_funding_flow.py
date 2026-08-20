from __future__ import annotations

import argparse
import json
import math
from bisect import bisect_right
from collections import defaultdict
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from statistics import NormalDist, mean, median, stdev
from typing import Any

from .data_policy import allowed_source_close_times, allowed_source_gap_ranges
from .derivatives_audit import (
    DerivativeKline,
    FundingRecord,
    _load_funding_csv,
    _load_kline_csv,
    audit_funding,
    audit_klines,
)
from .derivatives_audit_policy import EXPECTED_15M_SLOTS
from .history import Candle, load_csv, parse_utc, validate_interval_window
from .holdout_guard import assert_not_first_cycle_oos_overlap
from .m7_funding_flow_policy import (
    ACTIVITY_BASELINE_WINDOWS,
    BASELINE_UPLIFT,
    BASE_ROUND_TRIP_COST_BPS,
    CHALLENGE_END_EXCLUSIVE,
    CHALLENGE_START,
    DISCOVERY_END_EXCLUSIVE,
    DISCOVERY_START,
    EVENT_COOLDOWN_BARS,
    FDR_Q_THRESHOLD,
    FUNDING_LOOKBACK_RECORDS,
    FUNDING_SHA256,
    FUTURES_SHA256,
    HORIZONS_BARS,
    M7_CANDIDATES,
    MIN_CHALLENGE_EVENTS,
    MIN_DISCOVERY_DAYS,
    MIN_DISCOVERY_EVENTS,
    MIN_DISCOVERY_EVENTS_PER_YEAR,
    SEVERE_ROUND_TRIP_COST_BPS,
    SPOT_CHALLENGE_SHA256,
    SPOT_RESEARCH_SHA256,
    M7CandidateSpec,
    sha256_file,
    verify_m7_freeze,
)
from .provenance import collect_source_provenance
from .study_policy import FIRST_CYCLE_INTERVAL, FIRST_CYCLE_SYMBOL

FIFTEEN_MINUTES_MS = 15 * 60 * 1000
DISCOVERY_YEARS = (2021, 2022, 2023)


@dataclass(frozen=True, slots=True)
class FlowFeature:
    taker_buy_share: float
    quote_volume_intensity: float
    trade_count_intensity: float
    price_return: float


@dataclass(frozen=True, slots=True)
class FuturesFeatures:
    bars: tuple[DerivativeKline, ...]
    flow_1h: tuple[FlowFeature | None, ...]
    flow_4h: tuple[FlowFeature | None, ...]


@dataclass(frozen=True, slots=True)
class FundingEvent:
    funding_index: int
    funding_time_ms: int
    futures_bar_index: int
    funding_rate: float
    q10: float
    q90: float
    extreme_negative: bool
    extreme_positive: bool


@dataclass(frozen=True, slots=True)
class EventOutcome:
    signal_time_ms: int
    horizon_bars: int
    gross_signed_return: float
    base_net_signed_return: float
    severe_net_signed_return: float


@dataclass(frozen=True, slots=True)
class YearStats:
    year: int
    event_count: int
    mean_base_net: float | None
    mean_severe_net: float | None
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
    yearly: tuple[YearStats, ...]
    discovery_pass: bool
    challenge_pass: bool


@dataclass(frozen=True, slots=True)
class CandidateResult:
    candidate: M7CandidateSpec
    classification: str
    passing_horizons: tuple[int, ...]
    discovery: dict[int, HorizonStats]
    challenge: dict[int, HorizonStats]


def _is_contiguous(previous: DerivativeKline, current: DerivativeKline) -> bool:
    return current.open_time_ms - previous.open_time_ms == FIFTEEN_MINUTES_MS


def linear_percentile(values: list[float] | tuple[float, ...], percentile: float) -> float:
    if not 0 <= percentile <= 1:
        raise ValueError("percentile must be in [0, 1]")
    ordered = sorted(values)
    if not ordered:
        raise ValueError("percentile requires at least one value")
    if len(ordered) == 1:
        return ordered[0]
    position = percentile * (len(ordered) - 1)
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return ordered[lower]
    fraction = position - lower
    return ordered[lower] * (1.0 - fraction) + ordered[upper] * fraction


def _window_totals(
    bars: list[DerivativeKline],
    window: int,
) -> tuple[list[float | None], list[int | None], list[float | None], list[float | None]]:
    quote_totals: list[float | None] = [None] * len(bars)
    trade_totals: list[int | None] = [None] * len(bars)
    volume_totals: list[float | None] = [None] * len(bars)
    taker_totals: list[float | None] = [None] * len(bars)
    streak = 0
    for index, bar in enumerate(bars):
        streak = streak + 1 if index > 0 and _is_contiguous(bars[index - 1], bar) else 1
        if streak < window:
            continue
        selected = bars[index - window + 1 : index + 1]
        if any(
            item.quote_volume is None
            or item.trade_count is None
            or item.volume is None
            or item.taker_buy_base_volume is None
            for item in selected
        ):
            continue
        quote_totals[index] = sum(float(item.quote_volume) for item in selected)
        trade_totals[index] = sum(int(item.trade_count) for item in selected)
        volume_totals[index] = sum(float(item.volume) for item in selected)
        taker_totals[index] = sum(float(item.taker_buy_base_volume) for item in selected)
    return quote_totals, trade_totals, volume_totals, taker_totals


def _prior_median(values: list[float | int | None], index: int) -> float | None:
    if index < ACTIVITY_BASELINE_WINDOWS:
        return None
    prior = values[index - ACTIVITY_BASELINE_WINDOWS : index]
    if len(prior) != ACTIVITY_BASELINE_WINDOWS or any(value is None for value in prior):
        return None
    return float(median(float(value) for value in prior if value is not None))


def _flow_features_for_window(
    bars: list[DerivativeKline],
    window: int,
) -> tuple[FlowFeature | None, ...]:
    quote, trades, volume, taker = _window_totals(bars, window)
    result: list[FlowFeature | None] = [None] * len(bars)
    for index, bar in enumerate(bars):
        current_quote = quote[index]
        current_trades = trades[index]
        current_volume = volume[index]
        current_taker = taker[index]
        if (
            current_quote is None
            or current_trades is None
            or current_volume is None
            or current_taker is None
            or current_volume <= 0
        ):
            continue
        quote_median = _prior_median(quote, index)
        trade_median = _prior_median(trades, index)
        if quote_median is None or quote_median <= 0 or trade_median is None or trade_median <= 0:
            continue
        first_bar = bars[index - window + 1]
        if first_bar.open <= 0:
            continue
        result[index] = FlowFeature(
            taker_buy_share=current_taker / current_volume,
            quote_volume_intensity=current_quote / quote_median,
            trade_count_intensity=current_trades / trade_median,
            price_return=bar.close / first_bar.open - 1.0,
        )
    return tuple(result)


def prepare_futures_features(
    rows: list[DerivativeKline] | tuple[DerivativeKline, ...],
) -> FuturesFeatures:
    bars = list(rows)
    if not bars:
        raise ValueError("M7 futures features require rows")
    return FuturesFeatures(
        bars=tuple(bars),
        flow_1h=_flow_features_for_window(bars, 4),
        flow_4h=_flow_features_for_window(bars, 16),
    )


def build_funding_events(
    funding: list[FundingRecord] | tuple[FundingRecord, ...],
    futures: FuturesFeatures,
) -> tuple[FundingEvent, ...]:
    records = list(funding)
    bars = futures.bars
    open_times = [bar.open_time_ms for bar in bars]
    events: list[FundingEvent] = []
    for funding_index in range(FUNDING_LOOKBACK_RECORDS, len(records)):
        record = records[funding_index]
        bar_index = bisect_right(open_times, record.funding_time_ms) - 1
        if bar_index < 0:
            continue
        bar = bars[bar_index]
        if not bar.open_time_ms <= record.funding_time_ms <= bar.close_time_ms:
            continue
        prior_rates = [
            item.funding_rate
            for item in records[funding_index - FUNDING_LOOKBACK_RECORDS : funding_index]
        ]
        q10 = linear_percentile(prior_rates, 0.10)
        q90 = linear_percentile(prior_rates, 0.90)
        events.append(
            FundingEvent(
                funding_index=funding_index,
                funding_time_ms=record.funding_time_ms,
                futures_bar_index=bar_index,
                funding_rate=record.funding_rate,
                q10=q10,
                q90=q90,
                extreme_negative=record.funding_rate < 0 and record.funding_rate <= q10,
                extreme_positive=record.funding_rate > 0 and record.funding_rate >= q90,
            )
        )
    return tuple(events)


def _share_matches(candidate: M7CandidateSpec, feature: FlowFeature) -> bool:
    if candidate.taker_share_min is not None and feature.taker_buy_share < candidate.taker_share_min:
        return False
    if candidate.taker_share_max is not None and feature.taker_buy_share > candidate.taker_share_max:
        return False
    return True


def flow_candidate_matches(
    candidate: M7CandidateSpec,
    features: FuturesFeatures,
    index: int,
) -> bool:
    if candidate.family not in {"flow", "neutral_flow"} or candidate.window_bars is None:
        raise ValueError("flow_candidate_matches requires a flow candidate")
    feature = features.flow_1h[index] if candidate.window_bars == 4 else features.flow_4h[index]
    if feature is None or not _share_matches(candidate, feature):
        return False
    if (
        candidate.quote_intensity_min is not None
        and feature.quote_volume_intensity < candidate.quote_intensity_min
    ):
        return False
    if (
        candidate.trade_intensity_min is not None
        and feature.trade_count_intensity < candidate.trade_intensity_min
    ):
        return False
    if candidate.abs_return_max is not None and abs(feature.price_return) > candidate.abs_return_max:
        return False
    return True


def _funding_side_matches(candidate: M7CandidateSpec, event: FundingEvent) -> bool:
    if candidate.funding_side == -1:
        return event.extreme_negative
    if candidate.funding_side == 1:
        return event.extreme_positive
    raise ValueError("Funding candidate is missing funding_side")


def candidate_signal_indices(
    candidate: M7CandidateSpec,
    futures: FuturesFeatures,
    funding_events: tuple[FundingEvent, ...],
    *,
    signal_start_ms: int,
    signal_end_exclusive_ms: int,
) -> tuple[int, ...]:
    if candidate.family in {"flow", "neutral_flow"}:
        accepted: list[int] = []
        last_index: int | None = None
        for index, bar in enumerate(futures.bars):
            if not signal_start_ms <= bar.open_time_ms < signal_end_exclusive_ms:
                continue
            if last_index is not None and index - last_index < EVENT_COOLDOWN_BARS:
                continue
            if flow_candidate_matches(candidate, futures, index):
                accepted.append(index)
                last_index = index
        return tuple(accepted)

    accepted_funding: list[int] = []
    for event in funding_events:
        if not _funding_side_matches(candidate, event):
            continue
        signal_index = event.futures_bar_index
        if candidate.family == "funding_flow":
            signal_index += 3
            if signal_index >= len(futures.bars):
                continue
            first = futures.bars[event.futures_bar_index]
            last = futures.bars[signal_index]
            if last.open_time_ms - first.open_time_ms != 3 * FIFTEEN_MINUTES_MS:
                continue
            feature = futures.flow_1h[signal_index]
            if feature is None or not _share_matches(candidate, feature):
                continue
        signal_time = futures.bars[signal_index].open_time_ms
        if signal_start_ms <= signal_time < signal_end_exclusive_ms:
            accepted_funding.append(signal_index)
    return tuple(accepted_funding)


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
    if entry.open_time_ms - signal.open_time_ms != FIFTEEN_MINUTES_MS:
        return None
    if exit_bar.open_time_ms - signal.open_time_ms != horizon_bars * FIFTEEN_MINUTES_MS:
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
    signal_indices: tuple[int, ...],
    futures: FuturesFeatures,
    spot: list[Candle] | tuple[Candle, ...],
    index_by_time: dict[int, int],
    *,
    horizon_bars: int,
    direction: int,
    window_end_exclusive_ms: int,
) -> tuple[EventOutcome, ...]:
    outcomes: list[EventOutcome] = []
    for index in signal_indices:
        outcome = _spot_outcome(
            spot,
            index_by_time,
            futures.bars[index].open_time_ms,
            horizon_bars,
            direction,
            window_end_exclusive_ms=window_end_exclusive_ms,
        )
        if outcome is not None:
            outcomes.append(outcome)
    return tuple(outcomes)


def baseline_outcomes(
    spot: list[Candle] | tuple[Candle, ...],
    *,
    signal_start_ms: int,
    signal_end_exclusive_ms: int,
    horizon_bars: int,
    direction: int,
) -> tuple[EventOutcome, ...]:
    index_by_time = {bar.open_time_ms: index for index, bar in enumerate(spot)}
    outcomes: list[EventOutcome] = []
    for bar in spot:
        if not signal_start_ms <= bar.open_time_ms < signal_end_exclusive_ms:
            continue
        outcome = _spot_outcome(
            spot,
            index_by_time,
            bar.open_time_ms,
            horizon_bars,
            direction,
            window_end_exclusive_ms=signal_end_exclusive_ms,
        )
        if outcome is not None:
            outcomes.append(outcome)
    return tuple(outcomes)


def _utc_day(timestamp_ms: int):
    return datetime.fromtimestamp(timestamp_ms / 1000.0, tz=UTC).date()


def _utc_year(timestamp_ms: int) -> int:
    return datetime.fromtimestamp(timestamp_ms / 1000.0, tz=UTC).year


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


def _year_stats(
    outcomes: tuple[EventOutcome, ...],
    baseline: tuple[EventOutcome, ...],
    years: tuple[int, ...],
) -> tuple[YearStats, ...]:
    result: list[YearStats] = []
    for year in years:
        selected = tuple(item for item in outcomes if _utc_year(item.signal_time_ms) == year)
        control = tuple(item for item in baseline if _utc_year(item.signal_time_ms) == year)
        selected_mean = _mean_base(selected)
        control_mean = _mean_base(control)
        result.append(
            YearStats(
                year=year,
                event_count=len(selected),
                mean_base_net=selected_mean,
                mean_severe_net=(
                    mean(item.severe_net_signed_return for item in selected) if selected else None
                ),
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
    discovery: bool,
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
        yearly=_year_stats(outcomes, baseline, DISCOVERY_YEARS) if discovery else (),
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
    by_year = {item.year: item for item in stats.yearly}
    for year in DISCOVERY_YEARS:
        item = by_year.get(year)
        if (
            item is None
            or item.event_count < MIN_DISCOVERY_EVENTS_PER_YEAR
            or item.mean_base_net is None
            or item.mean_base_net <= 0
            or item.baseline_uplift is None
            or item.baseline_uplift < BASELINE_UPLIFT
        ):
            return False
    return True


def _passes_challenge(stats: HorizonStats, *, discovery_pass: bool) -> bool:
    if not discovery_pass or stats.event_count < MIN_CHALLENGE_EVENTS:
        return False
    return (
        stats.mean_base_net_signed_return is not None
        and stats.mean_base_net_signed_return > 0
        and stats.mean_severe_net_signed_return is not None
        and stats.mean_severe_net_signed_return > 0
        and stats.median_base_net_signed_return is not None
        and stats.median_base_net_signed_return > 0
        and stats.baseline_uplift is not None
        and stats.baseline_uplift >= BASELINE_UPLIFT
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
        yearly=stats.yearly,
        discovery_pass=stats.discovery_pass if discovery_pass is None else discovery_pass,
        challenge_pass=stats.challenge_pass if challenge_pass is None else challenge_pass,
    )


def evaluate_candidates(
    futures: FuturesFeatures,
    funding_events: tuple[FundingEvent, ...],
    spot: list[Candle] | tuple[Candle, ...],
) -> tuple[CandidateResult, ...]:
    discovery_start = parse_utc(DISCOVERY_START)
    discovery_end = parse_utc(DISCOVERY_END_EXCLUSIVE)
    challenge_start = parse_utc(CHALLENGE_START)
    challenge_end = parse_utc(CHALLENGE_END_EXCLUSIVE)
    spot_index = {bar.open_time_ms: index for index, bar in enumerate(spot)}

    baselines: dict[tuple[str, int, int], tuple[EventOutcome, ...]] = {}
    for window_name, start_ms, end_ms in (
        ("discovery", discovery_start, discovery_end),
        ("challenge", challenge_start, challenge_end),
    ):
        for direction in (-1, 1):
            for horizon in HORIZONS_BARS:
                baselines[(window_name, direction, horizon)] = baseline_outcomes(
                    spot,
                    signal_start_ms=start_ms,
                    signal_end_exclusive_ms=end_ms,
                    horizon_bars=horizon,
                    direction=direction,
                )

    raw_discovery: dict[tuple[str, int], tuple[EventOutcome, ...]] = {}
    raw_challenge: dict[tuple[str, int], tuple[EventOutcome, ...]] = {}
    preliminary: dict[tuple[str, int], HorizonStats] = {}
    p_values: dict[tuple[str, int], float] = {}

    for candidate in M7_CANDIDATES:
        discovery_indices = candidate_signal_indices(
            candidate,
            futures,
            funding_events,
            signal_start_ms=discovery_start,
            signal_end_exclusive_ms=discovery_end,
        )
        challenge_indices = candidate_signal_indices(
            candidate,
            futures,
            funding_events,
            signal_start_ms=challenge_start,
            signal_end_exclusive_ms=challenge_end,
        )
        for horizon in HORIZONS_BARS:
            key = (candidate.name, horizon)
            discovery_outcomes = collect_outcomes(
                discovery_indices,
                futures,
                spot,
                spot_index,
                horizon_bars=horizon,
                direction=candidate.direction,
                window_end_exclusive_ms=discovery_end,
            )
            challenge_outcomes = collect_outcomes(
                challenge_indices,
                futures,
                spot,
                spot_index,
                horizon_bars=horizon,
                direction=candidate.direction,
                window_end_exclusive_ms=challenge_end,
            )
            raw_discovery[key] = discovery_outcomes
            raw_challenge[key] = challenge_outcomes
            stats = summarize_outcomes(
                discovery_outcomes,
                baselines[("discovery", candidate.direction, horizon)],
                discovery=True,
            )
            preliminary[key] = stats
            p_values[key] = stats.daily_mean_p_value

    q_values = benjamini_hochberg(p_values)
    results: list[CandidateResult] = []
    for candidate in M7_CANDIDATES:
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
                discovery=False,
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
                "LONG_EDGE_CANDIDATE"
                if candidate.direction > 0
                else "NO_TRADE_VETO_CANDIDATE"
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


def _load_frozen_inputs(
    *,
    m6_dir: Path,
    spot_dir: Path,
) -> tuple[list[FundingRecord], list[DerivativeKline], list[Candle]]:
    funding_path = m6_dir / "btcusdt_usdm_funding_2021_2024.csv"
    futures_path = m6_dir / "btcusdt_usdm_perpetual_15m_2021_2024.csv"
    research_path = spot_dir / "btcusdt_15m_research.csv"
    challenge_path = spot_dir / "btcusdt_15m_validation.csv"

    expected = {
        funding_path: FUNDING_SHA256,
        futures_path: FUTURES_SHA256,
        research_path: SPOT_RESEARCH_SHA256,
        challenge_path: SPOT_CHALLENGE_SHA256,
    }
    for path, expected_hash in expected.items():
        if not path.is_file():
            raise FileNotFoundError(path)
        if sha256_file(path) != expected_hash:
            raise RuntimeError(f"M7 frozen input hash mismatch: {path}")

    discovery_start = parse_utc(DISCOVERY_START)
    discovery_end = parse_utc(DISCOVERY_END_EXCLUSIVE)
    challenge_start = parse_utc(CHALLENGE_START)
    challenge_end = parse_utc(CHALLENGE_END_EXCLUSIVE)
    for label, start_ms, end_ms in (
        ("M7 discovery", discovery_start, discovery_end),
        ("M7 challenge", challenge_start, challenge_end),
    ):
        assert_not_first_cycle_oos_overlap(
            symbol=FIRST_CYCLE_SYMBOL,
            interval=FIRST_CYCLE_INTERVAL,
            start_ms=start_ms,
            end_ms=end_ms,
            context=label,
        )

    funding = _load_funding_csv(funding_path)
    futures = _load_kline_csv(futures_path)
    funding_check = audit_funding(
        funding,
        start_ms=discovery_start,
        end_ms=challenge_end,
    )
    futures_check = audit_klines(
        futures,
        start_ms=discovery_start,
        end_ms=challenge_end,
        allow_nonpositive_prices=False,
        futures_activity=True,
    )
    if funding_check["status"] != "PASS" or futures_check["status"] != "PASS":
        raise RuntimeError("M7 requires the M6-PASS funding and futures datasets")

    gaps = allowed_source_gap_ranges(FIRST_CYCLE_SYMBOL, FIRST_CYCLE_INTERVAL)
    close_times = allowed_source_close_times(FIRST_CYCLE_SYMBOL, FIRST_CYCLE_INTERVAL)
    research = validate_interval_window(
        load_csv(research_path),
        FIRST_CYCLE_INTERVAL,
        discovery_start,
        discovery_end,
        allowed_missing_ranges=gaps,
        allowed_close_times=close_times,
    )
    challenge = validate_interval_window(
        load_csv(challenge_path),
        FIRST_CYCLE_INTERVAL,
        challenge_start,
        challenge_end,
        allowed_missing_ranges=gaps,
        allowed_close_times=close_times,
    )
    combined = [*research, *challenge]
    return funding, futures, combined


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
        "discovery": {
            str(horizon): asdict(stats) for horizon, stats in result.discovery.items()
        },
        "challenge": {
            str(horizon): asdict(stats) for horizon, stats in result.challenge.items()
        },
    }


def _write_report_once(output: Path, payload: dict[str, Any]) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    try:
        with output.open("x", encoding="utf-8") as handle:
            handle.write(json.dumps(payload, indent=2, sort_keys=True, allow_nan=False))
    except FileExistsError as error:
        raise RuntimeError("M7 report already exists; preserve the first frozen-search result") from error


def run_m7_edge_discovery(
    *,
    m6_dir: str | Path = "data/cache/m6",
    spot_dir: str | Path = "data/cache/m2",
    report_path: str | Path = "artifacts/m7_funding_futures_edge_discovery.json",
) -> dict[str, Any]:
    output = Path(report_path)
    if output.exists():
        raise RuntimeError("M7 report already exists; preserve the first frozen-search result")

    freeze = verify_m7_freeze()
    provenance = collect_source_provenance(require_clean=True)
    funding, futures_rows, spot = _load_frozen_inputs(
        m6_dir=Path(m6_dir),
        spot_dir=Path(spot_dir),
    )
    futures = prepare_futures_features(futures_rows)
    funding_events = build_funding_events(funding, futures)
    results = evaluate_candidates(futures, funding_events, spot)

    long_edges = [
        item.candidate.name
        for item in results
        if item.classification == "LONG_EDGE_CANDIDATE"
    ]
    veto_edges = [
        item.candidate.name
        for item in results
        if item.classification == "NO_TRADE_VETO_CANDIDATE"
    ]
    decision = (
        "DERIVATIVES_EDGE_CANDIDATES_FOUND"
        if long_edges or veto_edges
        else "NO_STABLE_DERIVATIVES_EDGE_FOUND"
    )
    report: dict[str, Any] = {
        "phase": "m7_funding_futures_edge_discovery_development_only",
        "decision": decision,
        "policy_freeze": freeze,
        "source_provenance": provenance,
        "data_boundary": {
            "discovery": f"{DISCOVERY_START}/{DISCOVERY_END_EXCLUSIVE}",
            "challenge": f"{CHALLENGE_START}/{CHALLENGE_END_EXCLUSIVE}",
            "oos_2025": "LOCKED_NOT_ACCESSED",
        },
        "input_sha256": {
            "funding_2021_2024": FUNDING_SHA256,
            "futures_15m_2021_2024": FUTURES_SHA256,
            "spot_research_2021_2023": SPOT_RESEARCH_SHA256,
            "spot_challenge_2024": SPOT_CHALLENGE_SHA256,
        },
        "search_space": {
            "candidate_count": len(M7_CANDIDATES),
            "horizons_bars": list(HORIZONS_BARS),
            "hypothesis_test_count": len(M7_CANDIDATES) * len(HORIZONS_BARS),
            "fdr_q_threshold": FDR_Q_THRESHOLD,
            "baseline_uplift": BASELINE_UPLIFT,
            "base_round_trip_cost_bps": BASE_ROUND_TRIP_COST_BPS,
            "severe_round_trip_cost_bps": SEVERE_ROUND_TRIP_COST_BPS,
        },
        "classification_summary": {
            "long_edge_candidates": long_edges,
            "no_trade_veto_candidates": veto_edges,
            "observation_only_count": sum(
                item.classification == "OBSERVATION_ONLY" for item in results
            ),
            "passing_candidate_horizons": sum(len(item.passing_horizons) for item in results),
        },
        "candidates": [_candidate_payload(item) for item in results],
        "strategy_generation": "FORBIDDEN_REQUIRES_SEPARATE_FROZEN_STRATEGY_CONTRACT",
        "ai_module": "excluded",
        "live_execution": "forbidden",
        "oos_2025": "LOCKED_NOT_ACCESSED",
    }
    safe = _json_safe(report)
    _write_report_once(output, safe)
    return safe


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run frozen M7 funding + futures-activity edge discovery on 2021-2024 only"
    )
    parser.add_argument("--m6-dir", default="data/cache/m6")
    parser.add_argument("--spot-dir", default="data/cache/m2")
    parser.add_argument("--report", default="artifacts/m7_funding_futures_edge_discovery.json")
    args = parser.parse_args()
    report = run_m7_edge_discovery(
        m6_dir=args.m6_dir,
        spot_dir=args.spot_dir,
        report_path=args.report,
    )
    summary = report["classification_summary"]
    print(f"M7 decision: {report['decision']}")
    print(f"LONG_EDGE_CANDIDATE: {len(summary['long_edge_candidates'])}")
    print(f"NO_TRADE_VETO_CANDIDATE: {len(summary['no_trade_veto_candidates'])}")
    print(f"Passing candidate-horizons: {summary['passing_candidate_horizons']}")
    print("2025 OOS remains LOCKED_NOT_ACCESSED")


if __name__ == "__main__":
    main()
