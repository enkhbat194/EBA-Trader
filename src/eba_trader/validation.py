from __future__ import annotations

import argparse
import json
import math
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from pathlib import Path
from statistics import median

from .backtest import BacktestResult, TrendBacktestConfig, run_trend_backtest
from .history import Candle, load_csv

DAY_MS = 24 * 60 * 60 * 1000


@dataclass(frozen=True, slots=True, order=True)
class ParameterCandidate:
    fast_ema: int
    slow_ema: int

    def __post_init__(self) -> None:
        if self.fast_ema <= 1 or self.slow_ema <= self.fast_ema:
            raise ValueError("Require 1 < fast_ema < slow_ema")


DEFAULT_PARAMETER_NEIGHBORHOOD = tuple(
    ParameterCandidate(fast, slow)
    for fast in (15, 20, 25)
    for slow in (40, 50, 60)
    if fast < slow
)


@dataclass(frozen=True, slots=True)
class ParameterEvaluation:
    candidate: ParameterCandidate
    total_return: float
    benchmark_relative_return: float
    max_drawdown: float
    benchmark_max_drawdown: float
    trade_count: int
    expectancy: float
    profit_factor: float


@dataclass(frozen=True, slots=True)
class NeighborhoodSummary:
    evaluations: tuple[ParameterEvaluation, ...]
    positive_return_fraction: float
    benchmark_beating_fraction: float
    positive_expectancy_fraction: float
    drawdown_improvement_fraction: float
    median_total_return: float
    worst_total_return: float
    median_max_drawdown: float
    worst_max_drawdown: float


@dataclass(frozen=True, slots=True)
class WalkForwardFold:
    fold: int
    train_start_ms: int
    train_end_ms: int
    test_start_ms: int
    test_end_ms: int
    selected: ParameterCandidate
    train_return: float
    train_max_drawdown: float
    test_return: float
    test_benchmark_return: float
    test_benchmark_max_drawdown: float
    test_benchmark_relative_return: float
    test_max_drawdown: float
    test_trade_count: int
    test_expectancy: float


@dataclass(frozen=True, slots=True)
class WalkForwardSummary:
    folds: tuple[WalkForwardFold, ...]
    positive_test_fraction: float
    benchmark_beating_fraction: float
    positive_expectancy_fraction: float
    drawdown_improvement_fraction: float
    median_test_return: float
    worst_test_return: float
    median_test_drawdown: float
    worst_test_drawdown: float
    median_benchmark_drawdown: float
    parameter_selection_counts: tuple[tuple[str, int], ...]


def _finite_or_none(value: float) -> float | None:
    return value if math.isfinite(value) else None


def _drawdown_is_better(strategy_drawdown: float, benchmark_drawdown: float) -> bool:
    # Drawdowns are zero or negative. A less-negative value is the better result.
    return strategy_drawdown > benchmark_drawdown


def _median_interval_ms(candles: Sequence[Candle]) -> int:
    if len(candles) < 2:
        raise ValueError("Need at least two candles to infer interval")
    gaps = [
        candles[index].open_time_ms - candles[index - 1].open_time_ms
        for index in range(1, len(candles))
    ]
    if any(gap <= 0 for gap in gaps):
        raise ValueError("Candles must be strictly increasing")
    return int(median(gaps))


def _bars_for_days(candles: Sequence[Candle], days: int) -> int:
    if days <= 0:
        raise ValueError("days must be positive")
    interval_ms = _median_interval_ms(candles)
    return max(1, round(days * DAY_MS / interval_ms))


def _evaluate_candidate(
    candles: Sequence[Candle],
    candidate: ParameterCandidate,
    *,
    initial_cash: float,
    fee_bps: float,
    slippage_bps: float,
    trade_start_time_ms: int | None = None,
) -> BacktestResult:
    return run_trend_backtest(
        candles,
        TrendBacktestConfig(
            fast_ema=candidate.fast_ema,
            slow_ema=candidate.slow_ema,
            initial_cash=initial_cash,
            fee_bps=fee_bps,
            slippage_bps=slippage_bps,
        ),
        trade_start_time_ms=trade_start_time_ms,
    )


