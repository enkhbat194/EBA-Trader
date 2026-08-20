from __future__ import annotations

import argparse
import json
import math
from bisect import bisect_left, insort
from collections import defaultdict, deque
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from statistics import NormalDist, mean, median, stdev
from typing import Any

from .data_policy import allowed_source_close_times, allowed_source_gap_ranges
from .edge_discovery_policy import (
    ATR_PERIOD,
    BASE_ROUND_TRIP_COST_BPS,
    BREAKOUT_LOOKBACK_BARS,
    CHALLENGE_END_EXCLUSIVE,
    CHALLENGE_START,
    DISCOVERY_END_EXCLUSIVE,
    DISCOVERY_START,
    EDGE_CANDIDATES,
    EDGE_DISCOVERY_CHALLENGE_SHA256,
    EDGE_DISCOVERY_RESEARCH_SHA256,
    EVENT_COOLDOWN_BARS,
    FDR_Q_THRESHOLD,
    HORIZONS_BARS,
    MIN_CHALLENGE_EVENTS,
    MIN_DISCOVERY_DAYS,
    MIN_DISCOVERY_EVENTS,
    MIN_DISCOVERY_EVENTS_PER_YEAR,
    ROLLING_WINDOW_BARS,
    SEVERE_ROUND_TRIP_COST_BPS,
    EdgeCandidateSpec,
    sha256_file,
    verify_edge_discovery_freeze,
)
from .history import Candle, load_csv, parse_utc, validate_interval_window
from .holdout_guard import assert_not_first_cycle_oos_overlap
from .provenance import collect_source_provenance
from .study_policy import (
    FIRST_CYCLE_INTERVAL,
    FIRST_CYCLE_SYMBOL,
)

FIFTEEN_MINUTES_MS = 15 * 60 * 1000
DISCOVERY_YEARS = (2021, 2022, 2023)


@dataclass(frozen=True, slots=True)
class EdgeFeatures:
    bars: tuple[Candle, ...]
    contiguous_streak: tuple[int, ...]
    atr: tuple[float | None, ...]
    ret_1h: tuple[float | None, ...]
    ret_4h: tuple[float | None, ...]
    prior_vwap: tuple[float | None, ...]
    prior_median_volume: tuple[float | None, ...]
    vwap_displacement_atr: tuple[float | None, ...]
    prior_high_20: tuple[float | None, ...]
    prior_low_20: tuple[float | None, ...]
    relative_atr: tuple[float | None, ...]


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


@dataclass(frozen=True, slots=True)
class HorizonStats:
    event_count: int
    distinct_days: int
    mean_gross_signed_return: float | None
    mean_base_net_signed_return: float | None
    mean_severe_net_signed_return: float | None
    median_base_net_signed_return: float | None
    base_net_win_rate: float | None
    daily_mean_p_value: float
    fdr_q_value: float
    yearly: tuple[YearStats, ...]
    discovery_pass: bool
    challenge_pass: bool


@dataclass(frozen=True, slots=True)
class CandidateResult:
    candidate: EdgeCandidateSpec
    classification: str
    passing_horizons: tuple[int, ...]
    discovery: dict[int, HorizonStats]
    challenge: dict[int, HorizonStats]


def _is_contiguous(previous: Candle, current: Candle) -> bool:
    return current.open_time_ms - previous.open_time_ms == FIFTEEN_MINUTES_MS


def _contiguous_streak(bars: list[Candle]) -> tuple[int, ...]:
    if not bars:
        return ()
    result = [1]
    for index in range(1, len(bars)):
        result.append(result[-1] + 1 if _is_contiguous(bars[index - 1], bars[index]) else 1)
    return tuple(result)


def _atr_with_gap_reset(bars: list[Candle], period: int) -> tuple[float | None, ...]:
    if period <= 1:
        raise ValueError("ATR period must be greater than one")
    result: list[float | None] = [None] * len(bars)
    seed: deque[float] = deque()
    current_atr: float | None = None
    for index, bar in enumerate(bars):
        contiguous = index > 0 and _is_contiguous(bars[index - 1], bar)
        if not contiguous:
            seed.clear()
            current_atr = None
            true_range = bar.high - bar.low
        else:
            previous_close = bars[index - 1].close
            true_range = max(
                bar.high - bar.low,
                abs(bar.high - previous_close),
                abs(bar.low - previous_close),
            )

        if current_atr is None:
            seed.append(true_range)
            if len(seed) == period:
                current_atr = mean(seed)
                result[index] = current_atr
            elif len(seed) > period:
                raise RuntimeError("ATR seed exceeded its frozen period")
        else:
            current_atr = ((period - 1) * current_atr + true_range) / period
            result[index] = current_atr
    return tuple(result)


