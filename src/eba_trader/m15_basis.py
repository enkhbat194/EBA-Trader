from __future__ import annotations

import argparse
import json
import math
from bisect import bisect_right
from collections import defaultdict
from dataclasses import asdict, dataclass, replace
from datetime import UTC, datetime
from pathlib import Path
from statistics import NormalDist, mean, median, stdev
from typing import Any

from .derivatives_audit import (
    DerivativeKline,
    FundingRecord,
    _load_funding_csv,
    _load_kline_csv,
)
from .history import Candle, load_csv, parse_utc
from .m15_basis_policy import (
    BASE_COST_BPS_PER_SIDE,
    CAPITAL_USD,
    CHALLENGE_END_EXCLUSIVE,
    CHALLENGE_START,
    CONFIG_COUNT,
    DISCOVERY_END_EXCLUSIVE,
    ENTRY_BASIS_THRESHOLDS,
    EXIT_BASIS_THRESHOLD,
    FDR_Q_THRESHOLD,
    FUNDING_SHA256,
    FUTURES_SHA256,
    LEG_NOTIONAL_USD,
    MAX_HOLD_BARS,
    MIN_CHALLENGE_PF,
    MIN_CHALLENGE_TRADES,
    MIN_DISCOVERY_DAYS,
    MIN_DISCOVERY_PF,
    MIN_DISCOVERY_TRADES,
    MIN_DISCOVERY_TRADES_PER_YEAR,
    SEVERE_COST_BPS_PER_SIDE,
    SPOT_CHALLENGE_SHA256,
    SPOT_RESEARCH_SHA256,
    sha256_file,
    verify_m15_freeze,
)
from .provenance import collect_source_provenance

STEP_MS = 15 * 60 * 1000
DISCOVERY_START = parse_utc("2021-01-01T00:00:00Z")
DISCOVERY_END = parse_utc(DISCOVERY_END_EXCLUSIVE)
CHALLENGE_START_MS = parse_utc(CHALLENGE_START)
CHALLENGE_END = parse_utc(CHALLENGE_END_EXCLUSIVE)
DISCOVERY_YEARS = (2021, 2022, 2023)


@dataclass(frozen=True, slots=True)
class BasisTrade:
    signal_open_time_ms: int
    entry_time_ms: int
    exit_time_ms: int
    entry_year: int
    entry_basis_threshold: float
    max_hold_bars: int
    signal_basis: float
    exit_basis_signal: float | None
    exit_reason: str
    actual_hold_bars: int
    spot_entry: float
    spot_exit: float
    perp_entry: float
    perp_exit: float
    funding_pnl: float
    spot_pnl: float
    perp_pnl: float
    gross_return_on_capital: float
    base_net_return: float
    severe_net_return: float


@dataclass(frozen=True, slots=True)
class YearStats:
    year: int
    trade_count: int
    mean_base_net: float | None
    mean_severe_net: float | None


@dataclass(frozen=True, slots=True)
class BasisStats:
    trade_count: int
    distinct_entry_days: int
    mean_gross_return: float | None
    mean_base_net: float | None
    mean_severe_net: float | None
    median_base_net: float | None
    profit_factor_base: float | None
    win_rate_base: float | None
    convergence_exit_rate: float | None
    mean_actual_hold_bars: float | None
    daily_mean_p_value: float
    fdr_q_value: float
    yearly: tuple[YearStats, ...]
    discovery_pass: bool
    challenge_pass: bool
    status: str


@dataclass(frozen=True, slots=True)
class BasisConfigResult:
    name: str
    entry_basis_threshold: float
    max_hold_bars: int
    discovery: BasisStats
    challenge: BasisStats | None
    classification: str


def basis_value(spot_close: float, perp_close: float) -> float:
    if spot_close <= 0 or perp_close <= 0:
        raise ValueError("basis requires positive prices")
    return perp_close / spot_close - 1.0