def run_parameter_neighborhood(
    candles: Iterable[Candle],
    *,
    candidates: Sequence[ParameterCandidate] = DEFAULT_PARAMETER_NEIGHBORHOOD,
    initial_cash: float = 1000.0,
    fee_bps: float = 10.0,
    slippage_bps: float = 5.0,
) -> NeighborhoodSummary:
    bars = list(candles)
    if not candidates:
        raise ValueError("At least one parameter candidate is required")

    evaluations: list[ParameterEvaluation] = []
    for candidate in candidates:
        result = _evaluate_candidate(
            bars,
            candidate,
            initial_cash=initial_cash,
            fee_bps=fee_bps,
            slippage_bps=slippage_bps,
        )
        evaluations.append(
            ParameterEvaluation(
                candidate=candidate,
                total_return=result.total_return,
                benchmark_relative_return=result.benchmark_relative_return,
                max_drawdown=result.max_drawdown,
                benchmark_max_drawdown=result.benchmark_max_drawdown,
                trade_count=result.trade_count,
                expectancy=result.expectancy,
                profit_factor=result.profit_factor,
            )
        )

    returns = [item.total_return for item in evaluations]
    drawdowns = [item.max_drawdown for item in evaluations]
    count = len(evaluations)
    return NeighborhoodSummary(
        evaluations=tuple(evaluations),
        positive_return_fraction=sum(item.total_return > 0 for item in evaluations) / count,
        benchmark_beating_fraction=(
            sum(item.benchmark_relative_return > 0 for item in evaluations) / count
        ),
        positive_expectancy_fraction=sum(item.expectancy > 0 for item in evaluations) / count,
        drawdown_improvement_fraction=(
            sum(
                _drawdown_is_better(item.max_drawdown, item.benchmark_max_drawdown)
                for item in evaluations
            )
            / count
        ),
        median_total_return=median(returns),
        worst_total_return=min(returns),
        median_max_drawdown=median(drawdowns),
        worst_max_drawdown=min(drawdowns),
    )


def _select_on_train(
    train: Sequence[Candle],
    candidates: Sequence[ParameterCandidate],
    *,
    initial_cash: float,
    fee_bps: float,
    slippage_bps: float,
) -> tuple[ParameterCandidate, BacktestResult]:
    if not candidates:
        raise ValueError("At least one parameter candidate is required")

    scored: list[tuple[ParameterCandidate, BacktestResult]] = []
    for candidate in candidates:
        result = _evaluate_candidate(
            train,
            candidate,
            initial_cash=initial_cash,
            fee_bps=fee_bps,
            slippage_bps=slippage_bps,
        )
        scored.append((candidate, result))

    return max(
        scored,
        key=lambda item: (
            item[1].total_return,
            item[1].max_drawdown,
            item[0].slow_ema,
            item[0].fast_ema,
        ),
    )


