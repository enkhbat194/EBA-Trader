from __future__ import annotations

import argparse
import math
from collections.abc import Iterable
from dataclasses import dataclass
from statistics import mean, median, pstdev

from .history import Candle, load_csv

YEAR_MS = 365.0 * 24.0 * 60.0 * 60.0 * 1000.0


@dataclass(frozen=True, slots=True)
class TrendBacktestConfig:
    fast_ema: int = 20
    slow_ema: int = 50
    initial_cash: float = 1000.0
    fee_bps: float = 10.0
    slippage_bps: float = 5.0

    def __post_init__(self) -> None:
        if self.fast_ema <= 1 or self.slow_ema <= self.fast_ema:
            raise ValueError("Require 1 < fast_ema < slow_ema")
        if self.initial_cash <= 0:
            raise ValueError("initial_cash must be positive")
        if min(self.fee_bps, self.slippage_bps) < 0:
            raise ValueError("Costs cannot be negative")


@dataclass(frozen=True, slots=True)
class ClosedTrade:
    entry_time_ms: int
    exit_time_ms: int
    entry_price: float
    exit_price: float
    net_return: float
    pnl: float


@dataclass(frozen=True, slots=True)
class BacktestResult:
    initial_cash: float
    final_equity: float
    total_return: float
    annualized_return: float
    benchmark_return: float
    benchmark_max_drawdown: float
    benchmark_relative_return: float
    max_drawdown: float
    trade_count: int
    win_rate: float
    profit_factor: float
    expectancy: float
    average_win: float
    average_loss: float
    sharpe: float
    sortino: float
    exposure: float
    total_cost: float
    trades: tuple[ClosedTrade, ...]


def ema(values: Iterable[float], period: int) -> list[float | None]:
    data = list(values)
    if period <= 1:
        raise ValueError("period must be > 1")
    result: list[float | None] = [None] * len(data)
    if len(data) < period:
        return result
    seed = mean(data[:period])
    result[period - 1] = seed
    alpha = 2.0 / (period + 1.0)
    current = seed
    for index in range(period, len(data)):
        current = alpha * data[index] + (1.0 - alpha) * current
        result[index] = current
    return result


def max_drawdown(equity_curve: list[float]) -> float:
    if not equity_curve:
        raise ValueError("equity_curve cannot be empty")
    peak = equity_curve[0]
    worst = 0.0
    for equity in equity_curve:
        peak = max(peak, equity)
        drawdown = equity / peak - 1.0
        worst = min(worst, drawdown)
    return worst


def _safe_profit_factor(trades: list[ClosedTrade]) -> float:
    gross_profit = sum(max(trade.pnl, 0.0) for trade in trades)
    gross_loss = -sum(min(trade.pnl, 0.0) for trade in trades)
    if gross_loss == 0:
        return math.inf if gross_profit > 0 else 0.0
    return gross_profit / gross_loss


def _infer_bars_per_year(bars: list[Candle]) -> float:
    if len(bars) < 2:
        return 0.0
    gaps = [
        bars[index].open_time_ms - bars[index - 1].open_time_ms
        for index in range(1, len(bars))
        if bars[index].open_time_ms > bars[index - 1].open_time_ms
    ]
    if not gaps:
        return 0.0
    interval_ms = float(median(gaps))
    return YEAR_MS / interval_ms if interval_ms > 0 else 0.0


def _annualized_return(initial: float, final: float, bars: list[Candle]) -> float:
    if not bars:
        return 0.0
    elapsed_ms = bars[-1].close_time_ms - bars[0].open_time_ms
    if initial <= 0 or final <= 0 or elapsed_ms <= 0:
        return 0.0
    years = elapsed_ms / YEAR_MS
    return (final / initial) ** (1.0 / years) - 1.0 if years > 0 else 0.0


def _risk_adjusted_ratios(returns: list[float], bars_per_year: float) -> tuple[float, float]:
    if len(returns) < 2 or bars_per_year <= 0:
        return 0.0, 0.0
    avg = mean(returns)
    std = pstdev(returns)
    sharpe = avg / std * math.sqrt(bars_per_year) if std > 0 else 0.0
    downside = [min(value, 0.0) for value in returns]
    downside_deviation = math.sqrt(mean([value * value for value in downside]))
    sortino = (
        avg / downside_deviation * math.sqrt(bars_per_year)
        if downside_deviation > 0
        else 0.0
    )
    return sharpe, sortino