def _entry_year(timestamp_ms: int) -> int:
    return datetime.fromtimestamp(timestamp_ms / 1000.0, tz=UTC).year


def _utc_day(timestamp_ms: int):
    return datetime.fromtimestamp(timestamp_ms / 1000.0, tz=UTC).date()


def _latest_completed_perp_close(
    funding_time_ms: int,
    futures: tuple[DerivativeKline, ...],
    open_times: tuple[int, ...],
) -> float:
    position = bisect_right(open_times, funding_time_ms) - 1
    while position >= 0 and futures[position].close_time_ms > funding_time_ms:
        position -= 1
    if position < 0:
        raise RuntimeError("No completed perpetual bar available for funding mark fallback")
    return futures[position].close


def _funding_mark_price(
    record: FundingRecord,
    futures: tuple[DerivativeKline, ...],
    open_times: tuple[int, ...],
) -> float:
    if record.mark_price is not None and math.isfinite(record.mark_price) and record.mark_price > 0:
        return record.mark_price
    return _latest_completed_perp_close(record.funding_time_ms, futures, open_times)


def _trade_cost(
    *,
    rate_bps: float,
    spot_units: float,
    perp_units: float,
    spot_exit: float,
    perp_exit: float,
) -> float:
    rate = rate_bps / 10_000.0
    entry_notional = 2.0 * LEG_NOTIONAL_USD
    exit_notional = spot_units * spot_exit + perp_units * perp_exit
    return rate * (entry_notional + exit_notional)


def _build_trade(
    *,
    signal_open_time: int,
    entry_basis_threshold: float,
    max_hold_bars: int,
    funding: tuple[FundingRecord, ...],
    funding_times: tuple[int, ...],
    spot_by_time: dict[int, Candle],
    futures_by_time: dict[int, DerivativeKline],
    futures: tuple[DerivativeKline, ...],
    futures_open_times: tuple[int, ...],
    window_start_ms: int,
    window_end_ms: int,
) -> BasisTrade | None:
    signal_spot = spot_by_time.get(signal_open_time)
    signal_perp = futures_by_time.get(signal_open_time)
    if signal_spot is None or signal_perp is None:
        return None
    if signal_spot.close_time_ms >= window_end_ms or signal_perp.close_time_ms >= window_end_ms:
        return None

    signal_basis = basis_value(signal_spot.close, signal_perp.close)
    if signal_basis < entry_basis_threshold:
        return None

    entry_time = signal_open_time + STEP_MS
    time_stop = entry_time + max_hold_bars * STEP_MS
    if entry_time < window_start_ms or time_stop >= window_end_ms:
        return None

    spot_entry_bar = spot_by_time.get(entry_time)
    perp_entry_bar = futures_by_time.get(entry_time)
    if spot_entry_bar is None or perp_entry_bar is None:
        return None

    exit_time = time_stop
    exit_reason = "TIME_STOP"
    exit_basis_signal: float | None = None

    check_time = entry_time
    while check_time < time_stop:
        spot_bar = spot_by_time.get(check_time)
        perp_bar = futures_by_time.get(check_time)
        if spot_bar is not None and perp_bar is not None:
            observed = basis_value(spot_bar.close, perp_bar.close)
            exit_basis_signal = observed
            if observed <= EXIT_BASIS_THRESHOLD:
                exit_time = check_time + STEP_MS
                exit_reason = "CONVERGENCE"
                break
        check_time += STEP_MS

    spot_exit_bar = spot_by_time.get(exit_time)
    perp_exit_bar = futures_by_time.get(exit_time)
    if spot_exit_bar is None or perp_exit_bar is None:
        return None

    spot_entry = spot_entry_bar.open
    spot_exit = spot_exit_bar.open
    perp_entry = perp_entry_bar.open
    perp_exit = perp_exit_bar.open
    if min(spot_entry, spot_exit, perp_entry, perp_exit) <= 0:
        return None

    spot_units = LEG_NOTIONAL_USD / spot_entry
    perp_units = LEG_NOTIONAL_USD / perp_entry
    spot_pnl = spot_units * (spot_exit - spot_entry)
    perp_pnl = perp_units * (perp_entry - perp_exit)

    funding_pnl = 0.0
    funding_index = bisect_right(funding_times, entry_time)
    while funding_index < len(funding):
        record = funding[funding_index]
        if record.funding_time_ms >= exit_time:
            break
        mark = _funding_mark_price(record, futures, futures_open_times)
        funding_pnl += perp_units * mark * record.funding_rate
        funding_index += 1

    gross_pnl = spot_pnl + perp_pnl + funding_pnl
    gross_return = gross_pnl / CAPITAL_USD
    base_cost = _trade_cost(
        rate_bps=BASE_COST_BPS_PER_SIDE,
        spot_units=spot_units,
        perp_units=perp_units,
        spot_exit=spot_exit,
        perp_exit=perp_exit,
    )
    severe_cost = _trade_cost(
        rate_bps=SEVERE_COST_BPS_PER_SIDE,
        spot_units=spot_units,
        perp_units=perp_units,
        spot_exit=spot_exit,
        perp_exit=perp_exit,
    )

    return BasisTrade(
        signal_open_time_ms=signal_open_time,
        entry_time_ms=entry_time,
        exit_time_ms=exit_time,
        entry_year=_entry_year(entry_time),
        entry_basis_threshold=entry_basis_threshold,
        max_hold_bars=max_hold_bars,
        signal_basis=signal_basis,
        exit_basis_signal=exit_basis_signal,
        exit_reason=exit_reason,
        actual_hold_bars=(exit_time - entry_time) // STEP_MS,
        spot_entry=spot_entry,
        spot_exit=spot_exit,
        perp_entry=perp_entry,
        perp_exit=perp_exit,
        funding_pnl=funding_pnl,
        spot_pnl=spot_pnl,
        perp_pnl=perp_pnl,
        gross_return_on_capital=gross_return,
        base_net_return=(gross_pnl - base_cost) / CAPITAL_USD,
        severe_net_return=(gross_pnl - severe_cost) / CAPITAL_USD,
    )


