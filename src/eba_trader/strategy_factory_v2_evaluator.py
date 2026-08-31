from __future__ import annotations

import math
import time
from dataclasses import dataclass
from typing import Any

from .atr_backtest import AtrTrailingConfig, atr_trailing_regime, run_atr_trailing_backtest
from .backtest import BacktestResult
from .breakout_backtest import (
    DonchianBreakoutConfig,
    donchian_signals,
    run_donchian_breakout_backtest,
)
from .history import Candle
from .mean_reversion_backtest import (
    MeanReversionConfig,
    mean_reversion_signals,
    run_mean_reversion_backtest,
)
from .orderflow_feature_dataset import OrderFlowFeatureRow
from .orderflow_impulse_backtest import (
    OrderFlowDeltaImpulseConfig,
    orderflow_delta_signals,
    run_orderflow_delta_impulse_backtest,
)
from .sf3_protocol import SF3Candidate
from .sf3_signal_backtest import run_sf3_candidate_backtest, sf3_candidate_signals
from .strategy_discovery_batch import DiscoveryEvaluation
from .strategy_discovery_v2 import BehavioralFingerprint, DiscoveryCandidate

PRICE_FAMILIES = frozenset({"atr_trailing_v1", "donchian_breakout_v1", "mean_reversion_z_v1"})
ORDERFLOW_FAMILIES = frozenset(
    {
        "orderflow_delta_impulse_v1",
        "rolling_flow_trend_v1",
        "volume_shock_momentum_v1",
        "vwap_reversion_flow_v1",
        "compression_expansion_v1",
    }
)
SUPPORTED_FAMILIES = PRICE_FAMILIES | ORDERFLOW_FAMILIES
REGIME_BUCKET_COUNT = 4


@dataclass(frozen=True, slots=True)
class DiscoveryDatasetV2:
    """One already-declared D0 evaluation dataset loaded in memory.

    The adapter does not choose data windows and has no D1/D2/D3 authority. Dataset identity is
    supplied separately by the immutable trial ledger/batch context.
    """

    candles: tuple[Candle, ...]
    orderflow_rows: tuple[OrderFlowFeatureRow, ...] = ()
    trade_start_time_ms: int | None = None

    def __post_init__(self) -> None:
        if len(self.candles) < 3:
            raise ValueError("D0 evaluator requires at least three candles")
        _assert_chronological_candles(self.candles)
        if self.orderflow_rows:
            _assert_orderflow_alignment(self.candles, self.orderflow_rows)
        if self.trade_start_time_ms is not None:
            if isinstance(self.trade_start_time_ms, bool) or not isinstance(
                self.trade_start_time_ms, int
            ):
                raise TypeError("trade_start_time_ms must be an integer UTC epoch millisecond")
            inside = (
                self.candles[0].open_time_ms
                <= self.trade_start_time_ms
                < self.candles[-1].close_time_ms
            )
            if not inside:
                raise ValueError("trade_start_time_ms must be inside the loaded D0 dataset")


@dataclass(frozen=True, slots=True)
class CandidateExecution:
    result: BacktestResult
    signal_keys: tuple[str, ...]
    side: int