def _rolling_prior_median(
    bars: list[Candle],
    values: list[float | None],
    window: int,
) -> tuple[float | None, ...]:
    queue: deque[float] = deque()
    ordered: list[float] = []
    result: list[float | None] = [None] * len(bars)
    for index, value in enumerate(values):
        if index == 0 or not _is_contiguous(bars[index - 1], bars[index]):
            queue.clear()
            ordered.clear()
        if len(queue) == window:
            result[index] = median(ordered)
        if value is not None:
            queue.append(value)
            insort(ordered, value)
            if len(queue) > window:
                removed = queue.popleft()
                ordered.pop(bisect_left(ordered, removed))
    return tuple(result)


def _rolling_prior_vwap(bars: list[Candle], window: int) -> tuple[float | None, ...]:
    weighted: deque[float] = deque()
    volumes: deque[float] = deque()
    weighted_sum = 0.0
    volume_sum = 0.0
    result: list[float | None] = [None] * len(bars)
    for index, bar in enumerate(bars):
        if index == 0 or not _is_contiguous(bars[index - 1], bar):
            weighted.clear()
            volumes.clear()
            weighted_sum = 0.0
            volume_sum = 0.0
        if len(weighted) == window and volume_sum > 0:
            result[index] = weighted_sum / volume_sum

        typical = (bar.high + bar.low + bar.close) / 3.0
        weighted_value = typical * bar.volume
        weighted.append(weighted_value)
        volumes.append(bar.volume)
        weighted_sum += weighted_value
        volume_sum += bar.volume
        if len(weighted) > window:
            weighted_sum -= weighted.popleft()
            volume_sum -= volumes.popleft()
    return tuple(result)


def prepare_edge_features(candles: list[Candle] | tuple[Candle, ...]) -> EdgeFeatures:
    bars = list(candles)
    if not bars:
        raise ValueError("Edge discovery requires candles")

    streak = _contiguous_streak(bars)
    atr_values = _atr_with_gap_reset(bars, ATR_PERIOD)
    ret_1h: list[float | None] = [None] * len(bars)
    ret_4h: list[float | None] = [None] * len(bars)
    prior_high: list[float | None] = [None] * len(bars)
    prior_low: list[float | None] = [None] * len(bars)

    for index, bar in enumerate(bars):
        if streak[index] >= 5:
            ret_1h[index] = bar.close / bars[index - 4].close - 1.0
        if streak[index] >= 17:
            ret_4h[index] = bar.close / bars[index - 16].close - 1.0
        if streak[index] >= BREAKOUT_LOOKBACK_BARS + 1:
            window = bars[index - BREAKOUT_LOOKBACK_BARS : index]
            prior_high[index] = max(item.high for item in window)
            prior_low[index] = min(item.low for item in window)

    prior_vwap = _rolling_prior_vwap(bars, ROLLING_WINDOW_BARS)
    volume_values = [bar.volume for bar in bars]
    prior_median_volume = _rolling_prior_median(bars, volume_values, ROLLING_WINDOW_BARS)

    atr_pct = [
        value / bar.close if value is not None and bar.close > 0 else None
        for bar, value in zip(bars, atr_values, strict=True)
    ]
    prior_median_atr_pct = _rolling_prior_median(bars, atr_pct, ROLLING_WINDOW_BARS)

    displacement: list[float | None] = [None] * len(bars)
    relative_atr: list[float | None] = [None] * len(bars)
    for index, bar in enumerate(bars):
        atr_value = atr_values[index]
        vwap = prior_vwap[index]
        median_atr_pct = prior_median_atr_pct[index]
        if atr_value is not None and atr_value > 0 and vwap is not None:
            displacement[index] = (bar.close - vwap) / atr_value
        if (
            atr_pct[index] is not None
            and median_atr_pct is not None
            and median_atr_pct > 0
        ):
            relative_atr[index] = atr_pct[index] / median_atr_pct

    return EdgeFeatures(
        bars=tuple(bars),
        contiguous_streak=streak,
        atr=atr_values,
        ret_1h=tuple(ret_1h),
        ret_4h=tuple(ret_4h),
        prior_vwap=prior_vwap,
        prior_median_volume=prior_median_volume,
        vwap_displacement_atr=tuple(displacement),
        prior_high_20=tuple(prior_high),
        prior_low_20=tuple(prior_low),
        relative_atr=tuple(relative_atr),
    )


