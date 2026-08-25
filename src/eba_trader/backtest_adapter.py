from __future__ import annotations

import math
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

from . import backtest as backtest_module
from . import history as history_module
from . import holdout_guard as holdout_guard_module
from .backtest import BacktestResult, TrendBacktestConfig, run_trend_backtest
from .history import load_csv, validate_interval_window
from .holdout_guard import assert_not_first_cycle_oos_overlap


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
        "annualized_return": result.annualized_return,
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
    return float(value)


class EmaTrendV1Adapter:
    """Adapter from an immutable research spec to the existing EMA baseline backtester."""

    name = "ema_trend_v1"
    version = "1"

    _SPEC_FIELDS = {"adapter", "fixed", "dataset"}
    _DATASET_FIELDS = {"symbol", "interval", "start_ms", "end_ms"}
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
        _reject_unknown(strategy_spec, self._SPEC_FIELDS, name="strategy spec")
        if strategy_spec.get("adapter") != self.name:
            raise ValueError(f"Strategy spec adapter must be {self.name!r}")

        fixed = _require_mapping(strategy_spec.get("fixed", {}), name="strategy fixed config")
        dataset = _require_mapping(strategy_spec.get("dataset"), name="strategy dataset")
        _reject_unknown(fixed, self._CONFIG_FIELDS, name="fixed config")
        _reject_unknown(dataset, self._DATASET_FIELDS, name="dataset")
        _reject_unknown(experiment_parameters, self._CONFIG_FIELDS, name="experiment parameter")

        overlap = sorted(set(fixed) & set(experiment_parameters))
        if overlap:
            raise ValueError(
                "Experiment parameters cannot override immutable fixed fields: " + ", ".join(overlap)
            )

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

        merged = {**fixed, **experiment_parameters}
        config_kwargs: dict[str, Any] = {}
        if "fast_ema" in merged:
            config_kwargs["fast_ema"] = _as_int(merged["fast_ema"], name="fast_ema")
        if "slow_ema" in merged:
            config_kwargs["slow_ema"] = _as_int(merged["slow_ema"], name="slow_ema")
        if "initial_cash" in merged:
            config_kwargs["initial_cash"] = _as_float(
                merged["initial_cash"], name="initial_cash"
            )
        if "fee_bps" in merged:
            config_kwargs["fee_bps"] = _as_float(merged["fee_bps"], name="fee_bps")
        if "slippage_bps" in merged:
            config_kwargs["slippage_bps"] = _as_float(
                merged["slippage_bps"], name="slippage_bps"
            )

        trade_start_time_ms = None
        if "trade_start_time_ms" in merged:
            trade_start_time_ms = _as_int(
                merged["trade_start_time_ms"], name="trade_start_time_ms"
            )

        config = TrendBacktestConfig(**config_kwargs)
        path = Path(dataset_path)
        candles = validate_interval_window(
            load_csv(path),
            interval,
            start_ms,
            end_ms,
        )
        result = run_trend_backtest(
            candles,
            config,
            trade_start_time_ms=trade_start_time_ms,
        )

        resolved_config = {
            "fast_ema": config.fast_ema,
            "slow_ema": config.slow_ema,
            "initial_cash": config.initial_cash,
            "fee_bps": config.fee_bps,
            "slippage_bps": config.slippage_bps,
            "trade_start_time_ms": trade_start_time_ms,
        }
        dataset_metadata = {
            "symbol": symbol,
            "interval": interval,
            "start_ms": start_ms,
            "end_ms": end_ms,
            "candle_count": len(candles),
        }
        return BacktestExecution(
            adapter_name=self.name,
            adapter_version=self.version,
            metrics=_result_metrics(result),
            resolved_config=resolved_config,
            dataset_metadata=dataset_metadata,
            source_files=(
                Path(__file__),
                Path(backtest_module.__file__),
                Path(history_module.__file__),
                Path(holdout_guard_module.__file__),
            ),
        )


class BacktestAdapterRegistry:
    def __init__(self, adapters: tuple[BacktestAdapter, ...] = ()) -> None:
        self._adapters: dict[str, BacktestAdapter] = {}
        for adapter in adapters:
            self.register(adapter)

    @classmethod
    def default(cls) -> BacktestAdapterRegistry:
        return cls((EmaTrendV1Adapter(),))

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
