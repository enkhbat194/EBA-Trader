from __future__ import annotations

from eba_trader.trend_v2_policy import (
    BASELINE_TREND_V2_CONFIG,
    TREND_V2_POLICY_SHA256,
    sha256_file,
    verify_trend_v2_policy_freeze,
)


def test_frozen_policy_hash_and_safety_boundary() -> None:
    manifest = verify_trend_v2_policy_freeze()

    assert sha256_file("docs/M3_TREND_V2_HYPOTHESIS.md") == TREND_V2_POLICY_SHA256
    assert manifest["gate_count"] == 36
    assert manifest["oos_2025"] == "LOCKED_NOT_ACCESSED"
    assert manifest["ai_module"] == "excluded"


def test_frozen_baseline_parameters_are_exact() -> None:
    config = BASELINE_TREND_V2_CONFIG

    assert (config.hour_fast_ema, config.hour_slow_ema) == (50, 200)
    assert config.hour_slope_lookback == 24
    assert (config.adx_period, config.adx_entry_threshold, config.adx_exit_threshold) == (
        14,
        25.0,
        20.0,
    )
    assert config.volatility_median_bars == 2880
    assert (config.min_relative_atr, config.max_relative_atr) == (0.60, 1.80)
    assert config.donchian_lookback == 20
    assert (config.signal_fast_ema, config.signal_slow_ema) == (20, 50)
    assert config.risk_fraction == 0.0035
    assert config.max_notional_fraction == 0.50
    assert config.daily_loss_limit == 0.015
    assert config.max_drawdown_halt == 0.08
