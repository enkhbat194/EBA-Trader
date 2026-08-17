from __future__ import annotations

import math
from bisect import bisect_left
from dataclasses import dataclass
from enum import StrEnum
from statistics import mean, median
from typing import Iterable, Sequence

from .backtest import BacktestResult
from .history import Candle

DAY_MS = 24 * 60 * 60 * 1000


class HistoricalRegime(StrEnum):
    BULL = "bull"
    BEAR = "bear"
    RANGE = "range"
    UNKNOWN = "unknown"


@dataclass(frozen=True, slots=True)
class RegimePoint:
    open_time_ms: int
    regime: HistoricalRegime
    directional_score: float


@dataclass(frozen=True, slots=True)
class RegimeTradeStats:
    regime: HistoricalRegime
    trade_count: int
    total_pnl: float
    average_pnl: float
    win_rate: float
    average_return: float


@dataclass(frozen=True, slots=True)
class RegimeDiagnostics:
    lookback_days: int
    threshold: float
    stats: tuple[RegimeTradeStats, ...]


def _median_interval_ms(candles: Sequence[Candle]) -> int:
    if len(candles) < 2:
        raise ValueError("Need at least two candles")
    gaps = [
        candles[index].open_time_ms - candles[index - 1].open_time_ms
        for index in range(1, len(candles))
    ]
    if any(gap <= 0 for gap in gaps):
        raise ValueError("Candles must be strictly increasing")
    return int(median(gaps))


def _lookback_bars(candles: Sequence[Candle], lookback_days: int) -> int:
    if lookback_days <= 0:
        raise ValueError("lookback_days must be positive")
    interval_ms = _median_interval_ms(candles)
    return max(2, round(lookback_days * DAY_MS / interval_ms))


def _directional_score(closes: Sequence[float]) -> float:
    if len(closes) < 3:
        return 0.0
    log_returns = [
        math.log(closes[index] / closes[index - 1])
        for index in range(1, len(closes))
        if closes[index] > 0 and closes[index - 1] > 0
    ]
    if not log_returns:
        return 0.0
    cumulative = sum(log_returns)
    path_energy = math.sqrt(sum(value * value for value in log_returns))
    return cumulative / path_energy if path_energy > 0 else 0.0


def classify_historical_regimes(
    candles: Iterable[Candle],
    *,
    lookback_days: int = 14,
    threshold: float = 1.5,
) -> tuple[RegimePoint, ...]:
    bars = list(candles)
    if threshold <= 0:
        raise ValueError("threshold must be positive")
    lookback = _lookback_bars(bars, lookback_days)

    points: list[RegimePoint] = []
    for index, candle in enumerate(bars):
        if index < lookback:
            points.append(
                RegimePoint(candle.open_time_ms, HistoricalRegime.UNKNOWN, 0.0)
            )
            continue

        closes = [bar.close for bar in bars[index - lookback : index + 1]]
        score = _directional_score(closes)
        if score >= threshold:
            regime = HistoricalRegime.BULL
        elif score <= -threshold:
            regime = HistoricalRegime.BEAR
        else:
            regime = HistoricalRegime.RANGE
        points.append(RegimePoint(candle.open_time_ms, regime, score))

    return tuple(points)


def regime_before_entry(
    points: Sequence[RegimePoint],
    entry_time_ms: int,
) -> HistoricalRegime:
    """Return the last regime whose candle was already complete before entry.

    RegimePoint timestamps are candle *open* times and their labels use that candle's close.
    A trade entered exactly at a candle open must therefore use the previous point, never
    the point sharing the entry timestamp.
    """
    if not points:
        return HistoricalRegime.UNKNOWN
    timestamps = [point.open_time_ms for point in points]
    index = bisect_left(timestamps, entry_time_ms) - 1
    return HistoricalRegime.UNKNOWN if index < 0 else points[index].regime


def diagnose_trades_by_regime(
    candles: Iterable[Candle],
    result: BacktestResult,
    *,
    lookback_days: int = 14,
    threshold: float = 1.5,
) -> RegimeDiagnostics:
    bars = list(candles)
    points = classify_historical_regimes(
        bars,
        lookback_days=lookback_days,
        threshold=threshold,
    )
    grouped: dict[HistoricalRegime, list[tuple[float, float]]] = {
        regime: [] for regime in HistoricalRegime
    }

    for trade in result.trades:
        regime = regime_before_entry(points, trade.entry_time_ms)
        grouped[regime].append((trade.pnl, trade.net_return))

    stats: list[RegimeTradeStats] = []
    for regime in HistoricalRegime:
        rows = grouped[regime]
        pnls = [row[0] for row in rows]
        returns = [row[1] for row in rows]
        stats.append(
            RegimeTradeStats(
                regime=regime,
                trade_count=len(rows),
                total_pnl=sum(pnls),
                average_pnl=mean(pnls) if pnls else 0.0,
                win_rate=(sum(value > 0 for value in pnls) / len(pnls)) if pnls else 0.0,
                average_return=mean(returns) if returns else 0.0,
            )
        )

    return RegimeDiagnostics(
        lookback_days=lookback_days,
        threshold=threshold,
        stats=tuple(stats),
    )