def run_walk_forward(
    candles: Iterable[Candle],
    *,
    candidates: Sequence[ParameterCandidate] = DEFAULT_PARAMETER_NEIGHBORHOOD,
    train_days: int = 180,
    test_days: int = 30,
    step_days: int = 30,
    initial_cash: float = 1000.0,
    fee_bps: float = 10.0,
    slippage_bps: float = 5.0,
) -> WalkForwardSummary:
    """Run causal rolling walk-forward validation.

    Parameter selection sees train data only. Test evaluation receives ``train + test``
    solely as causal EMA warm-up context, while ``trade_start_time_ms`` prevents any
    train-period trade/equity/benchmark contribution.
    """
    bars = list(candles)
    if not candidates:
        raise ValueError("At least one parameter candidate is required")
    if min(train_days, test_days, step_days) <= 0:
        raise ValueError("train_days, test_days and step_days must be positive")

    max_slow = max(candidate.slow_ema for candidate in candidates)
    train_bars = _bars_for_days(bars, train_days)
    test_bars = _bars_for_days(bars, test_days)
    step_bars = _bars_for_days(bars, step_days)
    if train_bars < max_slow + 2:
        raise ValueError("Train window is too short for the slowest EMA candidate")
    if test_bars < 2:
        raise ValueError("Test window must contain at least two bars")
    if len(bars) < train_bars + test_bars:
        raise ValueError("Not enough candles for one walk-forward fold")

    folds: list[WalkForwardFold] = []
    fold_index = 1
    start = 0
    while start + train_bars + test_bars <= len(bars):
        train = bars[start : start + train_bars]
        test = bars[start + train_bars : start + train_bars + test_bars]

        selected, train_result = _select_on_train(
            train,
            candidates,
            initial_cash=initial_cash,
            fee_bps=fee_bps,
            slippage_bps=slippage_bps,
        )

        test_result = _evaluate_candidate(
            train + test,
            selected,
            initial_cash=initial_cash,
            fee_bps=fee_bps,
            slippage_bps=slippage_bps,
            trade_start_time_ms=test[0].open_time_ms,
        )
        folds.append(
            WalkForwardFold(
                fold=fold_index,
                train_start_ms=train[0].open_time_ms,
                train_end_ms=train[-1].close_time_ms,
                test_start_ms=test[0].open_time_ms,
                test_end_ms=test[-1].close_time_ms,
                selected=selected,
                train_return=train_result.total_return,
                train_max_drawdown=train_result.max_drawdown,
                test_return=test_result.total_return,
                test_benchmark_return=test_result.benchmark_return,
                test_benchmark_max_drawdown=test_result.benchmark_max_drawdown,
                test_benchmark_relative_return=test_result.benchmark_relative_return,
                test_max_drawdown=test_result.max_drawdown,
                test_trade_count=test_result.trade_count,
                test_expectancy=test_result.expectancy,
            )
        )
        fold_index += 1
        start += step_bars

    if not folds:
        raise ValueError("No walk-forward folds were produced")

    selection_counts: dict[str, int] = {}
    for fold in folds:
        key = f"{fold.selected.fast_ema}/{fold.selected.slow_ema}"
        selection_counts[key] = selection_counts.get(key, 0) + 1

    test_returns = [fold.test_return for fold in folds]
    test_drawdowns = [fold.test_max_drawdown for fold in folds]
    benchmark_drawdowns = [fold.test_benchmark_max_drawdown for fold in folds]
    count = len(folds)
    return WalkForwardSummary(
        folds=tuple(folds),
        positive_test_fraction=sum(fold.test_return > 0 for fold in folds) / count,
        benchmark_beating_fraction=(
            sum(fold.test_benchmark_relative_return > 0 for fold in folds) / count
        ),
        positive_expectancy_fraction=sum(fold.test_expectancy > 0 for fold in folds) / count,
        drawdown_improvement_fraction=(
            sum(
                _drawdown_is_better(
                    fold.test_max_drawdown,
                    fold.test_benchmark_max_drawdown,
                )
                for fold in folds
            )
            / count
        ),
        median_test_return=median(test_returns),
        worst_test_return=min(test_returns),
        median_test_drawdown=median(test_drawdowns),
        worst_test_drawdown=min(test_drawdowns),
        median_benchmark_drawdown=median(benchmark_drawdowns),
        parameter_selection_counts=tuple(sorted(selection_counts.items())),
    )


def _neighborhood_to_dict(summary: NeighborhoodSummary) -> dict[str, object]:
    return {
        "positive_return_fraction": summary.positive_return_fraction,
        "benchmark_beating_fraction": summary.benchmark_beating_fraction,
        "positive_expectancy_fraction": summary.positive_expectancy_fraction,
        "drawdown_improvement_fraction": summary.drawdown_improvement_fraction,
        "median_total_return": summary.median_total_return,
        "worst_total_return": summary.worst_total_return,
        "median_max_drawdown": summary.median_max_drawdown,
        "worst_max_drawdown": summary.worst_max_drawdown,
        "evaluations": [
            {
                "fast_ema": item.candidate.fast_ema,
                "slow_ema": item.candidate.slow_ema,
                "total_return": item.total_return,
                "benchmark_relative_return": item.benchmark_relative_return,
                "max_drawdown": item.max_drawdown,
                "benchmark_max_drawdown": item.benchmark_max_drawdown,
                "drawdown_better_than_btc": _drawdown_is_better(
                    item.max_drawdown,
                    item.benchmark_max_drawdown,
                ),
                "trade_count": item.trade_count,
                "expectancy": item.expectancy,
                "profit_factor": _finite_or_none(item.profit_factor),
            }
            for item in summary.evaluations
        ],
    }


