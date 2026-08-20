from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path

TREND_V2_POLICY_VERSION = 1
TREND_V2_POLICY_NAME = "trend_v2_regime_filtered_volatility_aware_breakout"
TREND_V2_POLICY_DOCUMENT = Path("docs/M3_TREND_V2_HYPOTHESIS.md")
TREND_V2_FREEZE_MANIFEST = Path("docs/M3_TREND_V2_POLICY_FREEZE.json")
TREND_V2_POLICY_SHA256 = "af1b0667e0d0b514379286943c3ff7909140592dd562153e0213eff728a435f9"

TREND_V2_RESEARCH_SHA256 = "253c6ae35856e58e35df17eaa71caeea5caaa3681c38dd7214a2872afccd8d63"
TREND_V2_VALIDATION_SHA256 = "3a96b6b668cfacb0fefabb8665675d4ca589cc712b0681fb57e7a13356eda0f2"


@dataclass(frozen=True, slots=True)
class TrendV2Config:
    hour_fast_ema: int = 50
    hour_slow_ema: int = 200
    hour_slope_lookback: int = 24
    adx_period: int = 14
    adx_entry_threshold: float = 25.0
    adx_exit_threshold: float = 20.0
    atr_period: int = 14
    volatility_median_bars: int = 2880
    min_relative_atr: float = 0.60
    max_relative_atr: float = 1.80
    absolute_atr_pct_ceiling: float = 0.03
    donchian_lookback: int = 20
    signal_fast_ema: int = 20
    signal_slow_ema: int = 50
    signal_slope_lookback: int = 4
    max_entry_gap_atr: float = 0.50
    initial_stop_atr: float = 2.50
    trailing_stop_atr: float = 3.00
    regime_exit_bars: int = 2
    reentry_cooldown_bars: int = 4
    complete_hours_after_gap: int = 4
    initial_cash: float = 1000.0
    risk_fraction: float = 0.0035
    max_notional_fraction: float = 0.50
    daily_loss_limit: float = 0.015
    max_drawdown_halt: float = 0.08
    fee_bps: float = 10.0
    slippage_bps: float = 5.0

    def __post_init__(self) -> None:
        if not 1 < self.hour_fast_ema < self.hour_slow_ema:
            raise ValueError("Require 1 < hour_fast_ema < hour_slow_ema")
        if not 1 < self.signal_fast_ema < self.signal_slow_ema:
            raise ValueError("Require 1 < signal_fast_ema < signal_slow_ema")
        integer_positive = (
            self.hour_slope_lookback,
            self.adx_period,
            self.atr_period,
            self.volatility_median_bars,
            self.donchian_lookback,
            self.signal_slope_lookback,
            self.regime_exit_bars,
            self.reentry_cooldown_bars,
            self.complete_hours_after_gap,
        )
        if any(value <= 0 for value in integer_positive):
            raise ValueError("Trend V2 lookbacks and counters must be positive")
        if not 0 < self.min_relative_atr < self.max_relative_atr:
            raise ValueError("Relative ATR envelope is invalid")
        if not 0 < self.absolute_atr_pct_ceiling < 1:
            raise ValueError("ATR/close ceiling must be in (0, 1)")
        if min(
            self.max_entry_gap_atr,
            self.initial_stop_atr,
            self.trailing_stop_atr,
        ) <= 0:
            raise ValueError("ATR multiples must be positive")
        if not 0 < self.risk_fraction <= 0.005:
            raise ValueError("Risk fraction must be in (0, 0.005]")
        if not 0 < self.max_notional_fraction <= 1:
            raise ValueError("Notional fraction must be in (0, 1]")
        if not 0 < self.daily_loss_limit < self.max_drawdown_halt < 1:
            raise ValueError("Loss limits are invalid")
        if self.initial_cash <= 0 or min(self.fee_bps, self.slippage_bps) < 0:
            raise ValueError("Cash must be positive and costs non-negative")


BASELINE_TREND_V2_CONFIG = TrendV2Config()

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


def verify_trend_v2_policy_freeze(root: str | Path = ".") -> dict[str, object]:
    base = Path(root)
    document = base / TREND_V2_POLICY_DOCUMENT
    manifest_path = base / TREND_V2_FREEZE_MANIFEST
    if not document.is_file() or not manifest_path.is_file():
        raise FileNotFoundError("Trend V2 policy document or freeze manifest is missing")
    actual = sha256_file(document)
    if actual != TREND_V2_POLICY_SHA256:
        raise RuntimeError("Trend V2 policy document changed after freeze")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("policy_sha256") != actual:
        raise RuntimeError("Trend V2 freeze manifest hash mismatch")
    if manifest.get("gate_count") != 36:
        raise RuntimeError("Trend V2 freeze must contain exactly 36 gates")
    if manifest.get("oos_2025") != "LOCKED_NOT_ACCESSED":
        raise RuntimeError("Trend V2 freeze does not preserve the 2025 OOS lock")
    if manifest.get("ai_module") != "excluded":
        raise RuntimeError("Trend V2 freeze unexpectedly includes an AI module")
    return manifest