def _first_evaluation_bar_index(
    bars: list[Candle],
    cfg: TrendBacktestConfig,
    trade_start_time_ms: int | None,
) -> int:
    minimum_index = cfg.slow_ema + 1
    if minimum_index >= len(bars):
        raise ValueError("Not enough candles for trend backtest")
    if trade_start_time_ms is None:
        return minimum_index
    for index in range(minimum_index, len(bars)):
        if bars[index].open_time_ms >= trade_start_time_ms:
            return index
    raise ValueError("trade_start_time_ms is after the available candles")


def _buy_and_hold_metrics(
    bars: list[Candle],
    cfg: TrendBacktestConfig,
) -> tuple[float, float]:
    entry_price = bars[0].open * (1.0 + cfg.slippage_bps / 10_000.0)
    entry_fee = cfg.initial_cash * cfg.fee_bps / 10_000.0
    quantity = (cfg.initial_cash - entry_fee) / entry_price

    curve = [cfg.initial_cash]
    for bar in bars:
        curve.append(quantity * bar.close)

    exit_price = bars[-1].close * (1.0 - cfg.slippage_bps / 10_000.0)
    gross = quantity * exit_price
    exit_fee = gross * cfg.fee_bps / 10_000.0
    final_equity = gross - exit_fee
    curve.append(final_equity)
    return final_equity / cfg.initial_cash - 1.0, max_drawdown(curve)


def run_trend_backtest(
    candles: Iterable[Candle],
    config: TrendBacktestConfig | None = None,
    *,
    trade_start_time_ms: int | None = None,
) -> BacktestResult:
    """Run a strict long-only EMA crossover baseline.

    EMA values are computed over every supplied candle, allowing walk-forward callers to
    provide causal pre-test history for indicator warm-up. Trading, equity metrics,
    exposure and the benchmark begin only at ``trade_start_time_ms`` (or the first valid
    post-warm-up bar when omitted).
    """
    cfg = config or TrendBacktestConfig()
    bars = list(candles)
    if len(bars) < cfg.slow_ema + 2:
        raise ValueError("Not enough candles for trend backtest")

    evaluation_bar_index = _first_evaluation_bar_index(bars, cfg, trade_start_time_ms)
    evaluation_start_ms = bars[evaluation_bar_index].open_time_ms
    evaluation_bars = bars[evaluation_bar_index:]

    closes = [bar.close for bar in bars]
    fast = ema(closes, cfg.fast_ema)
    slow = ema(closes, cfg.slow_ema)

    signal_seed_index = cfg.slow_ema - 1
    seed_fast = fast[signal_seed_index]
    seed_slow = slow[signal_seed_index]
    if seed_fast is None or seed_slow is None:
        raise RuntimeError("EMA warm-up state is unexpectedly unavailable")
    previous_signal = seed_fast > seed_slow

    cash = cfg.initial_cash
    quantity = 0.0
    entry_equity = 0.0
    entry_price = 0.0
    entry_time_ms = 0
    total_cost = 0.0
    trades: list[ClosedTrade] = []
    equity_curve: list[float] = [cash]
    bar_returns: list[float] = []
    exposed_bars = 0
    evaluated_bars = 0
    previous_equity = cash

    for index in range(cfg.slow_ema, len(bars) - 1):
        fast_value = fast[index]
        slow_value = slow[index]
        if fast_value is None or slow_value is None:
            continue

        signal = fast_value > slow_value
        crossed_up = not previous_signal and signal
        crossed_down = previous_signal and not signal
        next_bar = bars[index + 1]
        evaluation_active = next_bar.open_time_ms >= evaluation_start_ms

        if evaluation_active:
            if crossed_up and quantity == 0.0:
                execution_price = next_bar.open * (1.0 + cfg.slippage_bps / 10_000.0)
                fee = cash * cfg.fee_bps / 10_000.0
                slippage_cost = cash * cfg.slippage_bps / 10_000.0
                total_cost += fee + slippage_cost
                deployable = cash - fee
                quantity = deployable / execution_price
                entry_equity = cash
                entry_price = execution_price
                entry_time_ms = next_bar.open_time_ms
                cash = 0.0

            elif crossed_down and quantity > 0.0:
                execution_price = next_bar.open * (1.0 - cfg.slippage_bps / 10_000.0)
                gross = quantity * execution_price
                fee = gross * cfg.fee_bps / 10_000.0
                slippage_cost = gross * cfg.slippage_bps / 10_000.0
                total_cost += fee + slippage_cost
                cash = gross - fee
                pnl = cash - entry_equity
                trades.append(
                    ClosedTrade(
                        entry_time_ms=entry_time_ms,
                        exit_time_ms=next_bar.open_time_ms,
                        entry_price=entry_price,
                        exit_price=execution_price,
                        net_return=cash / entry_equity - 1.0,
                        pnl=pnl,
                    )
                )
                quantity = 0.0

            mark_equity = cash if quantity == 0.0 else quantity * next_bar.close
            if quantity > 0.0:
                exposed_bars += 1
            if previous_equity > 0:
                bar_returns.append(mark_equity / previous_equity - 1.0)
            previous_equity = mark_equity
            equity_curve.append(mark_equity)
            evaluated_bars += 1

        previous_signal = signal

    if quantity > 0.0:
        final_bar = bars[-1]
        execution_price = final_bar.close * (1.0 - cfg.slippage_bps / 10_000.0)
        gross = quantity * execution_price
        fee = gross * cfg.fee_bps / 10_000.0
        slippage_cost = gross * cfg.slippage_bps / 10_000.0
        total_cost += fee + slippage_cost
        cash = gross - fee
        trades.append(
            ClosedTrade(
                entry_time_ms=entry_time_ms,
                exit_time_ms=final_bar.close_time_ms,
                entry_price=entry_price,
                exit_price=execution_price,
                net_return=cash / entry_equity - 1.0,
                pnl=cash - entry_equity,
            )
        )
        if previous_equity > 0:
            bar_returns.append(cash / previous_equity - 1.0)
        equity_curve.append(cash)

    final_equity = cash
    wins = [trade.pnl for trade in trades if trade.pnl > 0]
    losses = [trade.pnl for trade in trades if trade.pnl < 0]
    expectancy = mean([trade.pnl for trade in trades]) if trades else 0.0
    average_win = mean(wins) if wins else 0.0
    average_loss = mean(losses) if losses else 0.0
    bars_per_year = _infer_bars_per_year(evaluation_bars)
    sharpe, sortino = _risk_adjusted_ratios(bar_returns, bars_per_year)
    benchmark_return, benchmark_drawdown = _buy_and_hold_metrics(evaluation_bars, cfg)
    total_return = final_equity / cfg.initial_cash - 1.0

    return BacktestResult(
        initial_cash=cfg.initial_cash,
        final_equity=final_equity,
        total_return=total_return,
        annualized_return=_annualized_return(cfg.initial_cash, final_equity, evaluation_bars),
        benchmark_return=benchmark_return,
        benchmark_max_drawdown=benchmark_drawdown,
        benchmark_relative_return=total_return - benchmark_return,
        max_drawdown=max_drawdown(equity_curve),
        trade_count=len(trades),
        win_rate=len(wins) / len(trades) if trades else 0.0,
        profit_factor=_safe_profit_factor(trades),
        expectancy=expectancy,
        average_win=average_win,
        average_loss=average_loss,
        sharpe=sharpe,
        sortino=sortino,
        exposure=exposed_bars / max(evaluated_bars, 1),
        total_cost=total_cost,
        trades=tuple(trades),
    )


