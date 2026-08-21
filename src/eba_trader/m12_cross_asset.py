from __future__ import annotations

import argparse
import csv
import json
import math
from collections import defaultdict, deque
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from statistics import NormalDist, mean, median, stdev
from typing import Any

from .data_policy import allowed_source_close_times, allowed_source_gap_ranges
from .derivatives_audit import DerivativeKline
from .history import Candle, load_csv, parse_utc, validate_interval_window
from .holdout_guard import assert_not_first_cycle_oos_overlap
from .m12_cross_asset_policy import (
    BASE_ROUND_TRIP_COST_BPS,
    BASELINE_UPLIFT,
    CHALLENGE_END_EXCLUSIVE,
    CHALLENGE_START,
    DISCOVERY_END_EXCLUSIVE,
    DISCOVERY_START,
    ETH_SHA256,
    EVENT_COOLDOWN_BARS,
    FDR_Q_THRESHOLD,
    FLOW_BASELINE_WINDOWS,
    HORIZONS_BARS,
    M12_CANDIDATES,
    MIN_CHALLENGE_EVENTS,
    MIN_DISCOVERY_DAYS,
    MIN_DISCOVERY_EVENTS,
    MIN_DISCOVERY_EVENTS_PER_YEAR,
    SEVERE_ROUND_TRIP_COST_BPS,
    SPOT_CHALLENGE_SHA256,
    SPOT_RESEARCH_SHA256,
    M12CandidateSpec,
    sha256_file,
    verify_m12_freeze,
)
from .provenance import collect_source_provenance
from .study_policy import FIRST_CYCLE_INTERVAL, FIRST_CYCLE_SYMBOL

STEP_MS = 15 * 60 * 1000
DISCOVERY_YEARS = (2021, 2022, 2023)


@dataclass(frozen=True, slots=True)
class EthFeatures:
    bars: tuple[DerivativeKline, ...]
    index_by_time: dict[int, int]
    ret_1h: tuple[float | None, ...]
    ret_4h: tuple[float | None, ...]
    taker_buy_share_1h: tuple[float | None, ...]
    quote_volume_intensity_1h: tuple[float | None, ...]


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
    candidate: M12CandidateSpec
    classification: str
    passing_horizons: tuple[int, ...]
    discovery: dict[int, HorizonStats]
    challenge: dict[int, HorizonStats]


def _is_eth_contiguous(bars: tuple[DerivativeKline, ...], start: int, end: int) -> bool:
    if start < 0 or end >= len(bars) or start > end:
        return False
    return bars[end].open_time_ms - bars[start].open_time_ms == (end - start) * STEP_MS


def _is_btc_contiguous(bars: tuple[Candle, ...], start: int, end: int) -> bool:
    if start < 0 or end >= len(bars) or start > end:
        return False
    return bars[end].open_time_ms - bars[start].open_time_ms == (end - start) * STEP_MS


def load_eth_normalized(path: str | Path) -> tuple[DerivativeKline, ...]:
    rows: list[DerivativeKline] = []
    with Path(path).open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            rows.append(
                DerivativeKline(
                    open_time_ms=int(row["open_time_ms"]),
                    open=float(row["open"]),
                    high=float(row["high"]),
                    low=float(row["low"]),
                    close=float(row["close"]),
                    close_time_ms=int(row["close_time_ms"]),
                    volume=float(row["volume"]),
                    quote_volume=float(row["quote_volume"]),
                    trade_count=int(row["trade_count"]),
                    taker_buy_base_volume=float(row["taker_buy_base_volume"]),
                    taker_buy_quote_volume=float(row["taker_buy_quote_volume"]),
                )
            )
    if not rows:
        raise ValueError("M12 ETH input is empty")
    previous = rows[0].open_time_ms - STEP_MS
    for row in rows:
        if row.open_time_ms - previous != STEP_MS:
            raise RuntimeError("M12 ETH normalized input contains a 15m gap")
        if row.close_time_ms != row.open_time_ms + STEP_MS - 1:
            raise RuntimeError("M12 ETH normalized input violates close-time semantics")
        if min(row.open, row.high, row.low, row.close) <= 0:
            raise RuntimeError("M12 ETH normalized input contains non-positive OHLC")
        if (
            row.volume is None
            or row.quote_volume is None
            or row.trade_count is None
            or row.taker_buy_base_volume is None
            or row.taker_buy_quote_volume is None
        ):
            raise RuntimeError("M12 ETH normalized input is missing activity fields")
        previous = row.open_time_ms
    return tuple(rows)


