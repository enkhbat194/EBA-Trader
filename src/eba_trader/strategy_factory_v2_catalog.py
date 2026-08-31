from __future__ import annotations

from dataclasses import dataclass

from .strategy_discovery_v2 import (
    MAX_CANDIDATES_PER_FAMILY,
    MAX_RAW_CANDIDATES,
    DiscoveryCandidate,
)
from .strategy_family_v2 import (
    ParameterAxis,
    StrategyDataPlane,
    StrategyFamilyV2,
    deterministic_quasi_random_candidates,
)

TARGET_FAMILY_MIN = 8
TARGET_FAMILY_MAX = 12
PILOT_SEED = "sfv2-discovery-pilot-v1"


@dataclass(frozen=True, slots=True)
class PilotFamilyPlan:
    family: StrategyFamilyV2
    engine_id: str
    sample_count: int

    def __post_init__(self) -> None:
        if not self.engine_id.strip():
            raise ValueError("pilot family engine_id is required")
        if not 1 <= self.sample_count <= MAX_CANDIDATES_PER_FAMILY:
            raise ValueError("pilot family sample_count exceeds the per-family cap")
        if self.sample_count > self.family.parameter_combination_count:
            raise ValueError("pilot family sample_count exceeds its declared parameter space")


def pilot_family_plans() -> tuple[PilotFamilyPlan, ...]:
    """Return the first executable Strategy Factory v2 discovery catalog.

    Every family maps to a causal backtest engine that already exists in EBA Trader. The catalog
    intentionally declares only 406 raw samples even though the pilot hard cap is 500: the cap is
    a maximum, not a quota that should be filled with low-value parameter variants.
    """

    plans = (
        PilotFamilyPlan(
            family=StrategyFamilyV2(
                family_id="atr_trailing_v1",
                economic_mechanism="volatility-scaled trailing trend persistence",
                data_plane=StrategyDataPlane.PRICE_VOLUME,
                timeframe="1m",
                features=("ohlc", "wilder_atr", "trailing_regime"),
                parameter_axes=(
                    ParameterAxis("atr_period", (7, 10, 14, 21, 28)),
                    ParameterAxis("atr_multiplier", (1.5, 1.75, 2.0, 2.5, 3.0, 3.5)),
                ),
            ),
            engine_id="atr_backtest.run_atr_trailing_backtest",
            sample_count=30,
        ),
        PilotFamilyPlan(
            family=StrategyFamilyV2(
                family_id="donchian_breakout_v1",
                economic_mechanism="price-channel breakout with faster channel exit",
                data_plane=StrategyDataPlane.PRICE_VOLUME,
                timeframe="1m",
                features=("ohlc", "prior_high_channel", "prior_low_channel"),
                parameter_axes=(
                    ParameterAxis("entry_lookback", (24, 32, 48, 64)),
                    ParameterAxis("exit_lookback", (4, 8, 12, 16)),
                ),
            ),
            engine_id="breakout_backtest.run_donchian_breakout_backtest",
            sample_count=16,
        ),
        PilotFamilyPlan(
            family=StrategyFamilyV2(
                family_id="mean_reversion_z_v1",
                economic_mechanism="statistical reversion after downside price deviation",
                data_plane=StrategyDataPlane.PRICE_VOLUME,
                timeframe="1m",
                features=("close", "rolling_mean", "rolling_std", "zscore"),
                parameter_axes=(
                    ParameterAxis("lookback", (12, 16, 24, 32, 48, 64)),
                    ParameterAxis("entry_z", (1.25, 1.5, 1.75, 2.0, 2.25, 2.5)),
                    ParameterAxis("exit_z", (0.0, 0.25, 0.5, 0.75)),
                ),
            ),
            engine_id="mean_reversion_backtest.run_mean_reversion_backtest",
            sample_count=64,
        ),
        PilotFamilyPlan(
            family=StrategyFamilyV2(
                family_id="orderflow_delta_impulse_v1",
                economic_mechanism="executed-flow imbalance continuation impulse",
                data_plane=StrategyDataPlane.EXECUTED_ORDER_FLOW,
                timeframe="1m",
                features=("of_delta_ratio",),
                parameter_axes=(
                    ParameterAxis("side", (-1, 1)),
                    ParameterAxis("entry_delta_ratio", (0.10, 0.15, 0.20, 0.25, 0.30)),
                    ParameterAxis("exit_delta_ratio", (0.0, 0.03, 0.05, 0.08)),
                ),
            ),
            engine_id="orderflow_impulse_backtest.run_orderflow_delta_impulse_backtest",
            sample_count=40,
        ),
        PilotFamilyPlan(
            family=StrategyFamilyV2(
                family_id="rolling_flow_trend_v1",
                economic_mechanism="price trend confirmed by persistent executed-flow direction",
                data_plane=StrategyDataPlane.HYBRID,
                timeframe="1m",
                features=("closed_price_return", "of_buy_volume", "of_sell_volume", "of_delta"),
                parameter_axes=(
                    ParameterAxis("side", (-1, 1)),
                    ParameterAxis("lookback", (4, 8, 12, 16, 24, 32)),
                    ParameterAxis("minimum_flow_ratio", (0.03, 0.05, 0.08, 0.12)),
                    ParameterAxis("minimum_price_return", (0.0005, 0.0010, 0.0015)),
                ),
            ),
            engine_id="sf3_signal_backtest.run_sf3_candidate_backtest",
            sample_count=64,
        ),
        PilotFamilyPlan(
            family=StrategyFamilyV2(
                family_id="volume_shock_momentum_v1",
                economic_mechanism="abnormal executed-volume shock followed by directional continuation",
                data_plane=StrategyDataPlane.HYBRID,
                timeframe="1m",
                features=("closed_candle_return", "executed_volume", "rolling_median_volume"),
                parameter_axes=(
                    ParameterAxis("side", (-1, 1)),
                    ParameterAxis("lookback", (15, 30, 60)),
                    ParameterAxis("volume_multiple", (1.25, 1.5, 1.75, 2.0, 2.5)),
                    ParameterAxis("minimum_price_return", (0.0005, 0.0010, 0.0015)),
                ),
            ),
            engine_id="sf3_signal_backtest.run_sf3_candidate_backtest",
            sample_count=64,
        ),
        PilotFamilyPlan(
            family=StrategyFamilyV2(
                family_id="vwap_reversion_flow_v1",
                economic_mechanism="price dislocation from executed-volume VWAP with flow reversal",
                data_plane=StrategyDataPlane.HYBRID,
                timeframe="1m",
                features=("rolling_vwap", "price_deviation_bps", "of_delta_ratio"),
                parameter_axes=(
                    ParameterAxis("side", (-1, 1)),
                    ParameterAxis("lookback", (30, 60, 90, 120)),
                    ParameterAxis("entry_deviation_bps", (5.0, 10.0, 15.0, 20.0, 30.0)),
                    ParameterAxis("minimum_reversal_delta_ratio", (0.03, 0.05, 0.08, 0.12)),
                ),
            ),
            engine_id="sf3_signal_backtest.run_sf3_candidate_backtest",
            sample_count=64,
        ),
        PilotFamilyPlan(
            family=StrategyFamilyV2(
                family_id="compression_expansion_v1",
                economic_mechanism="range compression followed by directional volatility expansion",
                data_plane=StrategyDataPlane.PRICE_VOLUME,
                timeframe="1m",
                features=("normalized_range", "short_long_range_ratio", "closed_candle_return"),
                parameter_axes=(
                    ParameterAxis("side", (-1, 1)),
                    ParameterAxis("short_lookback", (4, 8, 12)),
                    ParameterAxis("long_lookback", (24, 32, 48, 64)),
                    ParameterAxis("compression_ratio_max", (0.50, 0.60, 0.70, 0.80)),
                    ParameterAxis("minimum_price_return", (0.0005, 0.0010, 0.0015)),
                ),
            ),
            engine_id="sf3_signal_backtest.run_sf3_candidate_backtest",
            sample_count=64,
        ),
    )
    _validate_catalog(plans)
    return plans