def backtest_trend_cli() -> None:
    parser = argparse.ArgumentParser(
        description="Run EBA Trader strict EMA Trend Following V1 research backtest"
    )
    parser.add_argument("--csv", required=True)
    parser.add_argument("--fast", type=int, default=20)
    parser.add_argument("--slow", type=int, default=50)
    parser.add_argument("--cash", type=float, default=1000.0)
    parser.add_argument("--fee-bps", type=float, default=10.0)
    parser.add_argument("--slippage-bps", type=float, default=5.0)
    args = parser.parse_args()

    result = run_trend_backtest(
        load_csv(args.csv),
        TrendBacktestConfig(
            fast_ema=args.fast,
            slow_ema=args.slow,
            initial_cash=args.cash,
            fee_bps=args.fee_bps,
            slippage_bps=args.slippage_bps,
        ),
    )
    print(f"final_equity={result.final_equity:.2f}")
    print(f"total_return={result.total_return:.2%}")
    print(f"annualized_return={result.annualized_return:.2%}")
    print(f"btc_buy_hold={result.benchmark_return:.2%}")
    print(f"btc_buy_hold_drawdown={result.benchmark_max_drawdown:.2%}")
    print(f"benchmark_relative={result.benchmark_relative_return:.2%}")
    print(f"max_drawdown={result.max_drawdown:.2%}")
    print(f"trades={result.trade_count}")
    print(f"win_rate={result.win_rate:.2%}")
    print(f"profit_factor={result.profit_factor:.3f}")
    print(f"expectancy_usd={result.expectancy:.4f}")
    print(f"average_win_usd={result.average_win:.4f}")
    print(f"average_loss_usd={result.average_loss:.4f}")
    print(f"sharpe_approx={result.sharpe:.3f}")
    print(f"sortino_approx={result.sortino:.3f}")
    print(f"exposure={result.exposure:.2%}")
    print(f"estimated_cost_usd={result.total_cost:.4f}")