def _rolling_quote_totals(
    bars: tuple[DerivativeKline, ...],
) -> tuple[float | None, ...]:
    result: list[float | None] = [None] * len(bars)
    for index in range(3, len(bars)):
        if not _is_eth_contiguous(bars, index - 3, index):
            continue
        selected = bars[index - 3 : index + 1]
        if any(item.quote_volume is None for item in selected):
            continue
        result[index] = sum(float(item.quote_volume) for item in selected)
    return tuple(result)


def _prior_median_rolling(
    bars: tuple[DerivativeKline, ...],
    values: tuple[float | None, ...],
    window: int,
) -> tuple[float | None, ...]:
    queue: deque[float] = deque()
    result: list[float | None] = [None] * len(bars)
    previous_time: int | None = None
    for index, value in enumerate(values):
        current_time = bars[index].open_time_ms
        if previous_time is None or current_time - previous_time != STEP_MS:
            queue.clear()
        if len(queue) == window:
            result[index] = median(queue)
        if value is not None:
            queue.append(value)
            if len(queue) > window:
                queue.popleft()
        previous_time = current_time
    return tuple(result)


def prepare_eth_features(
    rows: list[DerivativeKline] | tuple[DerivativeKline, ...],
) -> EthFeatures:
    bars = tuple(rows)
    if not bars:
        raise ValueError("M12 ETH features require rows")
    ret_1h: list[float | None] = [None] * len(bars)
    ret_4h: list[float | None] = [None] * len(bars)
    taker_share: list[float | None] = [None] * len(bars)
    quote_totals = _rolling_quote_totals(bars)
    prior_quote_median = _prior_median_rolling(bars, quote_totals, FLOW_BASELINE_WINDOWS)
    quote_intensity: list[float | None] = [None] * len(bars)

    for index, bar in enumerate(bars):
        if index >= 4 and _is_eth_contiguous(bars, index - 4, index):
            ret_1h[index] = bar.close / bars[index - 4].close - 1.0
        if index >= 16 and _is_eth_contiguous(bars, index - 16, index):
            ret_4h[index] = bar.close / bars[index - 16].close - 1.0
        if index >= 3 and _is_eth_contiguous(bars, index - 3, index):
            selected = bars[index - 3 : index + 1]
            if all(
                item.volume is not None and item.taker_buy_base_volume is not None
                for item in selected
            ):
                total_volume = sum(float(item.volume) for item in selected)
                total_taker = sum(float(item.taker_buy_base_volume) for item in selected)
                if total_volume > 0:
                    taker_share[index] = total_taker / total_volume
        current_quote = quote_totals[index]
        prior_median = prior_quote_median[index]
        if current_quote is not None and prior_median is not None and prior_median > 0:
            quote_intensity[index] = current_quote / prior_median

    return EthFeatures(
        bars=bars,
        index_by_time={bar.open_time_ms: index for index, bar in enumerate(bars)},
        ret_1h=tuple(ret_1h),
        ret_4h=tuple(ret_4h),
        taker_buy_share_1h=tuple(taker_share),
        quote_volume_intensity_1h=tuple(quote_intensity),
    )


def _directional_threshold(value: float, threshold: float, direction: int) -> bool:
    return value >= threshold if direction > 0 else value <= -threshold