def generate_non_overlapping_trades(
    *,
    entry_basis_threshold: float,
    max_hold_bars: int,
    funding: tuple[FundingRecord, ...],
    spot: tuple[Candle, ...],
    futures: tuple[DerivativeKline, ...],
    window_start_ms: int,
    window_end_ms: int,
) -> tuple[BasisTrade, ...]:
    spot_by_time = {item.open_time_ms: item for item in spot}
    futures_by_time = {item.open_time_ms: item for item in futures}
    futures_open_times = tuple(item.open_time_ms for item in futures)
    funding_times = tuple(item.funding_time_ms for item in funding)
    signal_times = sorted(set(spot_by_time).intersection(futures_by_time))
    result: list[BasisTrade] = []
    next_free_time = window_start_ms

    for signal_time in signal_times:
        if signal_time < window_start_ms:
            continue
        if signal_time >= window_end_ms:
            break
        candidate_entry = signal_time + STEP_MS
        if candidate_entry < next_free_time:
            continue
        spot_bar = spot_by_time[signal_time]
        perp_bar = futures_by_time[signal_time]
        if basis_value(spot_bar.close, perp_bar.close) < entry_basis_threshold:
            continue
        trade = _build_trade(
            signal_open_time=signal_time,
            entry_basis_threshold=entry_basis_threshold,
            max_hold_bars=max_hold_bars,
            funding=funding,
            funding_times=funding_times,
            spot_by_time=spot_by_time,
            futures_by_time=futures_by_time,
            futures=futures,
            futures_open_times=futures_open_times,
            window_start_ms=window_start_ms,
            window_end_ms=window_end_ms,
        )
        if trade is None:
            continue
        result.append(trade)
        next_free_time = trade.exit_time_ms
    return tuple(result)


