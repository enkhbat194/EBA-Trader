from pathlib import Path

import pytest

from eba_trader.backtest_adapter import (
    BacktestAdapterRegistry,
    EmaFeatureBaselineV1Adapter,
    EmaOrderFlowV1Adapter,
)
from eba_trader.history import Candle
from eba_trader.orderflow_feature_dataset import OrderFlowFeatureRow, _write_feature_csv

STEP_MS = 60_000


def _series(delta_ratio: float, cvd: float) -> tuple[OrderFlowFeatureRow, ...]:
    rows: list[OrderFlowFeatureRow] = []
    price = 100.0
    for index in range(140):
        if index < 40:
            price -= 0.20
        elif index < 95:
            price += 0.80
        else:
            price -= 0.70
        open_ms = index * STEP_MS
        candle = Candle(
            open_time_ms=open_ms,
            open=price - 0.2,
            high=price + 0.6,
            low=price - 0.8,
            close=price,
            volume=100.0,
            close_time_ms=open_ms + STEP_MS - 1,
            quote_volume=10_000.0,
            trade_count=100,
        )
        rows.append(
            OrderFlowFeatureRow(
                candle=candle,
                of_buy_volume=60.0,
                of_sell_volume=40.0,
                of_delta=20.0,
                of_delta_ratio=delta_ratio,
                of_cvd=cvd,
                of_poc_price=price,
                footprint_available_at_ms=open_ms,
            )
        )
    return tuple(rows)


def _spec(adapter: str) -> dict[str, object]:
    return {
        "adapter": adapter,
        "fixed": {
            "initial_cash": 1000.0,
            "fee_bps": 0.0,
            "slippage_bps": 0.0,
        },
        "dataset": {
            "symbol": "BTCUSDT",
            "interval": "1m",
            "start_ms": 0,
            "end_ms": 140 * STEP_MS,
        },
    }


def _write(tmp_path: Path, *, delta_ratio: float, cvd: float) -> Path:
    path = tmp_path / "features.csv"
    _write_feature_csv(_series(delta_ratio, cvd), path)
    return path


def test_registry_allowlists_both_ablation_adapters() -> None:
    registry = BacktestAdapterRegistry.default()
    assert registry.get("ema_feature_baseline_v1").name == "ema_feature_baseline_v1"
    assert registry.get("ema_orderflow_v1").name == "ema_orderflow_v1"


def test_permissive_orderflow_gate_matches_same_dataset_baseline(tmp_path: Path) -> None:
    path = _write(tmp_path, delta_ratio=0.5, cvd=100.0)
    common = {"fast_ema": 5, "slow_ema": 15}
    baseline = EmaFeatureBaselineV1Adapter().run(
        dataset_path=path,
        strategy_spec=_spec("ema_feature_baseline_v1"),
        experiment_parameters=common,
        stage="development",
    )
    filtered = EmaOrderFlowV1Adapter().run(
        dataset_path=path,
        strategy_spec=_spec("ema_orderflow_v1"),
        experiment_parameters={**common, "delta_ratio_threshold": 0.1},
        stage="development",
    )

    assert baseline.metrics == filtered.metrics
    assert baseline.dataset_metadata["ablation_arm"] == "candle_only"
    assert filtered.dataset_metadata["orderflow_features_consumed"] == ["of_delta_ratio"]


def test_negative_delta_filter_rejects_ema_cross_entry(tmp_path: Path) -> None:
    path = _write(tmp_path, delta_ratio=-0.5, cvd=-100.0)
    common = {"fast_ema": 5, "slow_ema": 15}
    baseline = EmaFeatureBaselineV1Adapter().run(
        dataset_path=path,
        strategy_spec=_spec("ema_feature_baseline_v1"),
        experiment_parameters=common,
        stage="development",
    )
    filtered = EmaOrderFlowV1Adapter().run(
        dataset_path=path,
        strategy_spec=_spec("ema_orderflow_v1"),
        experiment_parameters={**common, "delta_ratio_threshold": 0.1},
        stage="development",
    )

    assert baseline.metrics["trade_count"] >= 1
    assert filtered.metrics["trade_count"] == 0


def test_cvd_gate_is_consumed_when_requested(tmp_path: Path) -> None:
    path = _write(tmp_path, delta_ratio=0.5, cvd=-10.0)
    execution = EmaOrderFlowV1Adapter().run(
        dataset_path=path,
        strategy_spec=_spec("ema_orderflow_v1"),
        experiment_parameters={
            "fast_ema": 5,
            "slow_ema": 15,
            "delta_ratio_threshold": 0.1,
            "cvd_threshold": 0.0,
        },
        stage="development",
    )
    assert execution.metrics["trade_count"] == 0
    assert execution.dataset_metadata["orderflow_features_consumed"] == [
        "of_delta_ratio",
        "of_cvd",
    ]


def test_orderflow_adapter_requires_a_real_orderflow_gate(tmp_path: Path) -> None:
    path = _write(tmp_path, delta_ratio=0.5, cvd=100.0)
    with pytest.raises(ValueError, match="requires"):
        EmaOrderFlowV1Adapter().run(
            dataset_path=path,
            strategy_spec=_spec("ema_orderflow_v1"),
            experiment_parameters={"fast_ema": 5, "slow_ema": 15},
            stage="development",
        )


def test_feature_csv_rejects_noncausal_availability(tmp_path: Path) -> None:
    rows = list(_series(0.5, 100.0))
    first = rows[0]
    rows[0] = OrderFlowFeatureRow(
        candle=first.candle,
        of_buy_volume=first.of_buy_volume,
        of_sell_volume=first.of_sell_volume,
        of_delta=first.of_delta,
        of_delta_ratio=first.of_delta_ratio,
        of_cvd=first.of_cvd,
        of_poc_price=first.of_poc_price,
        footprint_available_at_ms=first.candle.open_time_ms + 1,
    )
    path = tmp_path / "noncausal.csv"
    _write_feature_csv(tuple(rows), path)

    with pytest.raises(ValueError, match="availability"):
        EmaFeatureBaselineV1Adapter().run(
            dataset_path=path,
            strategy_spec=_spec("ema_feature_baseline_v1"),
            experiment_parameters={"fast_ema": 5, "slow_ema": 15},
            stage="development",
        )
