from __future__ import annotations

import csv
import math
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

from . import backtest as backtest_module
from . import history as history_module
from . import holdout_guard as holdout_guard_module
from . import orderflow_feature_dataset as orderflow_feature_dataset_module
from .backtest import BacktestResult, TrendBacktestConfig, run_trend_backtest
from .history import load_csv, validate_interval_window
from .holdout_guard import assert_not_first_cycle_oos_overlap
from .orderflow_feature_dataset import load_orderflow_feature_csv


@dataclass(frozen=True, slots=True)
class BacktestExecution:
    adapter_name: str
    adapter_version: str
    metrics: dict[str, Any]
    resolved_config: dict[str, Any]
    dataset_metadata: dict[str, Any]
    source_files: tuple[Path, ...]


class BacktestAdapter(Protocol):
    name: str
    version: str

    def run(
        self,
        *,
        dataset_path: str | Path,
        strategy_spec: Mapping[str, Any],
        experiment_parameters: Mapping[str, Any],
        stage: str,
        allow_frozen_oos: bool = False,
    ) -> BacktestExecution: ...


def _json_number(value: float) -> float | None:
    return value if math.isfinite(value) else None


def _result_metrics(result: BacktestResult) -> dict[str, Any]:
    return {
        "initial_cash": result.initial_cash,
        "final_equity": result.final_equity,
        "total_return": result.total_return,
        "annualized_return": _json_number(result.annualized_return),
        "annualized_return_infinite": math.isinf(result.annualized_return),
        "benchmark_return": result.benchmark_return,
        "benchmark_max_drawdown": result.benchmark_max_drawdown,
        "benchmark_relative_return": result.benchmark_relative_return,
        "max_drawdown": result.max_drawdown,
        "trade_count": result.trade_count,
        "win_rate": result.win_rate,
        "profit_factor": _json_number(result.profit_factor),
        "profit_factor_infinite": math.isinf(result.profit_factor),
        "expectancy": result.expectancy,
        "average_win": result.average_win,
        "average_loss": result.average_loss,
        "sharpe": result.sharpe,
        "sortino": result.sortino,
        "exposure": result.exposure,
        "total_cost": result.total_cost,
    }