def _daily_p_value(trades: tuple[BasisTrade, ...]) -> tuple[int, float]:
    grouped: dict[object, list[float]] = defaultdict(list)
    for trade in trades:
        grouped[_utc_day(trade.entry_time_ms)].append(trade.base_net_return)
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


def benjamini_hochberg(p_values: dict[str, float]) -> dict[str, float]:
    ordered = sorted(p_values.items(), key=lambda item: (item[1], item[0]))
    total = len(ordered)
    adjusted: dict[str, float] = {}
    running = 1.0
    for reverse_index in range(total - 1, -1, -1):
        key, p_value = ordered[reverse_index]
        rank = reverse_index + 1
        running = min(running, p_value * total / rank)
        adjusted[key] = min(max(running, 0.0), 1.0)
    return adjusted


def _profit_factor(values: list[float]) -> float | None:
    if not values:
        return None
    positive = sum(value for value in values if value > 0)
    negative = -sum(value for value in values if value < 0)
    if negative == 0:
        return 1_000_000.0 if positive > 0 else None
    return positive / negative


def summarize_trades(
    trades: tuple[BasisTrade, ...],
    *,
    discovery: bool,
    q_value: float = 1.0,
) -> BasisStats:
    distinct_days, p_value = _daily_p_value(trades)
    gross = [item.gross_return_on_capital for item in trades]
    base = [item.base_net_return for item in trades]
    severe = [item.severe_net_return for item in trades]
    years = DISCOVERY_YEARS if discovery else (2024,)
    yearly = tuple(
        YearStats(
            year=year,
            trade_count=len(selected := [item for item in trades if item.entry_year == year]),
            mean_base_net=mean(item.base_net_return for item in selected) if selected else None,
            mean_severe_net=(
                mean(item.severe_net_return for item in selected) if selected else None
            ),
        )
        for year in years
    )
    return BasisStats(
        trade_count=len(trades),
        distinct_entry_days=distinct_days,
        mean_gross_return=mean(gross) if gross else None,
        mean_base_net=mean(base) if base else None,
        mean_severe_net=mean(severe) if severe else None,
        median_base_net=median(base) if base else None,
        profit_factor_base=_profit_factor(base),
        win_rate_base=sum(value > 0 for value in base) / len(base) if base else None,
        convergence_exit_rate=(
            sum(item.exit_reason == "CONVERGENCE" for item in trades) / len(trades)
            if trades
            else None
        ),
        mean_actual_hold_bars=mean(item.actual_hold_bars for item in trades) if trades else None,
        daily_mean_p_value=p_value,
        fdr_q_value=q_value,
        yearly=yearly,
        discovery_pass=False,
        challenge_pass=False,
        status="MEASURED",
    )


def _passes_discovery(stats: BasisStats) -> bool:
    if stats.trade_count < MIN_DISCOVERY_TRADES:
        return False
    if stats.distinct_entry_days < MIN_DISCOVERY_DAYS:
        return False
    if stats.mean_base_net is None or stats.mean_base_net <= 0:
        return False
    if stats.mean_severe_net is None or stats.mean_severe_net <= 0:
        return False
    if stats.median_base_net is None or stats.median_base_net <= 0:
        return False
    if stats.profit_factor_base is None or stats.profit_factor_base <= MIN_DISCOVERY_PF:
        return False
    if stats.fdr_q_value > FDR_Q_THRESHOLD:
        return False
    by_year = {item.year: item for item in stats.yearly}
    for year in DISCOVERY_YEARS:
        item = by_year.get(year)
        if (
            item is None
            or item.trade_count < MIN_DISCOVERY_TRADES_PER_YEAR
            or item.mean_base_net is None
            or item.mean_base_net <= 0
        ):
            return False
    return True