def _feature_context_ready(features: EdgeFeatures, index: int) -> bool:
    if features.contiguous_streak[index] < ROLLING_WINDOW_BARS + 1:
        return False
    return (
        features.atr[index] is not None
        and features.prior_vwap[index] is not None
        and features.prior_median_volume[index] is not None
    )


def candidate_matches(
    candidate: EdgeCandidateSpec,
    features: EdgeFeatures,
    index: int,
) -> bool:
    if not _feature_context_ready(features, index):
        return False

    bar = features.bars[index]
    median_volume = features.prior_median_volume[index]
    volume_ratio = (
        bar.volume / median_volume
        if median_volume is not None and median_volume > 0
        else None
    )

    if candidate.family in {"return_impulse", "volume_impulse"}:
        if candidate.return_lookback_bars == 4:
            observed_return = features.ret_1h[index]
        elif candidate.return_lookback_bars == 16:
            observed_return = features.ret_4h[index]
        else:
            raise RuntimeError("Frozen impulse candidate has invalid lookback")
        if observed_return is None or candidate.return_threshold is None:
            return False
        directional_match = (
            observed_return >= candidate.return_threshold
            if candidate.direction > 0
            else observed_return <= -candidate.return_threshold
        )
        if not directional_match:
            return False
        if candidate.family == "volume_impulse":
            return (
                volume_ratio is not None
                and candidate.volume_ratio_min is not None
                and volume_ratio >= candidate.volume_ratio_min
            )
        return True

    if candidate.family == "vwap_displacement":
        observed = features.vwap_displacement_atr[index]
        if observed is None or candidate.displacement_atr is None:
            return False
        return (
            observed >= candidate.displacement_atr
            if candidate.direction > 0
            else observed <= -candidate.displacement_atr
        )

    if candidate.family == "compressed_breakout":
        relative_atr = features.relative_atr[index]
        prior_high = features.prior_high_20[index]
        prior_low = features.prior_low_20[index]
        if (
            relative_atr is None
            or candidate.max_relative_atr is None
            or relative_atr > candidate.max_relative_atr
            or volume_ratio is None
            or candidate.volume_ratio_min is None
            or volume_ratio < candidate.volume_ratio_min
            or prior_high is None
            or prior_low is None
        ):
            return False
        return bar.close > prior_high if candidate.direction > 0 else bar.close < prior_low

    raise RuntimeError(f"Unhandled candidate family: {candidate.family}")


def accepted_event_indices(
    candidate: EdgeCandidateSpec,
    features: EdgeFeatures,
    *,
    signal_start_ms: int,
    signal_end_exclusive_ms: int,
) -> tuple[int, ...]:
    accepted: list[int] = []
    last_index: int | None = None
    for index, bar in enumerate(features.bars):
        if not signal_start_ms <= bar.open_time_ms < signal_end_exclusive_ms:
            continue
        if last_index is not None and index - last_index < EVENT_COOLDOWN_BARS:
            continue
        if candidate_matches(candidate, features, index):
            accepted.append(index)
            last_index = index
    return tuple(accepted)


def _outcome_for_event(
    features: EdgeFeatures,
    signal_index: int,
    horizon_bars: int,
    direction: int,
    *,
    window_end_exclusive_ms: int,
) -> EventOutcome | None:
    entry_index = signal_index + 1
    exit_index = signal_index + horizon_bars
    if exit_index >= len(features.bars):
        return None

    signal_bar = features.bars[signal_index]
    entry_bar = features.bars[entry_index]
    exit_bar = features.bars[exit_index]
    if entry_bar.open_time_ms - signal_bar.open_time_ms != FIFTEEN_MINUTES_MS:
        return None
    if (
        exit_bar.open_time_ms - signal_bar.open_time_ms
        != horizon_bars * FIFTEEN_MINUTES_MS
    ):
        return None
    if exit_bar.open_time_ms >= window_end_exclusive_ms:
        return None

    gross = direction * (exit_bar.close / entry_bar.open - 1.0)
    base_cost = BASE_ROUND_TRIP_COST_BPS / 10_000.0
    severe_cost = SEVERE_ROUND_TRIP_COST_BPS / 10_000.0
    return EventOutcome(
        signal_time_ms=signal_bar.open_time_ms,
        horizon_bars=horizon_bars,
        gross_signed_return=gross,
        base_net_signed_return=gross - base_cost,
        severe_net_signed_return=gross - severe_cost,
    )


