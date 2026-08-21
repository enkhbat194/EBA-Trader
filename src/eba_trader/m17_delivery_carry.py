from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass, replace
from pathlib import Path
from statistics import mean, median
from typing import Any

from .derivatives_archive_seed import _download_verified_archive, parse_kline_archive
from .derivatives_audit import DerivativeKline
from .history import Candle, load_csv
from .m16_delivery_audit import (
    ArchiveFileAudit,
    _window_months,
    archive_url,
    audit_contract_rows,
)
from .m16_delivery_policy import DeliveryContract, delivery_contracts
from .m17_delivery_carry_policy import (
    BASE_COST_BPS_PER_SIDE,
    CHALLENGE_CONTRACT_COUNT,
    CONFIG_COUNT,
    DISCOVERY_CONTRACT_COUNT,
    ENTRY_OFFSETS_DAYS,
    EXIT_MINUTES_BEFORE_DELIVERY,
    FDR_Q_THRESHOLD,
    MIN_BASE_PF,
    MIN_BASE_WIN_RATE,
    MIN_CHALLENGE_SEVERE_WINS,
    MIN_MARGIN_REMAINING_RATIO,
    MIN_SEVERE_PF,
    SEVERE_COST_BPS_PER_SIDE,
    SPOT_CHALLENGE_SHA256,
    SPOT_ENTRY_NOTIONAL_USD,
    SPOT_RESEARCH_SHA256,
    USDM_NORMALIZED_SHA256,
    sha256_file,
    verify_m17_freeze,
)
from .provenance import collect_source_provenance

DAY_MS = 24 * 60 * 60 * 1000
MINUTE_MS = 60 * 1000
OOS_2025_START_MS = 1_735_689_600_000


@dataclass(frozen=True, slots=True)
class DeliveryCarryTrade:
    symbol: str
    year: int
    entry_offset_days: int
    entry_time_ms: int
    exit_time_ms: int
    spot_entry: float
    spot_exit: float
    futures_entry: float
    futures_exit: float
    btc_quantity: float
    capital_usd: float
    entry_basis: float
    exit_basis: float
    gross_return: float
    base_net_return: float
    severe_net_return: float
    margin_remaining_ratio: float
    margin_safe: bool


@dataclass(frozen=True, slots=True)
class YearStats:
    year: int
    trade_count: int
    mean_base_net: float | None
    mean_severe_net: float | None


@dataclass(frozen=True, slots=True)
class CarryStats:
    trade_count: int
    mean_gross_return: float | None
    mean_base_net: float | None
    mean_severe_net: float | None
    median_base_net: float | None
    median_severe_net: float | None
    profit_factor_base: float | None
    profit_factor_severe: float | None
    win_rate_base: float | None
    win_rate_severe: float | None
    exact_sign_flip_p_value: float
    fdr_q_value: float
    all_margin_safe: bool
    yearly: tuple[YearStats, ...]
    discovery_pass: bool
    challenge_pass: bool


@dataclass(frozen=True, slots=True)
class ConfigResult:
    name: str
    entry_offset_days: int
    discovery: CarryStats
    challenge: CarryStats | None
    classification: str


def _profit_factor(values: list[float]) -> float | None:
    if not values:
        return None
    positive = sum(value for value in values if value > 0)
    negative = -sum(value for value in values if value < 0)
    if negative == 0:
        return 1_000_000.0 if positive > 0 else None
    return positive / negative


def exact_sign_flip_p_value(values: list[float]) -> float:
    if not values:
        return 1.0
    observed = sum(values)
    if observed <= 0:
        return 1.0
    if len(values) > 20:
        raise ValueError("Exact sign-flip test is intentionally limited to <=20 observations")
    total = 1 << len(values)
    extreme = 0
    for mask in range(total):
        candidate = 0.0
        for index, value in enumerate(values):
            candidate += value if mask & (1 << index) else -value
        if candidate >= observed - 1e-15:
            extreme += 1
    return extreme / total


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


def _trade_cost(
    *,
    rate_bps: float,
    spot_entry_notional: float,
    futures_entry_notional: float,
    spot_exit_notional: float,
    futures_exit_notional: float,
) -> float:
    return rate_bps / 10_000.0 * (
        spot_entry_notional
        + futures_entry_notional
        + spot_exit_notional
        + futures_exit_notional
    )