def _passes_challenge(stats: BasisStats) -> bool:
    return (
        stats.trade_count >= MIN_CHALLENGE_TRADES
        and stats.mean_base_net is not None
        and stats.mean_base_net > 0
        and stats.mean_severe_net is not None
        and stats.mean_severe_net > 0
        and stats.median_base_net is not None
        and stats.median_base_net > 0
        and stats.profit_factor_base is not None
        and stats.profit_factor_base > MIN_CHALLENGE_PF
    )


def _config_name(entry_basis_threshold: float, max_hold_bars: int) -> str:
    bps = entry_basis_threshold * 10_000
    return f"basis_{bps:g}bp_hold_{max_hold_bars}"


def evaluate_configs(
    *,
    funding: tuple[FundingRecord, ...],
    spot: tuple[Candle, ...],
    futures: tuple[DerivativeKline, ...],
) -> tuple[BasisConfigResult, ...]:
    preliminary: dict[str, BasisStats] = {}
    metadata: dict[str, tuple[float, int]] = {}
    p_values: dict[str, float] = {}

    for entry_basis_threshold in ENTRY_BASIS_THRESHOLDS:
        for max_hold_bars in MAX_HOLD_BARS:
            name = _config_name(entry_basis_threshold, max_hold_bars)
            trades = generate_non_overlapping_trades(
                entry_basis_threshold=entry_basis_threshold,
                max_hold_bars=max_hold_bars,
                funding=funding,
                spot=spot,
                futures=futures,
                window_start_ms=DISCOVERY_START,
                window_end_ms=DISCOVERY_END,
            )
            stats = summarize_trades(trades, discovery=True)
            preliminary[name] = stats
            metadata[name] = (entry_basis_threshold, max_hold_bars)
            p_values[name] = stats.daily_mean_p_value

    q_values = benjamini_hochberg(p_values)
    results: list[BasisConfigResult] = []
    for name in sorted(metadata):
        entry_basis_threshold, max_hold_bars = metadata[name]
        measured = replace(preliminary[name], fdr_q_value=q_values[name])
        discovery = replace(measured, discovery_pass=_passes_discovery(measured))
        challenge: BasisStats | None = None
        classification = "OBSERVATION_ONLY"
        if discovery.discovery_pass:
            challenge_trades = generate_non_overlapping_trades(
                entry_basis_threshold=entry_basis_threshold,
                max_hold_bars=max_hold_bars,
                funding=funding,
                spot=spot,
                futures=futures,
                window_start_ms=CHALLENGE_START_MS,
                window_end_ms=CHALLENGE_END,
            )
            challenge_measured = summarize_trades(challenge_trades, discovery=False)
            challenge = replace(
                challenge_measured,
                challenge_pass=_passes_challenge(challenge_measured),
            )
            if challenge.challenge_pass:
                classification = "MARKET_NEUTRAL_BASIS_CANDIDATE"
        results.append(
            BasisConfigResult(
                name=name,
                entry_basis_threshold=entry_basis_threshold,
                max_hold_bars=max_hold_bars,
                discovery=discovery,
                challenge=challenge,
                classification=classification,
            )
        )
    if len(results) != CONFIG_COUNT:
        raise RuntimeError("M15 evaluated config count changed after freeze")
    return tuple(results)


def _verify_inputs(
    research_path: Path,
    challenge_path: Path,
    futures_path: Path,
    funding_path: Path,
) -> dict[str, str]:
    expected = {
        "spot_research": (research_path, SPOT_RESEARCH_SHA256),
        "spot_challenge": (challenge_path, SPOT_CHALLENGE_SHA256),
        "futures": (futures_path, FUTURES_SHA256),
        "funding": (funding_path, FUNDING_SHA256),
    }
    actual: dict[str, str] = {}
    for name, (path, frozen_hash) in expected.items():
        if not path.is_file():
            raise FileNotFoundError(f"M15 frozen input missing: {path}")
        digest = sha256_file(path)
        if digest != frozen_hash:
            raise RuntimeError(f"M15 frozen input hash mismatch for {name}: {digest}")
        actual[name] = digest
    return actual


