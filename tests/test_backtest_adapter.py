from pathlib import Path

import pytest

from eba_trader.backtest_adapter import BacktestAdapterRegistry, EmaTrendV1Adapter
from eba_trader.history import INTERVAL_MS, Candle, save_csv
from eba_trader.holdout_guard import FIRST_CYCLE_OOS_START_MS


def _write_dataset(
    tmp_path: Path,
    *,
    start_ms: int = 1_704_067_200_000,
    count: int = 80,
) -> tuple[Path, int, int]:
    step = INTERVAL_MS["15m"]
    candles: list[Candle] = []
    previous_close = 100.0
    for index in range(count):
        open_price = previous_close
        cycle = index % 24
        drift = 1.25 if cycle < 12 else -1.0
        close_price = max(10.0, open_price + drift)
        open_time = start_ms + index * step
        candles.append(
            Candle(
                open_time_ms=open_time,
                open=open_price,
                high=max(open_price, close_price) + 0.5,
                low=min(open_price, close_price) - 0.5,
                close=close_price,
                volume=100.0 + index,
                close_time_ms=open_time + step - 1,
                quote_volume=(100.0 + index) * close_price,
                trade_count=100 + index,
            )
        )
        previous_close = close_price
    path = save_csv(candles, tmp_path / "btc_15m.csv")
    return path, start_ms, start_ms + count * step


def _spec(start_ms: int, end_ms: int) -> dict[str, object]:
    return {
        "adapter": "ema_trend_v1",
        "fixed": {"initial_cash": 1_000.0},
        "dataset": {
            "symbol": "BTCUSDT",
            "interval": "15m",
            "start_ms": start_ms,
            "end_ms": end_ms,
        },
    }


def test_ema_adapter_runs_existing_backtester_with_exact_dataset_gate(tmp_path: Path) -> None:
    path, start_ms, end_ms = _write_dataset(tmp_path)
    execution = EmaTrendV1Adapter().run(
        dataset_path=path,
        strategy_spec=_spec(start_ms, end_ms),
        experiment_parameters={
            "fast_ema": 3,
            "slow_ema": 8,
            "fee_bps": 1.0,
            "slippage_bps": 1.0,
        },
        stage="development_backtest",
    )

    assert execution.adapter_name == "ema_trend_v1"
    assert execution.adapter_version == "1"
    assert execution.dataset_metadata["candle_count"] == 80
    assert execution.resolved_config["fast_ema"] == 3
    assert execution.resolved_config["slow_ema"] == 8
    assert execution.metrics["trade_count"] >= 1
    assert execution.metrics["final_equity"] > 0
    assert len(execution.source_files) >= 4


def test_adapter_rejects_unknown_fields_and_fixed_overrides(tmp_path: Path) -> None:
    path, start_ms, end_ms = _write_dataset(tmp_path)
    spec = _spec(start_ms, end_ms)
    spec["mystery"] = True
    with pytest.raises(ValueError, match="Unsupported strategy spec fields"):
        EmaTrendV1Adapter().run(
            dataset_path=path,
            strategy_spec=spec,
            experiment_parameters={"fast_ema": 3, "slow_ema": 8},
            stage="development_backtest",
        )

    fixed_spec = _spec(start_ms, end_ms)
    fixed_spec["fixed"] = {"fast_ema": 3}
    with pytest.raises(ValueError, match="cannot override immutable fixed fields"):
        EmaTrendV1Adapter().run(
            dataset_path=path,
            strategy_spec=fixed_spec,
            experiment_parameters={"fast_ema": 4, "slow_ema": 8},
            stage="development_backtest",
        )


def test_adapter_blocks_frozen_oos_by_default(tmp_path: Path) -> None:
    step = INTERVAL_MS["15m"]
    start_ms = FIRST_CYCLE_OOS_START_MS
    end_ms = start_ms + 80 * step
    with pytest.raises(RuntimeError, match="frozen first-cycle"):
        EmaTrendV1Adapter().run(
            dataset_path=tmp_path / "does-not-need-to-exist.csv",
            strategy_spec=_spec(start_ms, end_ms),
            experiment_parameters={"fast_ema": 3, "slow_ema": 8},
            stage="development_backtest",
        )


def test_registry_is_fail_closed_for_unknown_adapter() -> None:
    registry = BacktestAdapterRegistry.default()
    assert registry.get("ema_trend_v1").name == "ema_trend_v1"
    with pytest.raises(KeyError, match="Unsupported backtest adapter"):
        registry.get("unknown")
