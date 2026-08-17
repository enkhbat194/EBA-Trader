from __future__ import annotations

from eba_trader.backtest import (
    TrendBacktestConfig,
    _infer_bars_per_year,
    run_trend_backtest,
)
from eba_trader.history import Candle


def make_series(step_ms: int = 900_000) -> list[Candle]:
    rows: list[Candle] = []
    price = 100.0
    for index in range(140):
        if index < 40:
            price -= 0.20
        elif index < 95:
            price += 0.80
        else:
            price -= 0.70
        rows.append(
            Candle(
                open_time_ms=index * step_ms,
                open=price - 0.2,
                high=price + 0.6,
                low=price - 0.8,
                close=price,
                volume=100.0,
                close_time_ms=index * step_ms + step_ms - 1,
                quote_volume=10_000.0,
                trade_count=100,
            )
        )
    return rows


def make_always_rising(count: int = 140, step_ms: int = 900_000) -> list[Candle]:
    rows: list[Candle] = []
    price = 100.0
    for index in range(count):
        price += 0.5
        rows.append(
            Candle(
                open_time_ms=index * step_ms,
                open=price - 0.1,
                high=price + 0.4,
                low=price - 0.4,
                close=price,
                volume=100.0,
                close_time_ms=index * step_ms + step_ms - 1,
                quote_volume=10_000.0,
                trade_count=100,
            )
        )
    return rows


def test_trend_backtest_produces_trade_and_metrics() -> None:
    result = run_trend_backtest(
        make_series(),
        TrendBacktestConfig(fast_ema=5, slow_ema=15, fee_bps=0, slippage_bps=0),
    )
    assert result.trade_count >= 1
    assert result.final_equity > 0
    assert result.max_drawdown <= 0
    assert 0 <= result.exposure <= 1
    assert result.annualized_return > -1
    assert result.benchmark_relative_return == result.total_return - result.benchmark_return
    assert result.average_win >= 0
    assert result.average_loss <= 0


def test_strict_crossover_does_not_synthesize_entry_when_already_above() -> None:
    result = run_trend_backtest(
        make_always_rising(),
        TrendBacktestConfig(fast_ema=5, slow_ema=15, fee_bps=0, slippage_bps=0),
    )
    assert result.trade_count == 0
    assert result.final_equity == result.initial_cash


def test_costs_do_not_improve_result() -> None:
    rows = make_series()
    free = run_trend_backtest(
        rows,
        TrendBacktestConfig(fast_ema=5, slow_ema=15, fee_bps=0, slippage_bps=0),
    )
    costly = run_trend_backtest(
        rows,
        TrendBacktestConfig(fast_ema=5, slow_ema=15, fee_bps=10, slippage_bps=5),
    )
    assert costly.final_equity <= free.final_equity
    assert costly.total_cost > 0


def test_sharpe_scaling_infers_interval() -> None:
    bars_15m = _infer_bars_per_year(make_series(900_000))
    bars_1h = _infer_bars_per_year(make_series(3_600_000))
    assert 34_000 < bars_15m < 36_000
    assert 8_000 < bars_1h < 9_000


def test_entries_align_to_next_bar_opens_after_warmup() -> None:
    rows = make_series()
    cfg = TrendBacktestConfig(fast_ema=5, slow_ema=15, fee_bps=0, slippage_bps=0)
    result = run_trend_backtest(rows, cfg)
    assert result.trades
    valid_entry_times = {bar.open_time_ms for bar in rows[cfg.slow_ema + 1 :]}
    assert all(trade.entry_time_ms in valid_entry_times for trade in result.trades)


def test_trade_start_uses_prior_history_for_signal_but_no_prestart_trades() -> None:
    rows = make_series()
    start_index = 70
    start_ms = rows[start_index].open_time_ms
    result = run_trend_backtest(
        rows,
        TrendBacktestConfig(fast_ema=5, slow_ema=15, fee_bps=0, slippage_bps=0),
        trade_start_time_ms=start_ms,
    )
    assert all(trade.entry_time_ms >= start_ms for trade in result.trades)
    expected_benchmark = rows[-1].close / rows[start_index].open - 1.0
    assert abs(result.benchmark_return - expected_benchmark) < 1e-12
