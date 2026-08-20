from __future__ import annotations

from dataclasses import replace

import pytest

from eba_trader.v3_pullback_policy import (
    BASELINE_V3_PULLBACK_CONFIG,
    V3_PULLBACK_POLICY_NAME,
    V3_PULLBACK_POLICY_SHA256,
    V3PullbackConfig,
    verify_v3_pullback_policy_freeze,
)


def test_v3_baseline_is_frozen_to_predeclared_values() -> None:
    config = BASELINE_V3_PULLBACK_CONFIG

    assert config.regime_fast_ema_4h == 50
    assert config.regime_slow_ema_4h == 200
    assert config.rolling_vwap_bars == 96
    assert config.min_pullback_depth_atr == pytest.approx(0.75)
    assert config.max_pullback_depth_atr == pytest.approx(2.25)
    assert config.arm_lifetime_bars == 8
    assert config.recovery_high_lookback == 3
    assert config.min_volume_ratio == pytest.approx(1.0)
    assert config.target_r == pytest.approx(2.0)
    assert config.risk_fraction == pytest.approx(0.0035)
    assert config.max_notional_fraction == pytest.approx(0.50)


def test_v3_freeze_manifest_matches_policy_document() -> None:
    manifest = verify_v3_pullback_policy_freeze()

    assert manifest["cycle"] == V3_PULLBACK_POLICY_NAME
    assert manifest["policy_sha256"] == V3_PULLBACK_POLICY_SHA256
    assert manifest["gate_count"] == 34
    assert manifest["oos_2025"] == "LOCKED_NOT_ACCESSED"
    assert manifest["ai_module"] == "excluded"


def test_v3_policy_rejects_invalid_pullback_envelope() -> None:
    with pytest.raises(ValueError, match="Pullback depth envelope"):
        replace(
            BASELINE_V3_PULLBACK_CONFIG,
            min_pullback_depth_atr=2.25,
            max_pullback_depth_atr=0.75,
        )


def test_v3_policy_rejects_invalid_stop_envelope() -> None:
    with pytest.raises(ValueError, match="Stop-distance envelope"):
        V3PullbackConfig(min_stop_distance_atr=3.0, max_stop_distance_atr=0.75)


def test_v3_policy_rejects_excessive_risk() -> None:
    with pytest.raises(ValueError, match="Risk fraction"):
        replace(BASELINE_V3_PULLBACK_CONFIG, risk_fraction=0.006)
