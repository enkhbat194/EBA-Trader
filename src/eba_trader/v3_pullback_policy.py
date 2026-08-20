from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path

V3_PULLBACK_POLICY_VERSION = 1
V3_PULLBACK_POLICY_NAME = "v3_bull_pullback_recovery"
V3_PULLBACK_POLICY_DOCUMENT = Path("docs/M4_V3_BULL_PULLBACK_RECOVERY_HYPOTHESIS.md")
V3_PULLBACK_FREEZE_MANIFEST = Path("docs/M4_V3_BULL_PULLBACK_RECOVERY_POLICY_FREEZE.json")
V3_PULLBACK_POLICY_SHA256 = "e10448c974bc6ff74cabe9f2ca0616f67c78c212457bd2fa198af7776b805feb"

V3_RESEARCH_SHA256 = "253c6ae35856e58e35df17eaa71caeea5caaa3681c38dd7214a2872afccd8d63"
V3_VALIDATION_SHA256 = "3a96b6b668cfacb0fefabb8665675d4ca589cc712b0681fb57e7a13356eda0f2"


@dataclass(frozen=True, slots=True)
class V3PullbackConfig:
    regime_fast_ema_4h: int = 50
    regime_slow_ema_4h: int = 200
    regime_slope_lookback_4h: int = 6
    atr_period: int = 14
    rolling_vwap_bars: int = 96
    min_pullback_depth_atr: float = 0.75
    max_pullback_depth_atr: float = 2.25
    max_true_range_atr: float = 3.00
    arm_lifetime_bars: int = 8
    recovery_high_lookback: int = 3
    min_volume_ratio: float = 1.00
    recovery_vwap_buffer_atr: float = 0.25
    max_entry_gap_atr: float = 0.50
    stop_buffer_atr: float = 0.25
    min_stop_distance_atr: float = 0.75
    max_stop_distance_atr: float = 3.00
    target_r: float = 2.00
    max_holding_bars: int = 24
    reentry_cooldown_bars: int = 4
    complete_15m_after_gap: int = 16
    initial_cash: float = 1000.0
    risk_fraction: float = 0.0035
    max_notional_fraction: float = 0.50
    daily_loss_limit: float = 0.015
    max_drawdown_halt: float = 0.08
    fee_bps: float = 10.0
    slippage_bps: float = 5.0

    def __post_init__(self) -> None:
        if not 1 < self.regime_fast_ema_4h < self.regime_slow_ema_4h:
            raise ValueError("Require 1 < regime_fast_ema_4h < regime_slow_ema_4h")
        positive_ints = (
            self.regime_slope_lookback_4h,
            self.atr_period,
            self.rolling_vwap_bars,
            self.arm_lifetime_bars,
            self.recovery_high_lookback,
            self.max_holding_bars,
            self.reentry_cooldown_bars,
            self.complete_15m_after_gap,
        )
        if any(value <= 0 for value in positive_ints):
            raise ValueError("V3 lookbacks and counters must be positive")
        if not 0 < self.min_pullback_depth_atr < self.max_pullback_depth_atr:
            raise ValueError("Pullback depth envelope is invalid")
        if self.min_volume_ratio <= 0:
            raise ValueError("Volume ratio must be positive")
        multiples = (
            self.max_true_range_atr,
            self.recovery_vwap_buffer_atr,
            self.max_entry_gap_atr,
            self.stop_buffer_atr,
            self.min_stop_distance_atr,
            self.max_stop_distance_atr,
            self.target_r,
        )
        if any(value <= 0 for value in multiples):
            raise ValueError("V3 ATR/R multiples must be positive")
        if self.min_stop_distance_atr >= self.max_stop_distance_atr:
            raise ValueError("Stop-distance envelope is invalid")
        if not 0 < self.risk_fraction <= 0.005:
            raise ValueError("Risk fraction must be in (0, 0.005]")
        if not 0 < self.max_notional_fraction <= 1:
            raise ValueError("Notional fraction must be in (0, 1]")
        if not 0 < self.daily_loss_limit < self.max_drawdown_halt < 1:
            raise ValueError("Loss limits are invalid")
        if self.initial_cash <= 0:
            raise ValueError("Initial cash must be positive")
        if min(self.fee_bps, self.slippage_bps) < 0:
            raise ValueError("Trading costs cannot be negative")


BASELINE_V3_PULLBACK_CONFIG = V3PullbackConfig()

COST_SCENARIOS = {
    "base": {"fee_bps": 10.0, "slippage_bps": 5.0},
    "adverse": {"fee_bps": 10.0, "slippage_bps": 10.0},
    "severe": {"fee_bps": 15.0, "slippage_bps": 20.0},
}


def sha256_file(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def verify_v3_pullback_policy_freeze(root: str | Path = ".") -> dict[str, object]:
    base = Path(root)
    document = base / V3_PULLBACK_POLICY_DOCUMENT
    manifest_path = base / V3_PULLBACK_FREEZE_MANIFEST
    if not document.is_file() or not manifest_path.is_file():
        raise FileNotFoundError("V3 policy document or freeze manifest is missing")
    actual = sha256_file(document)
    if actual != V3_PULLBACK_POLICY_SHA256:
        raise RuntimeError("V3 policy document changed after freeze")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("cycle") != V3_PULLBACK_POLICY_NAME:
        raise RuntimeError("V3 freeze manifest cycle mismatch")
    if manifest.get("policy_sha256") != actual:
        raise RuntimeError("V3 freeze manifest hash mismatch")
    if manifest.get("gate_count") != 34:
        raise RuntimeError("V3 freeze must contain exactly 34 gates")
    if manifest.get("oos_2025") != "LOCKED_NOT_ACCESSED":
        raise RuntimeError("V3 freeze does not preserve the 2025 OOS lock")
    if manifest.get("ai_module") != "excluded":
        raise RuntimeError("V3 freeze unexpectedly includes an AI module")
    return manifest