def build_trade(
    *,
    contract: DeliveryContract,
    entry_offset_days: int,
    spot_by_time: dict[int, Candle],
    futures_by_time: dict[int, DerivativeKline],
) -> DeliveryCarryTrade | None:
    entry_time = contract.delivery_time_ms - entry_offset_days * DAY_MS
    exit_time = contract.delivery_time_ms - EXIT_MINUTES_BEFORE_DELIVERY * MINUTE_MS
    if entry_time >= exit_time or exit_time >= OOS_2025_START_MS:
        return None

    spot_entry_bar = spot_by_time.get(entry_time)
    spot_exit_bar = spot_by_time.get(exit_time)
    futures_entry_bar = futures_by_time.get(entry_time)
    futures_exit_bar = futures_by_time.get(exit_time)
    if (
        spot_entry_bar is None
        or spot_exit_bar is None
        or futures_entry_bar is None
        or futures_exit_bar is None
    ):
        return None

    spot_entry = spot_entry_bar.open
    spot_exit = spot_exit_bar.open
    futures_entry = futures_entry_bar.open
    futures_exit = futures_exit_bar.open
    if min(spot_entry, spot_exit, futures_entry, futures_exit) <= 0:
        return None

    quantity = SPOT_ENTRY_NOTIONAL_USD / spot_entry
    futures_entry_notional = quantity * futures_entry
    capital = SPOT_ENTRY_NOTIONAL_USD + futures_entry_notional
    spot_pnl = quantity * (spot_exit - spot_entry)
    futures_pnl = quantity * (futures_entry - futures_exit)
    gross_pnl = spot_pnl + futures_pnl

    spot_exit_notional = quantity * spot_exit
    futures_exit_notional = quantity * futures_exit
    base_cost = _trade_cost(
        rate_bps=BASE_COST_BPS_PER_SIDE,
        spot_entry_notional=SPOT_ENTRY_NOTIONAL_USD,
        futures_entry_notional=futures_entry_notional,
        spot_exit_notional=spot_exit_notional,
        futures_exit_notional=futures_exit_notional,
    )
    severe_cost = _trade_cost(
        rate_bps=SEVERE_COST_BPS_PER_SIDE,
        spot_entry_notional=SPOT_ENTRY_NOTIONAL_USD,
        futures_entry_notional=futures_entry_notional,
        spot_exit_notional=spot_exit_notional,
        futures_exit_notional=futures_exit_notional,
    )

    held_rows = [
        row
        for timestamp, row in futures_by_time.items()
        if entry_time <= timestamp < exit_time
    ]
    if not held_rows:
        return None
    max_futures_high = max(row.high for row in held_rows)
    adverse_ratio = max(0.0, max_futures_high / futures_entry - 1.0)
    margin_remaining = 1.0 - adverse_ratio

    return DeliveryCarryTrade(
        symbol=contract.symbol("um"),
        year=contract.year,
        entry_offset_days=entry_offset_days,
        entry_time_ms=entry_time,
        exit_time_ms=exit_time,
        spot_entry=spot_entry,
        spot_exit=spot_exit,
        futures_entry=futures_entry,
        futures_exit=futures_exit,
        btc_quantity=quantity,
        capital_usd=capital,
        entry_basis=futures_entry / spot_entry - 1.0,
        exit_basis=futures_exit / spot_exit - 1.0,
        gross_return=gross_pnl / capital,
        base_net_return=(gross_pnl - base_cost) / capital,
        severe_net_return=(gross_pnl - severe_cost) / capital,
        margin_remaining_ratio=margin_remaining,
        margin_safe=margin_remaining >= MIN_MARGIN_REMAINING_RATIO,
    )