def candidate_matches(
    candidate: M12CandidateSpec,
    eth: EthFeatures,
    eth_index: int,
    btc: tuple[Candle, ...],
    btc_index: int,
) -> bool:
    if candidate.family == "impulse":
        observed = (
            eth.ret_1h[eth_index]
            if candidate.return_window_bars == 4
            else eth.ret_4h[eth_index]
        )
        return (
            observed is not None
            and candidate.return_threshold is not None
            and _directional_threshold(observed, candidate.return_threshold, candidate.direction)
        )

    if candidate.family == "relative":
        eth_return = eth.ret_1h[eth_index]
        if (
            eth_return is None
            or candidate.relative_threshold is None
            or btc_index < 4
            or not _is_btc_contiguous(btc, btc_index - 4, btc_index)
        ):
            return False
        btc_return = btc[btc_index].close / btc[btc_index - 4].close - 1.0
        relative = eth_return - btc_return
        return _directional_threshold(relative, candidate.relative_threshold, candidate.direction)

    if candidate.family == "flow_impulse":
        eth_return = eth.ret_1h[eth_index]
        share = eth.taker_buy_share_1h[eth_index]
        intensity = eth.quote_volume_intensity_1h[eth_index]
        if (
            eth_return is None
            or share is None
            or intensity is None
            or candidate.return_threshold is None
            or candidate.quote_intensity_min is None
            or intensity < candidate.quote_intensity_min
            or not _directional_threshold(
                eth_return,
                candidate.return_threshold,
                candidate.direction,
            )
        ):
            return False
        if candidate.taker_share_min is not None and share < candidate.taker_share_min:
            return False
        return not (
            candidate.taker_share_max is not None and share > candidate.taker_share_max
        )

    raise RuntimeError(f"Unhandled M12 candidate family: {candidate.family}")


def accepted_signal_indices(
    candidate: M12CandidateSpec,
    eth: EthFeatures,
    btc: tuple[Candle, ...],
    *,
    signal_start_ms: int,
    signal_end_exclusive_ms: int,
) -> tuple[int, ...]:
    accepted: list[int] = []
    last_index: int | None = None
    for btc_index, bar in enumerate(btc):
        if not signal_start_ms <= bar.open_time_ms < signal_end_exclusive_ms:
            continue
        if last_index is not None and btc_index - last_index < EVENT_COOLDOWN_BARS:
            continue
        eth_index = eth.index_by_time.get(bar.open_time_ms)
        if eth_index is None:
            continue
        if candidate_matches(candidate, eth, eth_index, btc, btc_index):
            accepted.append(btc_index)
            last_index = btc_index
    return tuple(accepted)


def _outcome_for_signal(
    btc: tuple[Candle, ...],
    signal_index: int,
    horizon_bars: int,
    direction: int,
    *,
    window_end_exclusive_ms: int,
) -> EventOutcome | None:
    entry_index = signal_index + 1
    exit_index = signal_index + horizon_bars
    if exit_index >= len(btc):
        return None
    if not _is_btc_contiguous(btc, signal_index, exit_index):
        return None
    signal = btc[signal_index]
    entry = btc[entry_index]
    exit_bar = btc[exit_index]
    if exit_bar.open_time_ms >= window_end_exclusive_ms:
        return None
    gross = direction * (exit_bar.close / entry.open - 1.0)
    return EventOutcome(
        signal_time_ms=signal.open_time_ms,
        horizon_bars=horizon_bars,
        gross_signed_return=gross,
        base_net_signed_return=gross - BASE_ROUND_TRIP_COST_BPS / 10_000.0,
        severe_net_signed_return=gross - SEVERE_ROUND_TRIP_COST_BPS / 10_000.0,
    )


