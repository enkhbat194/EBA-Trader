from __future__ import annotations

from eba_trader.backtest import TrendBacktestConfig, run_trend_backtest
from eba_trader.history import Candle
from eba_trader.regime_diagnostics import (
    HistoricalRegime,
    RegimePoint,
    classify_historical_regimes,
    diagnose_trades_by_regime,
    regime_before_entry,
)

INTERVAL_MS = 15 * 60 * 1000


def make_market(count: int = 500) -> list[Candle]:
    rows: list[Candle] = []
    price = 100.0
    for index in range(count):
        if index < 180:
            price += 0.20
        elif index < 330:
            price -= 0.16
        else:
            price += 0.02 if index % 2 == 0 else -0.02
        rows.append(
            Candle(
                open_time_ms=index * INTERVAL_MS,
                open=price - 0.03,
                high=price + 0.25,
                low=price - 0.25,
                close=price,
                volume=100.0,
                close_time_ms=(index + 1) * INTERVAL_MS - 1,
                quote_volume=price * 100.0,
                trade_count=100,
            )
        )
    return rows


def rewrite_future(rows: list[Candle], start: int) -> list[Candle]:
    changed = list(rows[:start])
    price = rows[start - 1].close
    for index in range(start, len(rows)):
        price += 5.0
        changed.append(
            Candle(
                open_time_ms=rows[index].open_time_ms,
                open=price - 0.1,
                high=price + 0.5,
                low=price - 0.5,
                close=price,
                volume=rows[index].volume,
                close_time_ms=rows[index].close_time_ms,
                quote_volume=price * rows[index].volume,
                trade_count=rows[index].trade_count,
            )
        )
    return changed


def test_regime_classification_is_causal_before_future_rewrite() -> None:
    rows = make_market()
    changed = rewrite_future(rows, 300)
    original = classify_historical_regimes(rows, lookback_days=1, threshold=1.0)
    modified = classify_historical_regimes(changed, lookback_days=1, threshold=1.0)
    assert original[250] == modified[250]
    assert original[299] == modified[299]


def test_regime_classifier_detects_directional_sections() -> None:
    points = classify_historical_regimes(make_market(), lookback_days=1, threshold=1.0)
    assert points[150].regime is HistoricalRegime.BULL
    assert points[300].regime is HistoricalRegime.BEAR


def test_entry_uses_previous_completed_candle_not_same_open_timestamp() -> None:
    points = (
        RegimePoint(0, HistoricalRegime.BULL, 2.0),
        RegimePoint(INTERVAL_MS, HistoricalRegime.BEAR, -2.0),
        RegimePoint(2 * INTERVAL_MS, HistoricalRegime.RANGE, 0.0),
    )
    assert regime_before_entry(points, INTERVAL_MS) is HistoricalRegime.BULL
    assert regime_before_entry(points, 2 * INTERVAL_MS) is HistoricalRegime.BEAR
    assert regime_before_entry(points, 0) is HistoricalRegime.UNKNOWN


def test_trade_diagnostics_account_for_all_closed_trades() -> None:
    rows = make_market()
    result = run_trend_backtest(
        rows,
        TrendBacktestConfig(fast_ema=5, slow_ema=20, fee_bps=0, slippage_bps=0),
    )
    diagnostics = diagnose_trades_by_regime(
        rows,
        result,
        lookback_days=1,
        threshold=1.0,
    )
    assert sum(item.trade_count for item in diagnostics.stats) == result.trade_count
    diagnostic_pnl = sum(item.total_pnl for item in diagnostics.stats)
    trade_pnl = sum(trade.pnl for trade in result.trades)
    assert abs(diagnostic_pnl - trade_pnl) < 1e-9