def _validate_catalog(plans: tuple[PilotFamilyPlan, ...]) -> None:
    if not TARGET_FAMILY_MIN <= len(plans) <= TARGET_FAMILY_MAX:
        raise ValueError("pilot family catalog must contain 8-12 independent families")
    ids = tuple(plan.family.family_id for plan in plans)
    if len(ids) != len(set(ids)):
        raise ValueError("pilot family catalog contains duplicate family IDs")
    total = sum(plan.sample_count for plan in plans)
    if total > MAX_RAW_CANDIDATES:
        raise ValueError("pilot family catalog exceeds the raw candidate cap")


def planned_raw_candidate_count() -> int:
    return sum(plan.sample_count for plan in pilot_family_plans())


def generate_pilot_candidates(*, seed: str = PILOT_SEED) -> tuple[DiscoveryCandidate, ...]:
    if not seed.strip():
        raise ValueError("pilot seed is required")
    candidates: list[DiscoveryCandidate] = []
    for plan in pilot_family_plans():
        family_seed = f"{seed}:{plan.family.family_id}"
        candidates.extend(
            deterministic_quasi_random_candidates(
                plan.family,
                count=plan.sample_count,
                seed=family_seed,
            )
        )
    ids = tuple(candidate.candidate_id for candidate in candidates)
    if len(ids) != planned_raw_candidate_count():
        raise RuntimeError("pilot candidate generation did not honor the declared sample plan")
    if len(ids) != len(set(ids)):
        raise RuntimeError("pilot candidate generation produced duplicate candidate IDs")
    if len(ids) > MAX_RAW_CANDIDATES:
        raise RuntimeError("pilot candidate generation exceeded the hard raw-candidate cap")
    return tuple(candidates)