def collect_candidate_outcomes(
    candidate: EdgeCandidateSpec,
    features: EdgeFeatures,
    *,
    signal_start_ms: int,
    signal_end_exclusive_ms: int,
) -> dict[int, tuple[EventOutcome, ...]]:
    indices = accepted_event_indices(
        candidate,
        features,
        signal_start_ms=signal_start_ms,
        signal_end_exclusive_ms=signal_end_exclusive_ms,
    )
    result: dict[int, tuple[EventOutcome, ...]] = {}
    for horizon in HORIZONS_BARS:
        outcomes = [
            outcome
            for index in indices
            if (
                outcome := _outcome_for_event(
                    features,
                    index,
                    horizon,
                    candidate.direction,
                    window_end_exclusive_ms=signal_end_exclusive_ms,
                )
            )
            is not None
        ]
        result[horizon] = tuple(outcomes)
    return result


def _utc_date(timestamp_ms: int):
    return datetime.fromtimestamp(timestamp_ms / 1000.0, tz=UTC).date()


def _one_sided_daily_mean_p_value(outcomes: tuple[EventOutcome, ...]) -> tuple[int, float]:
    grouped: dict[object, list[float]] = defaultdict(list)
    for outcome in outcomes:
        grouped[_utc_date(outcome.signal_time_ms)].append(outcome.base_net_signed_return)
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


def benjamini_hochberg(p_values: dict[tuple[str, int], float]) -> dict[tuple[str, int], float]:
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


def _year_stats(
    outcomes: tuple[EventOutcome, ...],
    years: tuple[int, ...],
) -> tuple[YearStats, ...]:
    result: list[YearStats] = []
    for year in years:
        selected = [
            item
            for item in outcomes
            if datetime.fromtimestamp(item.signal_time_ms / 1000.0, tz=UTC).year == year
        ]
        result.append(
            YearStats(
                year=year,
                event_count=len(selected),
                mean_base_net=(
                    mean(item.base_net_signed_return for item in selected) if selected else None
                ),
                mean_severe_net=(
                    mean(item.severe_net_signed_return for item in selected) if selected else None
                ),
            )
        )
    return tuple(result)


def summarize_outcomes(
    outcomes: tuple[EventOutcome, ...],
    *,
    q_value: float = 1.0,
    discovery: bool,
    discovery_pass: bool = False,
) -> HorizonStats:
    distinct_days, p_value = _one_sided_daily_mean_p_value(outcomes)
    base_values = [item.base_net_signed_return for item in outcomes]
    severe_values = [item.severe_net_signed_return for item in outcomes]
    gross_values = [item.gross_signed_return for item in outcomes]
    years = _year_stats(outcomes, DISCOVERY_YEARS) if discovery else ()
    return HorizonStats(
        event_count=len(outcomes),
        distinct_days=distinct_days,
        mean_gross_signed_return=mean(gross_values) if gross_values else None,
        mean_base_net_signed_return=mean(base_values) if base_values else None,
        mean_severe_net_signed_return=mean(severe_values) if severe_values else None,
        median_base_net_signed_return=median(base_values) if base_values else None,
        base_net_win_rate=(
            sum(value > 0 for value in base_values) / len(base_values) if base_values else None
        ),
        daily_mean_p_value=p_value,
        fdr_q_value=q_value,
        yearly=years,
        discovery_pass=discovery_pass,
        challenge_pass=False,
    )


def _passes_discovery(stats: HorizonStats) -> bool:
    if stats.event_count < MIN_DISCOVERY_EVENTS or stats.distinct_days < MIN_DISCOVERY_DAYS:
        return False
    if stats.mean_base_net_signed_return is None or stats.mean_base_net_signed_return <= 0:
        return False
    if stats.mean_severe_net_signed_return is None or stats.mean_severe_net_signed_return <= 0:
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
    )


def _replace_gate_flags(
    stats: HorizonStats,
    *,
    discovery_pass: bool | None = None,
    challenge_pass: bool | None = None,
    q_value: float | None = None,
) -> HorizonStats:
    values = asdict(stats)
    values["yearly"] = stats.yearly
    if discovery_pass is not None:
        values["discovery_pass"] = discovery_pass
    if challenge_pass is not None:
        values["challenge_pass"] = challenge_pass
    if q_value is not None:
        values["fdr_q_value"] = q_value
    return HorizonStats(**values)