def summarize_trades(
    trades: tuple[DeliveryCarryTrade, ...],
    *,
    years: tuple[int, ...],
    q_value: float = 1.0,
) -> CarryStats:
    gross = [item.gross_return for item in trades]
    base = [item.base_net_return for item in trades]
    severe = [item.severe_net_return for item in trades]
    yearly = tuple(
        YearStats(
            year=year,
            trade_count=len(selected := [item for item in trades if item.year == year]),
            mean_base_net=mean(item.base_net_return for item in selected) if selected else None,
            mean_severe_net=(
                mean(item.severe_net_return for item in selected) if selected else None
            ),
        )
        for year in years
    )
    return CarryStats(
        trade_count=len(trades),
        mean_gross_return=mean(gross) if gross else None,
        mean_base_net=mean(base) if base else None,
        mean_severe_net=mean(severe) if severe else None,
        median_base_net=median(base) if base else None,
        median_severe_net=median(severe) if severe else None,
        profit_factor_base=_profit_factor(base),
        profit_factor_severe=_profit_factor(severe),
        win_rate_base=sum(value > 0 for value in base) / len(base) if base else None,
        win_rate_severe=(
            sum(value > 0 for value in severe) / len(severe) if severe else None
        ),
        exact_sign_flip_p_value=exact_sign_flip_p_value(base),
        fdr_q_value=q_value,
        all_margin_safe=all(item.margin_safe for item in trades),
        yearly=yearly,
        discovery_pass=False,
        challenge_pass=False,
    )


def _passes_discovery(stats: CarryStats) -> bool:
    if stats.trade_count != DISCOVERY_CONTRACT_COUNT:
        return False
    required_positive = (
        stats.mean_base_net,
        stats.mean_severe_net,
        stats.median_base_net,
        stats.median_severe_net,
    )
    if any(value is None or value <= 0 for value in required_positive):
        return False
    if stats.profit_factor_base is None or stats.profit_factor_base <= MIN_BASE_PF:
        return False
    if stats.profit_factor_severe is None or stats.profit_factor_severe <= MIN_SEVERE_PF:
        return False
    if stats.win_rate_base is None or stats.win_rate_base < MIN_BASE_WIN_RATE:
        return False
    if not stats.all_margin_safe or stats.fdr_q_value > FDR_Q_THRESHOLD:
        return False
    for item in stats.yearly:
        if (
            item.trade_count != 4
            or item.mean_base_net is None
            or item.mean_base_net <= 0
            or item.mean_severe_net is None
            or item.mean_severe_net <= 0
        ):
            return False
    return True


def _passes_challenge(stats: CarryStats) -> bool:
    severe_wins = round((stats.win_rate_severe or 0.0) * stats.trade_count)
    return (
        stats.trade_count == CHALLENGE_CONTRACT_COUNT
        and stats.mean_base_net is not None
        and stats.mean_base_net > 0
        and stats.mean_severe_net is not None
        and stats.mean_severe_net > 0
        and stats.median_base_net is not None
        and stats.median_base_net > 0
        and stats.median_severe_net is not None
        and stats.median_severe_net > 0
        and stats.profit_factor_base is not None
        and stats.profit_factor_base > MIN_BASE_PF
        and severe_wins >= MIN_CHALLENGE_SEVERE_WINS
        and stats.all_margin_safe
    )


def _verify_spot_hashes(research_path: Path, challenge_path: Path) -> dict[str, str]:
    expected = {
        "research": (research_path, SPOT_RESEARCH_SHA256),
        "challenge": (challenge_path, SPOT_CHALLENGE_SHA256),
    }
    actual: dict[str, str] = {}
    for name, (path, frozen_hash) in expected.items():
        if not path.is_file():
            raise FileNotFoundError(f"M17 frozen Spot input missing: {path}")
        digest = sha256_file(path)
        if digest != frozen_hash:
            raise RuntimeError(f"M17 frozen Spot hash mismatch for {name}: {digest}")
        actual[name] = digest
    return actual


def _download_contract_rows(contract: DeliveryContract) -> tuple[DerivativeKline, ...]:
    symbol = contract.symbol("um")
    expected_hash = USDM_NORMALIZED_SHA256[symbol]
    start = contract.delivery_time_ms - 30 * DAY_MS
    rows: list[DerivativeKline] = []
    files: list[ArchiveFileAudit] = []
    for year, month in _window_months(start, contract.delivery_time_ms):
        url = archive_url("um", symbol, year, month)
        downloaded = _download_verified_archive(url)
        if downloaded is None:
            raise RuntimeError(f"M17 qualified M16 archive became unavailable: {url}")
        payload, digest = downloaded
        parsed = parse_kline_archive(payload, futures_activity=True)
        rows.extend(parsed)
        files.append(
            ArchiveFileAudit(
                period=f"{year:04d}-{month:02d}",
                url=url,
                status="VERIFIED",
                sha256=digest,
                zip_bytes=len(payload),
                parsed_rows=len(parsed),
            )
        )
    audit = audit_contract_rows(
        family="um",
        contract=contract,
        rows=rows,
        archive_files=tuple(files),
    )
    if audit.status != "PASS":
        raise RuntimeError(f"M17 M16-qualified contract no longer passes audit: {symbol}")
    if audit.normalized_sha256 != expected_hash:
        raise RuntimeError(
            f"M17 normalized delivery hash mismatch for {symbol}: {audit.normalized_sha256}"
        )
    start_ms = audit.window_start_ms
    end_ms = audit.window_end_ms
    by_time = {
        row.open_time_ms: row
        for row in rows
        if start_ms <= row.open_time_ms < end_ms
    }
    return tuple(by_time[timestamp] for timestamp in sorted(by_time))