def _require_mapping(value: object, *, name: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ValueError(f"{name} must be an object")
    return value


def _reject_unknown(mapping: Mapping[str, Any], allowed: set[str], *, name: str) -> None:
    unknown = sorted(set(mapping) - allowed)
    if unknown:
        raise ValueError(f"Unsupported {name} fields: {', '.join(unknown)}")


def _as_int(value: object, *, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"{name} must be an integer")
    return value


def _as_float(value: object, *, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{name} must be numeric")
    result = float(value)
    if not math.isfinite(result):
        raise ValueError(f"{name} must be finite")
    return result


def _parse_dataset_spec(
    strategy_spec: Mapping[str, Any],
    *,
    adapter_name: str,
    config_fields: set[str],
    experiment_parameters: Mapping[str, Any],
    stage: str,
    allow_frozen_oos: bool,
) -> tuple[Mapping[str, Any], str, str, int, int, dict[str, Any]]:
    spec_fields = {"adapter", "fixed", "dataset"}
    dataset_fields = {"symbol", "interval", "start_ms", "end_ms"}
    _reject_unknown(strategy_spec, spec_fields, name="strategy spec")
    if strategy_spec.get("adapter") != adapter_name:
        raise ValueError(f"Strategy spec adapter must be {adapter_name!r}")

    fixed = _require_mapping(strategy_spec.get("fixed", {}), name="strategy fixed config")
    dataset = _require_mapping(strategy_spec.get("dataset"), name="strategy dataset")
    _reject_unknown(fixed, config_fields, name="fixed config")
    _reject_unknown(dataset, dataset_fields, name="dataset")
    _reject_unknown(experiment_parameters, config_fields, name="experiment parameter")

    overlap = sorted(set(fixed) & set(experiment_parameters))
    if overlap:
        joined = ", ".join(overlap)
        raise ValueError(f"Experiment parameters cannot override immutable fixed fields: {joined}")

    symbol = str(dataset.get("symbol", "")).strip().upper()
    interval = str(dataset.get("interval", "")).strip()
    if not symbol:
        raise ValueError("dataset.symbol is required")
    if not interval:
        raise ValueError("dataset.interval is required")
    start_ms = _as_int(dataset.get("start_ms"), name="dataset.start_ms")
    end_ms = _as_int(dataset.get("end_ms"), name="dataset.end_ms")
    if start_ms >= end_ms:
        raise ValueError("dataset.start_ms must be earlier than dataset.end_ms")

    if not allow_frozen_oos:
        assert_not_first_cycle_oos_overlap(
            symbol=symbol,
            interval=interval,
            start_ms=start_ms,
            end_ms=end_ms,
            context=f"Generic adapter stage={stage}",
        )
    return fixed, symbol, interval, start_ms, end_ms, {**fixed, **experiment_parameters}


def _resolve_trend_config(merged: Mapping[str, Any]) -> tuple[TrendBacktestConfig, int | None]:
    config_kwargs: dict[str, Any] = {}
    if "fast_ema" in merged:
        config_kwargs["fast_ema"] = _as_int(merged["fast_ema"], name="fast_ema")
    if "slow_ema" in merged:
        config_kwargs["slow_ema"] = _as_int(merged["slow_ema"], name="slow_ema")
    if "initial_cash" in merged:
        config_kwargs["initial_cash"] = _as_float(merged["initial_cash"], name="initial_cash")
    if "fee_bps" in merged:
        config_kwargs["fee_bps"] = _as_float(merged["fee_bps"], name="fee_bps")
    if "slippage_bps" in merged:
        config_kwargs["slippage_bps"] = _as_float(merged["slippage_bps"], name="slippage_bps")

    trade_start_time_ms = None
    if "trade_start_time_ms" in merged:
        trade_start_time_ms = _as_int(merged["trade_start_time_ms"], name="trade_start_time_ms")
    return TrendBacktestConfig(**config_kwargs), trade_start_time_ms


def _resolved_trend_config(
    config: TrendBacktestConfig,
    trade_start_time_ms: int | None,
) -> dict[str, Any]:
    return {
        "fast_ema": config.fast_ema,
        "slow_ema": config.slow_ema,
        "initial_cash": config.initial_cash,
        "fee_bps": config.fee_bps,
        "slippage_bps": config.slippage_bps,
        "trade_start_time_ms": trade_start_time_ms,
    }


def _require_stacked_columns(path: Path) -> None:
    with path.open("r", newline="", encoding="utf-8") as handle:
        fields = set(csv.DictReader(handle).fieldnames or ())
    required = {
        "of_stacked_buy_levels",
        "of_stacked_sell_levels",
        "of_stacked_imbalance",
    }
    if not required <= fields:
        raise ValueError("stacked imbalance gate requires a v2 feature CSV with stacked columns")


class EmaTrendV1Adapter:
    """Adapter from an immutable research spec to the existing EMA baseline backtester."""

    name = "ema_trend_v1"
    version = "1"
    _CONFIG_FIELDS = {
        "fast_ema",
        "slow_ema",
        "initial_cash",
        "fee_bps",
        "slippage_bps",
        "trade_start_time_ms",
    }

    def run(
        self,
        *,
        dataset_path: str | Path,
        strategy_spec: Mapping[str, Any],
        experiment_parameters: Mapping[str, Any],
        stage: str,
        allow_frozen_oos: bool = False,
    ) -> BacktestExecution:
        _, symbol, interval, start_ms, end_ms, merged = _parse_dataset_spec(
            strategy_spec,
            adapter_name=self.name,
            config_fields=self._CONFIG_FIELDS,
            experiment_parameters=experiment_parameters,
            stage=stage,
            allow_frozen_oos=allow_frozen_oos,
        )
        config, trade_start_time_ms = _resolve_trend_config(merged)
        path = Path(dataset_path)
        candles = validate_interval_window(load_csv(path), interval, start_ms, end_ms)
        result = run_trend_backtest(candles, config, trade_start_time_ms=trade_start_time_ms)
        return BacktestExecution(
            adapter_name=self.name,
            adapter_version=self.version,
            metrics=_result_metrics(result),
            resolved_config=_resolved_trend_config(config, trade_start_time_ms),
            dataset_metadata={
                "symbol": symbol,
                "interval": interval,
                "start_ms": start_ms,
                "end_ms": end_ms,
                "candle_count": len(candles),
            },
            source_files=(
                Path(__file__),
                Path(backtest_module.__file__),
                Path(history_module.__file__),
                Path(holdout_guard_module.__file__),
            ),
        )


class EmaFeatureBaselineV1Adapter:
    """EMA baseline that uses the exact same aligned feature CSV as the order-flow arm."""

    name = "ema_feature_baseline_v1"
    version = "1"
    _CONFIG_FIELDS = EmaTrendV1Adapter._CONFIG_FIELDS

    def run(
        self,
        *,
        dataset_path: str | Path,
        strategy_spec: Mapping[str, Any],
        experiment_parameters: Mapping[str, Any],
        stage: str,
        allow_frozen_oos: bool = False,
    ) -> BacktestExecution:
        _, symbol, interval, start_ms, end_ms, merged = _parse_dataset_spec(
            strategy_spec,
            adapter_name=self.name,
            config_fields=self._CONFIG_FIELDS,
            experiment_parameters=experiment_parameters,
            stage=stage,
            allow_frozen_oos=allow_frozen_oos,
        )
        config, trade_start_time_ms = _resolve_trend_config(merged)
        path = Path(dataset_path)
        feature_rows = load_orderflow_feature_csv(path)
        candles = validate_interval_window(
            [row.candle for row in feature_rows], interval, start_ms, end_ms
        )
        result = run_trend_backtest(candles, config, trade_start_time_ms=trade_start_time_ms)
        metadata = {
            "symbol": symbol,
            "interval": interval,
            "start_ms": start_ms,
            "end_ms": end_ms,
            "candle_count": len(candles),
            "ablation_arm": "candle_only",
            "orderflow_features_consumed": [],
        }
        return BacktestExecution(
            adapter_name=self.name,
            adapter_version=self.version,
            metrics=_result_metrics(result),
            resolved_config=_resolved_trend_config(config, trade_start_time_ms),
            dataset_metadata=metadata,
            source_files=(
                Path(__file__),
                Path(backtest_module.__file__),
                Path(history_module.__file__),
                Path(holdout_guard_module.__file__),
                Path(orderflow_feature_dataset_module.__file__),
            ),
        )


class EmaOrderFlowV1Adapter:
    """EMA crossover with causal closed-footprint gates at candidate entry bar open."""

    name = "ema_orderflow_v1"
    version = "1"
    _CONFIG_FIELDS = EmaTrendV1Adapter._CONFIG_FIELDS | {
        "delta_ratio_threshold",
        "cvd_threshold",
        "stacked_imbalance_threshold",
    }

    def run(
        self,
        *,
        dataset_path: str | Path,
        strategy_spec: Mapping[str, Any],
        experiment_parameters: Mapping[str, Any],
        stage: str,
        allow_frozen_oos: bool = False,
    ) -> BacktestExecution:
        _, symbol, interval, start_ms, end_ms, merged = _parse_dataset_spec(
            strategy_spec,
            adapter_name=self.name,
            config_fields=self._CONFIG_FIELDS,
            experiment_parameters=experiment_parameters,
            stage=stage,
            allow_frozen_oos=allow_frozen_oos,
        )
        config, trade_start_time_ms = _resolve_trend_config(merged)
        has_delta = "delta_ratio_threshold" in merged
        has_cvd = "cvd_threshold" in merged
        has_stacked = "stacked_imbalance_threshold" in merged
        if not has_delta and not has_cvd and not has_stacked:
            raise ValueError(
                "order-flow adapter requires delta_ratio_threshold, cvd_threshold, "
                "or stacked_imbalance_threshold"
            )
        delta_threshold = (
            _as_float(merged["delta_ratio_threshold"], name="delta_ratio_threshold")
            if has_delta
            else None
        )
        cvd_threshold = (
            _as_float(merged["cvd_threshold"], name="cvd_threshold") if has_cvd else None
        )
        stacked_threshold = (
            _as_int(merged["stacked_imbalance_threshold"], name="stacked_imbalance_threshold")
            if has_stacked
            else None
        )
        if stacked_threshold is not None and stacked_threshold < 1:
            raise ValueError("stacked_imbalance_threshold must be >= 1")

        path = Path(dataset_path)
        if stacked_threshold is not None:
            _require_stacked_columns(path)
        feature_rows = load_orderflow_feature_csv(path)
        candles = validate_interval_window(
            [row.candle for row in feature_rows], interval, start_ms, end_ms
        )
        by_open = {row.candle.open_time_ms: row for row in feature_rows}

        def entry_filter(open_time_ms: int) -> bool:
            try:
                row = by_open[open_time_ms]
            except KeyError as exc:
                raise RuntimeError("missing causal order-flow row at candidate entry") from exc
            if row.footprint_available_at_ms != open_time_ms:
                raise RuntimeError("order-flow feature is not available at candidate entry")
            if delta_threshold is not None and row.of_delta_ratio < delta_threshold:
                return False
            if cvd_threshold is not None and row.of_cvd < cvd_threshold:
                return False
            return stacked_threshold is None or row.of_stacked_imbalance >= stacked_threshold

        result = run_trend_backtest(
            candles,
            config,
            trade_start_time_ms=trade_start_time_ms,
            entry_filter=entry_filter,
        )
        resolved = _resolved_trend_config(config, trade_start_time_ms)
        resolved.update(
            {
                "delta_ratio_threshold": delta_threshold,
                "cvd_threshold": cvd_threshold,
                "stacked_imbalance_threshold": stacked_threshold,
            }
        )
        consumed = []
        if delta_threshold is not None:
            consumed.append("of_delta_ratio")
        if cvd_threshold is not None:
            consumed.append("of_cvd")
        if stacked_threshold is not None:
            consumed.append("of_stacked_imbalance")
        metadata = {
            "symbol": symbol,
            "interval": interval,
            "start_ms": start_ms,
            "end_ms": end_ms,
            "candle_count": len(candles),
            "ablation_arm": "candle_plus_orderflow",
            "orderflow_features_consumed": consumed,
        }
        return BacktestExecution(
            adapter_name=self.name,
            adapter_version=self.version,
            metrics=_result_metrics(result),
            resolved_config=resolved,
            dataset_metadata=metadata,
            source_files=(
                Path(__file__),
                Path(backtest_module.__file__),
                Path(history_module.__file__),
                Path(holdout_guard_module.__file__),
                Path(orderflow_feature_dataset_module.__file__),
            ),
        )


class BacktestAdapterRegistry:
    def __init__(self, adapters: tuple[BacktestAdapter, ...] = ()) -> None:
        self._adapters: dict[str, BacktestAdapter] = {}
        for adapter in adapters:
            self.register(adapter)

    @classmethod
    def default(cls) -> BacktestAdapterRegistry:
        return cls(
            (
                EmaTrendV1Adapter(),
                EmaFeatureBaselineV1Adapter(),
                EmaOrderFlowV1Adapter(),
            )
        )

    def register(self, adapter: BacktestAdapter) -> None:
        name = adapter.name.strip()
        if not name:
            raise ValueError("adapter name is required")
        if name in self._adapters:
            raise ValueError(f"adapter already registered: {name}")
        self._adapters[name] = adapter

    def get(self, name: str) -> BacktestAdapter:
        try:
            return self._adapters[name]
        except KeyError as exc:
            raise KeyError(f"Unsupported backtest adapter: {name}") from exc