def evaluate_edge_candidates(
    discovery_features: EdgeFeatures,
    challenge_features: EdgeFeatures,
    *,
    discovery_start_ms: int,
    discovery_end_ms: int,
    challenge_start_ms: int,
    challenge_end_ms: int,
) -> tuple[CandidateResult, ...]:
    raw_discovery: dict[str, dict[int, tuple[EventOutcome, ...]]] = {}
    raw_challenge: dict[str, dict[int, tuple[EventOutcome, ...]]] = {}
    p_values: dict[tuple[str, int], float] = {}
    preliminary: dict[tuple[str, int], HorizonStats] = {}

    for candidate in EDGE_CANDIDATES:
        discovery_outcomes = collect_candidate_outcomes(
            candidate,
            discovery_features,
            signal_start_ms=discovery_start_ms,
            signal_end_exclusive_ms=discovery_end_ms,
        )
        challenge_outcomes = collect_candidate_outcomes(
            candidate,
            challenge_features,
            signal_start_ms=challenge_start_ms,
            signal_end_exclusive_ms=challenge_end_ms,
        )
        raw_discovery[candidate.name] = discovery_outcomes
        raw_challenge[candidate.name] = challenge_outcomes
        for horizon in HORIZONS_BARS:
            stats = summarize_outcomes(discovery_outcomes[horizon], discovery=True)
            preliminary[(candidate.name, horizon)] = stats
            p_values[(candidate.name, horizon)] = stats.daily_mean_p_value

    q_values = benjamini_hochberg(p_values)
    results: list[CandidateResult] = []
    for candidate in EDGE_CANDIDATES:
        discovery_stats: dict[int, HorizonStats] = {}
        challenge_stats: dict[int, HorizonStats] = {}
        passing_horizons: list[int] = []
        for horizon in HORIZONS_BARS:
            key = (candidate.name, horizon)
            with_q = _replace_gate_flags(preliminary[key], q_value=q_values[key])
            discovery_pass = _passes_discovery(with_q)
            finalized_discovery = _replace_gate_flags(
                with_q,
                discovery_pass=discovery_pass,
            )
            challenge = summarize_outcomes(
                raw_challenge[candidate.name][horizon],
                discovery=False,
            )
            challenge_pass = _passes_challenge(challenge, discovery_pass=discovery_pass)
            finalized_challenge = _replace_gate_flags(
                challenge,
                discovery_pass=discovery_pass,
                challenge_pass=challenge_pass,
            )
            discovery_stats[horizon] = finalized_discovery
            challenge_stats[horizon] = finalized_challenge
            if discovery_pass and challenge_pass:
                passing_horizons.append(horizon)

        if passing_horizons:
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
                passing_horizons=tuple(passing_horizons),
                discovery=discovery_stats,
                challenge=challenge_stats,
            )
        )
    return tuple(results)


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
    except FileExistsError as exc:
        raise RuntimeError(
            "M5 report already exists. Preserve the first complete frozen-search result."
        ) from exc