def run_m15_basis(
    *,
    research_path: str | Path = "data/cache/m2/btcusdt_15m_research.csv",
    challenge_path: str | Path = "data/cache/m2/btcusdt_15m_validation.csv",
    futures_path: str | Path = "data/cache/m6/btcusdt_usdm_perpetual_15m_2021_2024.csv",
    funding_path: str | Path = "data/cache/m6/btcusdt_usdm_funding_2021_2024.csv",
    report_path: str | Path = "artifacts/m15_market_neutral_basis_convergence.json",
) -> dict[str, Any]:
    output = Path(report_path)
    if output.exists():
        raise RuntimeError("M15 evidence already exists; preserve first complete result")

    freeze = verify_m15_freeze()
    provenance = collect_source_provenance(require_clean=True)
    research_file = Path(research_path)
    challenge_file = Path(challenge_path)
    futures_file = Path(futures_path)
    funding_file = Path(funding_path)
    hashes = _verify_inputs(research_file, challenge_file, futures_file, funding_file)

    research = tuple(load_csv(research_file))
    challenge = tuple(load_csv(challenge_file))
    spot = tuple(sorted((*research, *challenge), key=lambda item: item.open_time_ms))
    futures = tuple(_load_kline_csv(futures_file))
    funding = tuple(_load_funding_csv(funding_file))

    if max(item.open_time_ms for item in spot) >= CHALLENGE_END:
        raise RuntimeError("M15 must not access 2025 Spot OOS")
    if max(item.open_time_ms for item in futures) >= CHALLENGE_END:
        raise RuntimeError("M15 must not access 2025 futures OOS")
    if max(item.funding_time_ms for item in funding) >= CHALLENGE_END:
        raise RuntimeError("M15 must not access 2025 funding OOS")

    results = evaluate_configs(funding=funding, spot=spot, futures=futures)
    candidates = [
        item.name
        for item in results
        if item.classification == "MARKET_NEUTRAL_BASIS_CANDIDATE"
    ]
    decision = (
        "MARKET_NEUTRAL_BASIS_CANDIDATE_FOUND"
        if candidates
        else "NO_STABLE_BASIS_CONVERGENCE_EDGE_FOUND"
    )

    report: dict[str, Any] = {
        "phase": "m15_market_neutral_basis_convergence_first_complete_frozen_evidence",
        "decision": decision,
        "policy_freeze": freeze,
        "source_provenance": provenance,
        "input_sha256": hashes,
        "search": {
            "configuration_count": len(results),
            "market_neutral_basis_candidates": candidates,
            "discovery_passing_configs": sum(item.discovery.discovery_pass for item in results),
            "challenge_passing_configs": sum(
                bool(item.challenge and item.challenge.challenge_pass) for item in results
            ),
            "results": [asdict(item) for item in results],
        },
        "oos_2025": "LOCKED_NOT_ACCESSED",
        "leverage": "FORBIDDEN",
        "naked_short": "FORBIDDEN",
        "risk_sizing": "BLOCKED_RESEARCH_ONLY",
        "live_execution": "BLOCKED_RESEARCH_ONLY",
        "parameter_changes_after_result": "FORBIDDEN",
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(report, indent=2, sort_keys=True, allow_nan=False),
        encoding="utf-8",
    )
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description="Run frozen M15 market-neutral basis convergence")
    parser.add_argument("--report", default="artifacts/m15_market_neutral_basis_convergence.json")
    args = parser.parse_args()
    report = run_m15_basis(report_path=args.report)
    print("M15 decision:", report["decision"])
    print(
        "MARKET_NEUTRAL_BASIS_CANDIDATE:",
        report["search"]["market_neutral_basis_candidates"],
    )
    print("discovery_passing_configs:", report["search"]["discovery_passing_configs"])
    print("challenge_passing_configs:", report["search"]["challenge_passing_configs"])
    print("2025 OOS remains", report["oos_2025"])


if __name__ == "__main__":
    main()