def _walk_forward_to_dict(summary: WalkForwardSummary) -> dict[str, object]:
    return {
        "positive_test_fraction": summary.positive_test_fraction,
        "benchmark_beating_fraction": summary.benchmark_beating_fraction,
        "positive_expectancy_fraction": summary.positive_expectancy_fraction,
        "drawdown_improvement_fraction": summary.drawdown_improvement_fraction,
        "median_test_return": summary.median_test_return,
        "worst_test_return": summary.worst_test_return,
        "median_test_drawdown": summary.median_test_drawdown,
        "worst_test_drawdown": summary.worst_test_drawdown,
        "median_benchmark_drawdown": summary.median_benchmark_drawdown,
        "parameter_selection_counts": dict(summary.parameter_selection_counts),
        "folds": [
            {
                "fold": fold.fold,
                "train_start_ms": fold.train_start_ms,
                "train_end_ms": fold.train_end_ms,
                "test_start_ms": fold.test_start_ms,
                "test_end_ms": fold.test_end_ms,
                "selected_fast_ema": fold.selected.fast_ema,
                "selected_slow_ema": fold.selected.slow_ema,
                "train_return": fold.train_return,
                "train_max_drawdown": fold.train_max_drawdown,
                "test_return": fold.test_return,
                "test_benchmark_return": fold.test_benchmark_return,
                "test_benchmark_max_drawdown": fold.test_benchmark_max_drawdown,
                "test_benchmark_relative_return": fold.test_benchmark_relative_return,
                "test_max_drawdown": fold.test_max_drawdown,
                "test_drawdown_better_than_btc": _drawdown_is_better(
                    fold.test_max_drawdown,
                    fold.test_benchmark_max_drawdown,
                ),
                "test_trade_count": fold.test_trade_count,
                "test_expectancy": fold.test_expectancy,
            }
            for fold in summary.folds
        ],
    }


def trend_validation_cli() -> None:
    parser = argparse.ArgumentParser(
        description="Run parameter-neighborhood and rolling walk-forward validation"
    )
    parser.add_argument("--csv", required=True)
    parser.add_argument("--cash", type=float, default=1000.0)
    parser.add_argument("--fee-bps", type=float, default=10.0)
    parser.add_argument("--slippage-bps", type=float, default=5.0)
    parser.add_argument("--train-days", type=int, default=180)
    parser.add_argument("--test-days", type=int, default=30)
    parser.add_argument("--step-days", type=int, default=30)
    parser.add_argument("--report", default="artifacts/m2_trend_robustness.json")
    args = parser.parse_args()

    candles = load_csv(args.csv)
    neighborhood = run_parameter_neighborhood(
        candles,
        initial_cash=args.cash,
        fee_bps=args.fee_bps,
        slippage_bps=args.slippage_bps,
    )
    walk_forward = run_walk_forward(
        candles,
        initial_cash=args.cash,
        fee_bps=args.fee_bps,
        slippage_bps=args.slippage_bps,
        train_days=args.train_days,
        test_days=args.test_days,
        step_days=args.step_days,
    )

    report = {
        "method": {
            "selection_rule": "max train total_return; tie-break shallower drawdown",
            "test_indicator_context": "causal train history; trading starts at test boundary",
            "candidate_count": len(DEFAULT_PARAMETER_NEIGHBORHOOD),
            "train_days": args.train_days,
            "test_days": args.test_days,
            "step_days": args.step_days,
            "fee_bps_per_side": args.fee_bps,
            "slippage_bps_per_side": args.slippage_bps,
        },
        "neighborhood": _neighborhood_to_dict(neighborhood),
        "walk_forward": _walk_forward_to_dict(walk_forward),
    }
    output = Path(args.report)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")

    print(
        "neighborhood "
        f"positive={neighborhood.positive_return_fraction:.1%} "
        f"beats_btc={neighborhood.benchmark_beating_fraction:.1%} "
        f"risk_better={neighborhood.drawdown_improvement_fraction:.1%} "
        f"median_return={neighborhood.median_total_return:.2%} "
        f"worst_return={neighborhood.worst_total_return:.2%}"
    )
    print(
        "walk_forward "
        f"folds={len(walk_forward.folds)} "
        f"positive={walk_forward.positive_test_fraction:.1%} "
        f"beats_btc={walk_forward.benchmark_beating_fraction:.1%} "
        f"risk_better={walk_forward.drawdown_improvement_fraction:.1%} "
        f"median_test={walk_forward.median_test_return:.2%} "
        f"worst_test={walk_forward.worst_test_return:.2%}"
    )
    print(f"report={output}")