def _load_frozen_data(data_dir: Path) -> tuple[list[Candle], list[Candle]]:
    research_path = data_dir / "btcusdt_15m_research.csv"
    challenge_path = data_dir / "btcusdt_15m_validation.csv"
    if sha256_file(research_path) != EDGE_DISCOVERY_RESEARCH_SHA256:
        raise RuntimeError("M5 discovery data hash mismatch")
    if sha256_file(challenge_path) != EDGE_DISCOVERY_CHALLENGE_SHA256:
        raise RuntimeError("M5 challenge data hash mismatch")

    research_start = parse_utc(DISCOVERY_START)
    research_end = parse_utc(DISCOVERY_END_EXCLUSIVE)
    challenge_start = parse_utc(CHALLENGE_START)
    challenge_end = parse_utc(CHALLENGE_END_EXCLUSIVE)
    assert_not_first_cycle_oos_overlap(
        symbol=FIRST_CYCLE_SYMBOL,
        interval=FIRST_CYCLE_INTERVAL,
        start_ms=research_start,
        end_ms=research_end,
        context="M5 discovery window",
    )
    assert_not_first_cycle_oos_overlap(
        symbol=FIRST_CYCLE_SYMBOL,
        interval=FIRST_CYCLE_INTERVAL,
        start_ms=challenge_start,
        end_ms=challenge_end,
        context="M5 challenge window",
    )

    gaps = allowed_source_gap_ranges(FIRST_CYCLE_SYMBOL, FIRST_CYCLE_INTERVAL)
    close_times = allowed_source_close_times(FIRST_CYCLE_SYMBOL, FIRST_CYCLE_INTERVAL)
    research = validate_interval_window(
        load_csv(research_path),
        FIRST_CYCLE_INTERVAL,
        research_start,
        research_end,
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
    return research, challenge


def run_edge_discovery(
    *,
    data_dir: str | Path = "data/cache/m2",
    report_path: str | Path = "artifacts/m5_edge_discovery_price_volume_v1.json",
) -> dict[str, Any]:
    output = Path(report_path)
    if output.exists():
        raise RuntimeError(
            "M5 report already exists. Preserve the first complete frozen-search result."
        )

    manifest = verify_edge_discovery_freeze()
    provenance = collect_source_provenance(require_clean=True)
    research, challenge = _load_frozen_data(Path(data_dir))

    discovery_features = prepare_edge_features(research)
    combined = [*research, *challenge]
    challenge_features = prepare_edge_features(combined)
    discovery_start = parse_utc(DISCOVERY_START)
    discovery_end = parse_utc(DISCOVERY_END_EXCLUSIVE)
    challenge_start = parse_utc(CHALLENGE_START)
    challenge_end = parse_utc(CHALLENGE_END_EXCLUSIVE)

    results = evaluate_edge_candidates(
        discovery_features,
        challenge_features,
        discovery_start_ms=discovery_start,
        discovery_end_ms=discovery_end,
        challenge_start_ms=challenge_start,
        challenge_end_ms=challenge_end,
    )
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
    decision = "EDGE_CANDIDATES_FOUND" if long_edges or veto_edges else "NO_STABLE_EDGE_FOUND"

    report: dict[str, Any] = {
        "phase": "edge_discovery_development_only",
        "cycle": "m5_edge_discovery_price_volume_v1",
        "decision": decision,
        "policy_freeze": manifest,
        "source_provenance": provenance,
        "data_boundary": {
            "discovery": f"{DISCOVERY_START}/{DISCOVERY_END_EXCLUSIVE}",
            "challenge": f"{CHALLENGE_START}/{CHALLENGE_END_EXCLUSIVE}",
            "oos_2025": "LOCKED_NOT_ACCESSED",
        },
        "search_space": {
            "candidate_count": len(EDGE_CANDIDATES),
            "horizons_bars": list(HORIZONS_BARS),
            "hypothesis_test_count": len(EDGE_CANDIDATES) * len(HORIZONS_BARS),
            "event_cooldown_bars": EVENT_COOLDOWN_BARS,
            "fdr_q_threshold": FDR_Q_THRESHOLD,
        },
        "costs": {
            "base_round_trip_bps": BASE_ROUND_TRIP_COST_BPS,
            "severe_round_trip_bps": SEVERE_ROUND_TRIP_COST_BPS,
        },
        "classification_summary": {
            "long_edge_candidates": long_edges,
            "no_trade_veto_candidates": veto_edges,
            "observation_only_count": sum(
                item.classification == "OBSERVATION_ONLY" for item in results
            ),
        },
        "candidates": [_candidate_payload(item) for item in results],
        "strategy_generation": "FORBIDDEN_REQUIRES_SEPARATE_FROZEN_CONTRACT",
        "ai_module": "excluded",
        "oos_2025": "LOCKED_NOT_ACCESSED",
    }
    safe = _json_safe(report)
    _write_report_once(output, safe)
    return safe


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run frozen M5 BTCUSDT price-volume edge discovery on 2021-2024 only"
    )
    parser.add_argument(
        "--report",
        default="artifacts/m5_edge_discovery_price_volume_v1.json",
    )
    args = parser.parse_args()
    report = run_edge_discovery(report_path=args.report)
    summary = report["classification_summary"]
    print(f"decision={report['decision']}")
    print(f"long_edge_candidates={len(summary['long_edge_candidates'])}")
    print(f"no_trade_veto_candidates={len(summary['no_trade_veto_candidates'])}")
    print(f"observation_only={summary['observation_only_count']}")
    print("oos_2025=LOCKED_NOT_ACCESSED")
    print(f"report={args.report}")


if __name__ == "__main__":
    main()