def collect_candidate_outcomes(
    candidate: M12CandidateSpec,
    eth: EthFeatures,
    btc: tuple[Candle, ...],
    *,
    signal_start_ms: int,
    signal_end_exclusive_ms: int,
) -> dict[int, tuple[EventOutcome, ...]]:
    indices = accepted_signal_indices(
        candidate,
        eth,
        btc,
        signal_start_ms=signal_start_ms,
        signal_end_exclusive_ms=signal_end_exclusive_ms,
    )
    result: dict[int, tuple[EventOutcome, ...]] = {}
    for horizon in HORIZONS_BARS:
        outcomes = [
            outcome
            for index in indices
            if (
                outcome := _outcome_for_signal(
                    btc,
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


def unconditional_baseline(
    btc: tuple[Candle, ...],
    *,
    signal_start_ms: int,
    signal_end_exclusive_ms: int,
    horizon_bars: int,
    direction: int,
) -> tuple[EventOutcome, ...]:
    outcomes: list[EventOutcome] = []
    for index, bar in enumerate(btc):
        if not signal_start_ms <= bar.open_time_ms < signal_end_exclusive_ms:
            continue
        outcome = _outcome_for_signal(
            btc,
            index,
            horizon_bars,
            direction,
            window_end_exclusive_ms=signal_end_exclusive_ms,
        )
        if outcome is not None:
            outcomes.append(outcome)
    return tuple(outcomes)


def _utc_date(timestamp_ms: int):
    return datetime.fromtimestamp(timestamp_ms / 1000.0, tz=UTC).date()


def _utc_year(timestamp_ms: int) -> int:
    return datetime.fromtimestamp(timestamp_ms / 1000.0, tz=UTC).year


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
) -> tuple[YearStats, ...]:
    result: list[YearStats] = []
    for year in DISCOVERY_YEARS:
        selected = tuple(item for item in outcomes if _utc_year(item.signal_time_ms) == year)
        base_selected = tuple(item for item in baseline if _utc_year(item.signal_time_ms) == year)
        event_mean = _mean_base(selected)
        baseline_mean = _mean_base(base_selected)
        uplift = (
            event_mean - baseline_mean
            if event_mean is not None and baseline_mean is not None
            else None
        )
        result.append(
            YearStats(
                year=year,
                event_count=len(selected),
                mean_base_net=event_mean,
                mean_severe_net=(
                    mean(item.severe_net_signed_return for item in selected)
                    if selected
                    else None
                ),
                baseline_mean_base_net=baseline_mean,
                baseline_uplift=uplift,
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
    event_mean = mean(base) if base else None
    baseline_mean = _mean_base(baseline)
    uplift = (
        event_mean - baseline_mean
        if event_mean is not None and baseline_mean is not None
        else None
    )
    return HorizonStats(
        event_count=len(outcomes),
        distinct_days=distinct_days,
        mean_gross_signed_return=mean(gross) if gross else None,
        mean_base_net_signed_return=event_mean,
        mean_severe_net_signed_return=mean(severe) if severe else None,
        median_base_net_signed_return=median(base) if base else None,
        base_net_win_rate=(sum(value > 0 for value in base) / len(base) if base else None),
        baseline_mean_base_net=baseline_mean,
        baseline_uplift=uplift,
        daily_mean_p_value=p_value,
        fdr_q_value=q_value,
        yearly=_year_stats(outcomes, baseline) if discovery else (),
        discovery_pass=discovery_pass,
        challenge_pass=challenge_pass,
    )


def _passes_discovery(stats: HorizonStats) -> bool:
    if stats.event_count < MIN_DISCOVERY_EVENTS or stats.distinct_days < MIN_DISCOVERY_DAYS:
        return False
    if (
        stats.mean_base_net_signed_return is None
        or stats.mean_base_net_signed_return <= 0
        or stats.mean_severe_net_signed_return is None
        or stats.mean_severe_net_signed_return <= 0
        or stats.median_base_net_signed_return is None
        or stats.median_base_net_signed_return <= 0
        or stats.baseline_uplift is None
        or stats.baseline_uplift < BASELINE_UPLIFT
        or stats.fdr_q_value > FDR_Q_THRESHOLD
    ):
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
            or item.baseline_uplift < 0
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
    values = asdict(stats)
    values["yearly"] = stats.yearly
    if q_value is not None:
        values["fdr_q_value"] = q_value
    if discovery_pass is not None:
        values["discovery_pass"] = discovery_pass
    if challenge_pass is not None:
        values["challenge_pass"] = challenge_pass
    return HorizonStats(**values)


def evaluate_candidates(
    eth: EthFeatures,
    discovery_btc: tuple[Candle, ...],
    challenge_btc: tuple[Candle, ...],
) -> tuple[CandidateResult, ...]:
    discovery_start = parse_utc(DISCOVERY_START)
    discovery_end = parse_utc(DISCOVERY_END_EXCLUSIVE)
    challenge_start = parse_utc(CHALLENGE_START)
    challenge_end = parse_utc(CHALLENGE_END_EXCLUSIVE)

    discovery_raw: dict[str, dict[int, tuple[EventOutcome, ...]]] = {}
    challenge_raw: dict[str, dict[int, tuple[EventOutcome, ...]]] = {}
    preliminary: dict[tuple[str, int], HorizonStats] = {}
    p_values: dict[tuple[str, int], float] = {}
    baseline_cache: dict[tuple[str, int, int], tuple[EventOutcome, ...]] = {}

    def baseline(
        window: str,
        direction: int,
        horizon: int,
    ) -> tuple[EventOutcome, ...]:
        key = (window, direction, horizon)
        if key not in baseline_cache:
            bars = discovery_btc if window == "discovery" else challenge_btc
            start = discovery_start if window == "discovery" else challenge_start
            end = discovery_end if window == "discovery" else challenge_end
            baseline_cache[key] = unconditional_baseline(
                bars,
                signal_start_ms=start,
                signal_end_exclusive_ms=end,
                horizon_bars=horizon,
                direction=direction,
            )
        return baseline_cache[key]

    for candidate in M12_CANDIDATES:
        d_outcomes = collect_candidate_outcomes(
            candidate,
            eth,
            discovery_btc,
            signal_start_ms=discovery_start,
            signal_end_exclusive_ms=discovery_end,
        )
        c_outcomes = collect_candidate_outcomes(
            candidate,
            eth,
            challenge_btc,
            signal_start_ms=challenge_start,
            signal_end_exclusive_ms=challenge_end,
        )
        discovery_raw[candidate.name] = d_outcomes
        challenge_raw[candidate.name] = c_outcomes
        for horizon in HORIZONS_BARS:
            stats = summarize_outcomes(
                d_outcomes[horizon],
                baseline("discovery", candidate.direction, horizon),
                discovery=True,
            )
            preliminary[(candidate.name, horizon)] = stats
            p_values[(candidate.name, horizon)] = stats.daily_mean_p_value

    q_values = benjamini_hochberg(p_values)
    results: list[CandidateResult] = []
    for candidate in M12_CANDIDATES:
        discovery_stats: dict[int, HorizonStats] = {}
        challenge_stats: dict[int, HorizonStats] = {}
        passing: list[int] = []
        for horizon in HORIZONS_BARS:
            key = (candidate.name, horizon)
            with_q = _with_flags(preliminary[key], q_value=q_values[key])
            discovery_pass = _passes_discovery(with_q)
            final_discovery = _with_flags(with_q, discovery_pass=discovery_pass)
            raw_challenge = summarize_outcomes(
                challenge_raw[candidate.name][horizon],
                baseline("challenge", candidate.direction, horizon),
                discovery=False,
            )
            challenge_pass = _passes_challenge(
                raw_challenge,
                discovery_pass=discovery_pass,
            )
            final_challenge = _with_flags(
                raw_challenge,
                discovery_pass=discovery_pass,
                challenge_pass=challenge_pass,
            )
            discovery_stats[horizon] = final_discovery
            challenge_stats[horizon] = final_challenge
            if discovery_pass and challenge_pass:
                passing.append(horizon)

        classification = "OBSERVATION_ONLY"
        if passing:
            classification = (
                "LONG_EDGE_CANDIDATE"
                if candidate.direction > 0
                else "NO_TRADE_VETO_CANDIDATE"
            )
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


def _validate_btc_file(
    path: Path,
    expected_sha: str,
    start: str,
    end: str,
) -> tuple[Candle, ...]:
    if sha256_file(path) != expected_sha:
        raise RuntimeError(f"M12 BTC input hash mismatch: {path}")
    start_ms = parse_utc(start)
    end_ms = parse_utc(end)
    assert_not_first_cycle_oos_overlap(
        symbol=FIRST_CYCLE_SYMBOL,
        interval=FIRST_CYCLE_INTERVAL,
        start_ms=start_ms,
        end_ms=end_ms,
        context="M12 BTC Spot outcome input",
    )
    rows = load_csv(path)
    validated = validate_interval_window(
        rows,
        FIRST_CYCLE_INTERVAL,
        start_ms,
        end_ms,
        allowed_missing_ranges=allowed_source_gap_ranges(
            FIRST_CYCLE_SYMBOL,
            FIRST_CYCLE_INTERVAL,
        ),
        allowed_close_times=allowed_source_close_times(
            FIRST_CYCLE_SYMBOL,
            FIRST_CYCLE_INTERVAL,
        ),
    )
    return tuple(validated)


def _validate_eth_file(path: Path) -> EthFeatures:
    if sha256_file(path) != ETH_SHA256:
        raise RuntimeError("M12 ETH input hash mismatch")
    rows = load_eth_normalized(path)
    if rows[0].open_time_ms != parse_utc(DISCOVERY_START):
        raise RuntimeError("M12 ETH input does not start at 2021-01-01")
    if rows[-1].open_time_ms != parse_utc(CHALLENGE_END_EXCLUSIVE) - STEP_MS:
        raise RuntimeError("M12 ETH input does not end at 2024-12-31 23:45")
    expected = (
        parse_utc(CHALLENGE_END_EXCLUSIVE) - parse_utc(DISCOVERY_START)
    ) // STEP_MS
    if len(rows) != expected:
        raise RuntimeError("M12 ETH input row count does not match full 2021-2024 window")
    return prepare_eth_features(rows)


def _write_report_once(path: Path, report: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with path.open("x", encoding="utf-8") as handle:
            json.dump(report, handle, indent=2, sort_keys=True, allow_nan=False)
            handle.write("\n")
    except FileExistsError as error:
        raise RuntimeError(
            "M12 report already exists; preserve the first complete result"
        ) from error


def run_m12_cross_asset_edge(
    *,
    eth_path: str | Path = "data/cache/m12/m11_ethusdt_usdm_15m_normalized.csv",
    spot_research_path: str | Path = "data/cache/m2/btcusdt_15m_research.csv",
    spot_challenge_path: str | Path = "data/cache/m2/btcusdt_15m_validation.csv",
    report_path: str | Path = "artifacts/m12_cross_asset_eth_btc_edge.json",
) -> dict[str, Any]:
    output = Path(report_path)
    if output.exists():
        raise RuntimeError("M12 report already exists; preserve the first complete result")

    freeze = verify_m12_freeze()
    provenance = collect_source_provenance(require_clean=True)
    eth_file = Path(eth_path)
    research_file = Path(spot_research_path)
    challenge_file = Path(spot_challenge_path)
    if not eth_file.is_file() or not research_file.is_file() or not challenge_file.is_file():
        raise FileNotFoundError("M12 requires frozen ETH and BTC cache inputs")

    eth = _validate_eth_file(eth_file)
    discovery_btc = _validate_btc_file(
        research_file,
        SPOT_RESEARCH_SHA256,
        DISCOVERY_START,
        DISCOVERY_END_EXCLUSIVE,
    )
    challenge_btc = _validate_btc_file(
        challenge_file,
        SPOT_CHALLENGE_SHA256,
        CHALLENGE_START,
        CHALLENGE_END_EXCLUSIVE,
    )
    results = evaluate_candidates(eth, discovery_btc, challenge_btc)

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
    discovery_passes = sum(
        stats.discovery_pass for item in results for stats in item.discovery.values()
    )
    challenge_passes = sum(
        stats.challenge_pass for item in results for stats in item.challenge.values()
    )
    decision = (
        "CROSS_ASSET_EDGE_CANDIDATE_FOUND_REQUIRES_NEW_STRATEGY_FREEZE"
        if long_edges or veto_edges
        else "NO_STABLE_CROSS_ASSET_EDGE_FOUND"
    )

    report: dict[str, Any] = {
        "phase": "m12_cross_asset_eth_btc_edge_discovery",
        "decision": decision,
        "policy_freeze": freeze,
        "source_provenance": provenance,
        "data_boundary": {
            "discovery": f"{DISCOVERY_START}/{DISCOVERY_END_EXCLUSIVE}",
            "challenge": f"{CHALLENGE_START}/{CHALLENGE_END_EXCLUSIVE}",
            "challenge_is_pristine_oos": False,
            "oos_2025": "LOCKED_NOT_ACCESSED",
        },
        "input_sha256": {
            "ethusdt_usdm_15m_2021_2024": sha256_file(eth_file),
            "btcusdt_spot_research_2021_2023": sha256_file(research_file),
            "btcusdt_spot_challenge_2024": sha256_file(challenge_file),
        },
        "search": {
            "candidate_count": len(M12_CANDIDATES),
            "horizons_bars": list(HORIZONS_BARS),
            "hypothesis_test_count": len(M12_CANDIDATES) * len(HORIZONS_BARS),
            "discovery_passing_horizons": discovery_passes,
            "challenge_passing_horizons": challenge_passes,
            "long_edge_candidates": long_edges,
            "no_trade_veto_candidates": veto_edges,
        },
        "results": [asdict(item) for item in results],
        "strategy_generation": "FORBIDDEN",
        "risk_sizing": "FORBIDDEN",
        "ai_module": "EXCLUDED",
        "short_execution": "NOT_AUTHORIZED",
        "live_execution": "FORBIDDEN",
        "oos_2025": "LOCKED_NOT_ACCESSED",
    }
    _write_report_once(output, report)
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description="Run frozen M12 ETH→BTC cross-asset edge study")
    parser.add_argument(
        "--eth",
        default="data/cache/m12/m11_ethusdt_usdm_15m_normalized.csv",
    )
    parser.add_argument(
        "--spot-research",
        default="data/cache/m2/btcusdt_15m_research.csv",
    )
    parser.add_argument(
        "--spot-challenge",
        default="data/cache/m2/btcusdt_15m_validation.csv",
    )
    parser.add_argument(
        "--out",
        default="artifacts/m12_cross_asset_eth_btc_edge.json",
    )
    args = parser.parse_args()
    report = run_m12_cross_asset_edge(
        eth_path=args.eth,
        spot_research_path=args.spot_research,
        spot_challenge_path=args.spot_challenge,
        report_path=args.out,
    )
    print("M12 decision:", report["decision"])
    print("LONG_EDGE_CANDIDATE:", report["search"]["long_edge_candidates"])
    print("NO_TRADE_VETO_CANDIDATE:", report["search"]["no_trade_veto_candidates"])
    print("discovery_passing_horizons:", report["search"]["discovery_passing_horizons"])
    print("challenge_passing_horizons:", report["search"]["challenge_passing_horizons"])
    print("2025 OOS remains LOCKED_NOT_ACCESSED")


if __name__ == "__main__":
    main()