def make_d0_candidate_evaluator(dataset: DiscoveryDatasetV2):
    """Return a `run_discovery_batch` compatible evaluator for one immutable D0 dataset."""

    def evaluate(candidate: DiscoveryCandidate) -> DiscoveryEvaluation:
        started = time.perf_counter_ns()
        try:
            execution = execute_discovery_candidate(dataset=dataset, candidate=candidate)
            compute_ms = max(0, (time.perf_counter_ns() - started) // 1_000_000)
            metrics = _normalized_metrics(execution.result, execution.signal_keys, dataset)
            behavior = _behavioral_fingerprint(
                result=execution.result,
                signal_keys=execution.signal_keys,
                side=execution.side,
                dataset=dataset,
            )
            rejection_reason = None
            if not execution.signal_keys:
                rejection_reason = "no_signal_opportunity_on_declared_d0_dataset"
            elif execution.result.trade_count == 0:
                rejection_reason = "no_executed_trade_on_declared_d0_dataset"
            return DiscoveryEvaluation(
                metrics=metrics,
                behavior=behavior,
                compute_ms=compute_ms,
                rejection_reason=rejection_reason,
            )
        except (TypeError, ValueError) as exc:
            compute_ms = max(0, (time.perf_counter_ns() - started) // 1_000_000)
            return DiscoveryEvaluation(
                metrics={"selection_only": True, "static_valid": False},
                behavior=None,
                compute_ms=compute_ms,
                rejection_reason=f"invalid_candidate_spec:{type(exc).__name__}",
            )

    return evaluate


def execute_discovery_candidate(
    *,
    dataset: DiscoveryDatasetV2,
    candidate: DiscoveryCandidate,
) -> CandidateExecution:
    """Execute one bounded catalog candidate with existing causal EBA strategy semantics."""

    family = candidate.family_id
    if family not in SUPPORTED_FAMILIES:
        raise ValueError(f"unsupported Strategy Factory v2 family: {family}")
    parameters = dict(candidate.parameters)
    start = dataset.trade_start_time_ms

    if family == "atr_trailing_v1":
        config = AtrTrailingConfig(**parameters)
        result = run_atr_trailing_backtest(dataset.candles, config, trade_start_time_ms=start)
        _, regimes = atr_trailing_regime(dataset.candles, config)
        signals = tuple(
            index > 0 and regimes[index - 1] <= 0 and regime == 1
            for index, regime in enumerate(regimes)
        )
        signal_keys = _price_signal_keys(dataset.candles, signals, side=1, start_ms=start)
        return CandidateExecution(result=result, signal_keys=signal_keys, side=1)

    if family == "donchian_breakout_v1":
        config = DonchianBreakoutConfig(**parameters)
        result = run_donchian_breakout_backtest(dataset.candles, config, trade_start_time_ms=start)
        entries, _ = donchian_signals(dataset.candles, config)
        signal_keys = _price_signal_keys(dataset.candles, entries, side=1, start_ms=start)
        return CandidateExecution(result=result, signal_keys=signal_keys, side=1)

    if family == "mean_reversion_z_v1":
        config = MeanReversionConfig(**parameters)
        result = run_mean_reversion_backtest(dataset.candles, config, trade_start_time_ms=start)
        entries, _, _ = mean_reversion_signals(dataset.candles, config)
        signal_keys = _price_signal_keys(dataset.candles, entries, side=1, start_ms=start)
        return CandidateExecution(result=result, signal_keys=signal_keys, side=1)

    rows = _required_orderflow_rows(dataset)
    if family == "orderflow_delta_impulse_v1":
        config = OrderFlowDeltaImpulseConfig(**parameters)
        result = run_orderflow_delta_impulse_backtest(rows, config, trade_start_time_ms=start)
        entries, _, _ = orderflow_delta_signals(rows, config)
        signal_keys = _orderflow_signal_keys(rows, entries, side=config.side, start_ms=start)
        return CandidateExecution(result=result, signal_keys=signal_keys, side=config.side)

    sf3_candidate = SF3Candidate(
        candidate_id=candidate.candidate_id,
        family=family,
        parameters=parameters,
    )
    observations = sf3_candidate_signals(rows, sf3_candidate)
    result = run_sf3_candidate_backtest(rows, sf3_candidate, trade_start_time_ms=start)
    side = _candidate_side(parameters)
    signal_keys = _orderflow_signal_keys(
        rows,
        tuple(observation.entry for observation in observations),
        side=side,
        start_ms=start,
    )
    return CandidateExecution(result=result, signal_keys=signal_keys, side=side)


def _normalized_metrics(
    result: BacktestResult,
    signal_keys: tuple[str, ...],
    dataset: DiscoveryDatasetV2,
) -> dict[str, Any]:
    turnover = _turnover(result, dataset)
    metrics: dict[str, Any] = {
        "selection_only": True,
        "static_valid": True,
        "total_return": result.total_return,
        "expectancy": result.expectancy,
        "trade_count": result.trade_count,
        "signal_count": len(signal_keys),
        "max_drawdown": result.max_drawdown,
        "total_cost": result.total_cost,
        "benchmark_relative_return": result.benchmark_relative_return,
        "exposure": result.exposure,
        "turnover_round_trips_per_1000_bars": turnover,
    }
    for name, value in metrics.items():
        if isinstance(value, float) and not math.isfinite(value):
            raise RuntimeError(f"non-finite D0 selection metric: {name}")
    return metrics


def _behavioral_fingerprint(
    *,
    result: BacktestResult,
    signal_keys: tuple[str, ...],
    side: int,
    dataset: DiscoveryDatasetV2,
) -> BehavioralFingerprint:
    trade_keys = tuple(
        sorted(
            {
                f"{trade.entry_time_ms:013d}:{trade.exit_time_ms:013d}:{side:+d}"
                for trade in result.trades
            }
        )
    )
    return BehavioralFingerprint(
        signal_keys=signal_keys,
        trade_keys=trade_keys,
        regime_returns=_chronological_trade_return_buckets(result, dataset),
        exposure_fraction=result.exposure,
        turnover=_turnover(result, dataset),
    )


def _chronological_trade_return_buckets(
    result: BacktestResult,
    dataset: DiscoveryDatasetV2,
) -> tuple[float, ...]:
    start_ms = dataset.trade_start_time_ms or dataset.candles[0].open_time_ms
    end_ms = dataset.candles[-1].close_time_ms
    span = max(1, end_ms - start_ms)
    sums = [0.0] * REGIME_BUCKET_COUNT
    for trade in result.trades:
        relative = min(max(trade.entry_time_ms - start_ms, 0), span - 1)
        bucket = min(REGIME_BUCKET_COUNT - 1, relative * REGIME_BUCKET_COUNT // span)
        sums[bucket] += trade.net_return
    return tuple(sums)


def _turnover(result: BacktestResult, dataset: DiscoveryDatasetV2) -> float:
    evaluated_bars = sum(
        candle.open_time_ms >= (dataset.trade_start_time_ms or dataset.candles[0].open_time_ms)
        for candle in dataset.candles
    )
    return 1000.0 * result.trade_count / max(1, evaluated_bars)


def _price_signal_keys(
    candles: tuple[Candle, ...],
    signals: tuple[bool, ...],
    *,
    side: int,
    start_ms: int | None,
) -> tuple[str, ...]:
    if len(candles) != len(signals):
        raise ValueError("price signal vector length does not match candles")
    return tuple(
        sorted(
            {
                f"{candle.open_time_ms:013d}:{side:+d}"
                for candle, signal in zip(candles, signals, strict=True)
                if signal and (start_ms is None or candle.open_time_ms >= start_ms)
            }
        )
    )


def _orderflow_signal_keys(
    rows: tuple[OrderFlowFeatureRow, ...],
    signals: tuple[bool, ...],
    *,
    side: int,
    start_ms: int | None,
) -> tuple[str, ...]:
    if len(rows) != len(signals):
        raise ValueError("order-flow signal vector length does not match rows")
    return tuple(
        sorted(
            {
                f"{row.candle.open_time_ms:013d}:{side:+d}"
                for row, signal in zip(rows, signals, strict=True)
                if signal and (start_ms is None or row.candle.open_time_ms >= start_ms)
            }
        )
    )


def _required_orderflow_rows(dataset: DiscoveryDatasetV2) -> tuple[OrderFlowFeatureRow, ...]:
    if not dataset.orderflow_rows:
        raise ValueError("candidate family requires executed-order-flow rows")
    return dataset.orderflow_rows


def _candidate_side(parameters: dict[str, object]) -> int:
    value = parameters.get("side")
    if isinstance(value, bool) or not isinstance(value, int) or value not in (-1, 1):
        raise ValueError("candidate side must be +1 or -1")
    return value


def _assert_chronological_candles(candles: tuple[Candle, ...]) -> None:
    previous_open: int | None = None
    for candle in candles:
        if previous_open is not None and candle.open_time_ms <= previous_open:
            raise ValueError("D0 candles must be strictly chronological")
        previous_open = candle.open_time_ms


def _assert_orderflow_alignment(
    candles: tuple[Candle, ...],
    rows: tuple[OrderFlowFeatureRow, ...],
) -> None:
    if len(candles) != len(rows):
        raise ValueError("D0 candles and order-flow rows must have identical lengths")
    for candle, row in zip(candles, rows, strict=True):
        if row.candle.open_time_ms != candle.open_time_ms:
            raise ValueError("D0 candles and order-flow rows are not time-aligned")
        if row.footprint_available_at_ms > row.candle.open_time_ms:
            raise ValueError("D0 order-flow feature is not causal at candle open")