def _trades_for_offset(
    *,
    contracts: tuple[DeliveryContract, ...],
    offset_days: int,
    spot: tuple[Candle, ...],
    futures_by_symbol: dict[str, tuple[DerivativeKline, ...]],
) -> tuple[DeliveryCarryTrade, ...]:
    spot_by_time = {item.open_time_ms: item for item in spot}
    trades: list[DeliveryCarryTrade] = []
    for contract in contracts:
        symbol = contract.symbol("um")
        futures_by_time = {
            item.open_time_ms: item for item in futures_by_symbol[symbol]
        }
        trade = build_trade(
            contract=contract,
            entry_offset_days=offset_days,
            spot_by_time=spot_by_time,
            futures_by_time=futures_by_time,
        )
        if trade is not None:
            trades.append(trade)
    return tuple(trades)


def _config_name(offset_days: int) -> str:
    return f"delivery_carry_entry_{offset_days}d"


def run_m17_delivery_carry(
    *,
    research_path: str | Path = "data/cache/m2/btcusdt_15m_research.csv",
    challenge_path: str | Path = "data/cache/m2/btcusdt_15m_validation.csv",
    report_path: str | Path = "artifacts/m17_usdm_quarterly_cash_carry.json",
) -> dict[str, Any]:
    output = Path(report_path)
    if output.exists():
        raise RuntimeError("M17 evidence already exists; preserve first complete result")

    freeze = verify_m17_freeze()
    provenance = collect_source_provenance(require_clean=True)
    research_file = Path(research_path)
    challenge_file = Path(challenge_path)
    spot_hashes = _verify_spot_hashes(research_file, challenge_file)

    research_spot = tuple(load_csv(research_file))
    if max(item.open_time_ms for item in research_spot) >= 1_704_067_200_000:
        raise RuntimeError("M17 research Spot input crosses into reused 2024 challenge")

    contracts = delivery_contracts()
    discovery_contracts = tuple(item for item in contracts if item.discovery)
    challenge_contracts = tuple(item for item in contracts if not item.discovery)
    if len(discovery_contracts) != DISCOVERY_CONTRACT_COUNT:
        raise RuntimeError("M17 discovery contract count changed")
    if len(challenge_contracts) != CHALLENGE_CONTRACT_COUNT:
        raise RuntimeError("M17 challenge contract count changed")

    discovery_futures = {
        contract.symbol("um"): _download_contract_rows(contract)
        for contract in discovery_contracts
    }

    preliminary: dict[str, CarryStats] = {}
    discovery_trades_by_name: dict[str, tuple[DeliveryCarryTrade, ...]] = {}
    p_values: dict[str, float] = {}
    for offset_days in ENTRY_OFFSETS_DAYS:
        name = _config_name(offset_days)
        trades = _trades_for_offset(
            contracts=discovery_contracts,
            offset_days=offset_days,
            spot=research_spot,
            futures_by_symbol=discovery_futures,
        )
        discovery_trades_by_name[name] = trades
        stats = summarize_trades(trades, years=(2021, 2022, 2023))
        preliminary[name] = stats
        p_values[name] = stats.exact_sign_flip_p_value

    q_values = benjamini_hochberg(p_values)
    discovery_stats: dict[str, CarryStats] = {}
    passing_names: set[str] = set()
    for name, stats in preliminary.items():
        measured = replace(stats, fdr_q_value=q_values[name])
        measured = replace(measured, discovery_pass=_passes_discovery(measured))
        discovery_stats[name] = measured
        if measured.discovery_pass:
            passing_names.add(name)

    challenge_spot: tuple[Candle, ...] = ()
    challenge_futures: dict[str, tuple[DerivativeKline, ...]] = {}
    challenge_access = "BLOCKED_NO_DISCOVERY_PASS"
    if passing_names:
        challenge_access = "REUSED_2024_ACCESSED_AFTER_DISCOVERY_PASS"
        challenge_spot = tuple(load_csv(challenge_file))
        if max(item.open_time_ms for item in challenge_spot) >= OOS_2025_START_MS:
            raise RuntimeError("M17 challenge Spot input touches 2025 OOS")
        challenge_futures = {
            contract.symbol("um"): _download_contract_rows(contract)
            for contract in challenge_contracts
        }

    results: list[ConfigResult] = []
    for offset_days in ENTRY_OFFSETS_DAYS:
        name = _config_name(offset_days)
        challenge: CarryStats | None = None
        classification = "OBSERVATION_ONLY"
        if name in passing_names:
            trades = _trades_for_offset(
                contracts=challenge_contracts,
                offset_days=offset_days,
                spot=challenge_spot,
                futures_by_symbol=challenge_futures,
            )
            challenge_measured = summarize_trades(trades, years=(2024,))
            challenge = replace(
                challenge_measured,
                challenge_pass=_passes_challenge(challenge_measured),
            )
            if challenge.challenge_pass:
                classification = "MARKET_NEUTRAL_DELIVERY_CARRY_CANDIDATE"
        results.append(
            ConfigResult(
                name=name,
                entry_offset_days=offset_days,
                discovery=discovery_stats[name],
                challenge=challenge,
                classification=classification,
            )
        )

    if len(results) != CONFIG_COUNT:
        raise RuntimeError("M17 frozen configuration count changed after evaluation")
    candidates = [
        item.name
        for item in results
        if item.classification == "MARKET_NEUTRAL_DELIVERY_CARRY_CANDIDATE"
    ]
    decision = (
        "MARKET_NEUTRAL_DELIVERY_CARRY_CANDIDATE_FOUND"
        if candidates
        else "NO_STABLE_DELIVERY_CARRY_EDGE_FOUND"
    )
    report: dict[str, Any] = {
        "phase": "m17_usdm_quarterly_cash_carry_first_complete_frozen_evidence",
        "decision": decision,
        "policy_freeze": freeze,
        "source_provenance": provenance,
        "spot_input_sha256": spot_hashes,
        "delivery_input_sha256": USDM_NORMALIZED_SHA256,
        "challenge_access": challenge_access,
        "search": {
            "configuration_count": len(results),
            "market_neutral_delivery_carry_candidates": candidates,
            "discovery_passing_configs": sum(item.discovery.discovery_pass for item in results),
            "challenge_passing_configs": sum(
                bool(item.challenge and item.challenge.challenge_pass) for item in results
            ),
            "results": [asdict(item) for item in results],
        },
        "discovery_trades": {
            name: [asdict(item) for item in trades]
            for name, trades in discovery_trades_by_name.items()
        },
        "oos_2025": "LOCKED_NOT_ACCESSED",
        "coin_m": "FORBIDDEN",
        "leverage": "FORBIDDEN",
        "naked_short": "FORBIDDEN",
        "settlement_price_model": "FORBIDDEN_EXIT_15M_PRE_DELIVERY",
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
    parser = argparse.ArgumentParser(description="Run frozen M17 USD-M quarterly cash-and-carry")
    parser.add_argument("--report", default="artifacts/m17_usdm_quarterly_cash_carry.json")
    args = parser.parse_args()
    report = run_m17_delivery_carry(report_path=args.report)
    print("M17 decision:", report["decision"])
    print(
        "MARKET_NEUTRAL_DELIVERY_CARRY_CANDIDATE:",
        report["search"]["market_neutral_delivery_carry_candidates"],
    )
    print("discovery_passing_configs:", report["search"]["discovery_passing_configs"])
    print("challenge_passing_configs:", report["search"]["challenge_passing_configs"])
    print("challenge_access:", report["challenge_access"])
    print("2025 OOS remains", report["oos_2025"])


if __name__ == "__main__":
    main()
