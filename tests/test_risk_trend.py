from __future__ import annotations

from eba_trader.execution_policy import (
    FIRST_CYCLE_ATR_MULTIPLIER,
    FIRST_CYCLE_ATR_PERIOD,
    FIRST_CYCLE_DAILY_LOSS_LIMIT,
    FIRST_CYCLE_MAX_DRAWDOWN_HALT,
    FIRST_CYCLE_RISK_FRACTION,
)
from eba_trader.history import Candle
from eba_trader.risk_trend import (
    RiskTrendConfig,
    _entry_quantity,
    atr,
    run_risk_sized_trend_backtest,
)

STEP = 15 * 60 * 1000


def make_market(count: int = 320) -> list[Candle]:
    rows: list[Candle] = []
    price = 100.0
    for index in range(count):
        phase = index % 120
        if phase < 40:
            price -= 0.18
        elif phase < 90:
            price += 0.42
        else:
            price -= 0.12
        open_price = price - 0.08
        rows.append(
            Candle(
                open_time_ms=index * STEP,
                open=open_price,
                high=max(open_price, price) + 0.35,
                low=min(open_price, price) - 0.35,
                close=price,
                volume=100.0,
                close_time_ms=(index + 1) * STEP - 1,
                quote_volume=10_000.0,
                trade_count=100,
            )
        )
    return rows


def test_default_risk_trend_config_matches_predeclared_policy() -> None:
    config = RiskTrendConfig()
    assert config.atr_period == FIRST_CYCLE_ATR_PERIOD
    assert config.atr_multiplier == FIRST_CYCLE_ATR_MULTIPLIER
    assert config.risk_fraction == FIRST_CYCLE_RISK_FRACTION
    assert config.daily_loss_limit == FIRST_CYCLE_DAILY_LOSS_LIMIT
    assert config.max_drawdown_halt == FIRST_CYCLE_MAX_DRAWDOWN_HALT


def test_atr_is_causal_and_positive_after_warmup() -> None:
    values = atr(make_market(40), period=14)
    assert all(value is None for value in values[:13])
    assert all(value is not None and value > 0 for value in values[13:])


def test_position_sizing_respects_planned_risk_and_spot_cash_cap() -> None:
    quantity, planned_loss = _entry_quantity(
        cash=1000.0,
        equity=1000.0,
        entry_price=100.0,
        stop_price=98.0,
        fee_bps=10.0,
        slippage_bps=5.0,
        risk_fraction=0.005,
    )
    assert quantity > 0
    assert planned_loss <= 5.0 + 1e-9
    entry_fee = quantity * 100.0 * 10.0 / 10_000.0
    assert quantity * 100.0 + entry_fee <= 1000.0 + 1e-9


def test_risk_sized_backtest_never_plans_above_half_percent_risk() -> None:
    result = run_risk_sized_trend_backtest(
        make_market(),
        RiskTrendConfig(fast_ema=5, slow_ema=15, atr_period=7),
    )
    assert result.final_equity > 0
    assert result.max_drawdown <= 0
    assert result.benchmark_max_drawdown <= 0
    assert 0 <= result.time_exposure <= 1
    assert 0 <= result.average_notional_fraction <= 1.0000001
    for item in result.trades:
        assert item.planned_risk_fraction <= 0.005 + 1e-12
        assert item.quantity > 0
        assert item.stop_price > 0
        assert item.exit_reason in {"stop", "ema_exit", "end_of_test"}
