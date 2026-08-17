from __future__ import annotations

import pytest

from eba_trader.history import Candle
from eba_trader.validation import (
    ParameterCandidate,
    run_parameter_neighborhood,
    run_walk_forward,
)

INTERVAL_MS = 15 * 60 * 1000


def make_market(count: int = 480) -> list[Candle]:
    rows: list[Candle] = []
    price = 100.0
    for index in range(count):
        phase = index % 160
        if phase < 70:
            price += 0.25
        elif phase < 110:
            price -= 0.18
        else:
            price += 0.04
        open_price = price - 0.05
        rows.append(
            Candle(
                open_time_ms=index * INTERVAL_MS,
                open=open_price,
                high=max(open_price, price) + 0.30,
                low=min(open_price, price) - 0.30,
                close=price,
                volume=100.0 + index,
                close_time_ms=(index + 1) * INTERVAL_MS - 1,
                quote_volume=(100.0 + index) * price,
                trade_count=100 + index,
            )
        )
    return rows


def rewrite_tail(rows: list[Candle], start: int) -> list[Candle]:
    rewritten = list(rows[:start])
    price = rows[start - 1].close
    for index in range(start, len(rows)):
        price += 2.0
        rewritten.append(
            Candle(
                open_time_ms=rows[index].open_time_ms,
                open=price - 0.2,
                high=price + 0.5,
                low=price - 0.5,
                close=price,
                volume=rows[index].volume,
                close_time_ms=rows[index].close_time_ms,
                quote_volume=rows[index].quote_volume,
                trade_count=rows[index].trade_count,
            )
        )
    return rewritten


def test_parameter_neighborhood_returns_bounded_fractions() -> None:
    summary = run_parameter_neighborhood(
        make_market(),
        candidates=(
            ParameterCandidate(5, 15),
            ParameterCandidate(8, 20),
            ParameterCandidate(10, 30),
        ),
        fee_bps=10,
        slippage_bps=5,
    )
    assert len(summary.evaluations) == 3
    assert 0 <= summary.positive_return_fraction <= 1
    assert 0 <= summary.benchmark_beating_fraction <= 1
    assert 0 <= summary.positive_expectancy_fraction <= 1
    assert summary.worst_total_return <= summary.median_total_return
    assert summary.worst_max_drawdown <= summary.median_max_drawdown <= 0


def test_walk_forward_produces_out_of_sample_folds() -> None:
    candidates = (
        ParameterCandidate(5, 15),
        ParameterCandidate(8, 20),
        ParameterCandidate(10, 30),
    )
    summary = run_walk_forward(
        make_market(),
        candidates=candidates,
        train_days=1,
        test_days=1,
        step_days=1,
        fee_bps=10,
        slippage_bps=5,
    )
    assert len(summary.folds) >= 3
    assert sum(count for _, count in summary.parameter_selection_counts) == len(summary.folds)
    assert 0 <= summary.positive_test_fraction <= 1
    assert 0 <= summary.benchmark_beating_fraction <= 1
    for fold in summary.folds:
        assert fold.train_end_ms < fold.test_start_ms
        assert fold.selected in candidates
        assert fold.test_max_drawdown <= 0


def test_first_walk_forward_selection_does_not_look_into_test_tail() -> None:
    rows = make_market()
    altered = rewrite_tail(rows, 96)
    candidates = (
        ParameterCandidate(5, 15),
        ParameterCandidate(8, 20),
        ParameterCandidate(10, 30),
    )
    original = run_walk_forward(
        rows,
        candidates=candidates,
        train_days=1,
        test_days=1,
        step_days=1,
        fee_bps=0,
        slippage_bps=0,
    )
    changed = run_walk_forward(
        altered,
        candidates=candidates,
        train_days=1,
        test_days=1,
        step_days=1,
        fee_bps=0,
        slippage_bps=0,
    )
    assert original.folds[0].selected == changed.folds[0].selected
    assert original.folds[0].train_return == changed.folds[0].train_return


def test_walk_forward_rejects_too_short_series() -> None:
    with pytest.raises(ValueError, match="Not enough candles"):
        run_walk_forward(
            make_market(150),
            candidates=(ParameterCandidate(5, 15),),
            train_days=1,
            test_days=1,
            step_days=1,
        )
