from __future__ import annotations

import csv
from dataclasses import replace
from pathlib import Path

import pytest

from eba_trader.backtest_adapter import EmaFeatureBaselineV1Adapter, EmaOrderFlowV1Adapter
from eba_trader.history import Candle
from eba_trader.m5_ablation import OrderFlowGate
from eba_trader.m5_features import DEFAULT_FEATURE_REGISTRY, FeatureFamily
from eba_trader.orderflow_feature_dataset import (
    OrderFlowFeatureRow,
    _write_feature_csv,
    apply_price_delta_divergence,
)

STEP_MS = 60_000


def _candle(index: int, *, high: float, low: float, close: float) -> Candle:
    open_ms = index * STEP_MS
    return Candle(
        open_time_ms=open_ms,
        open=close,
        high=high,
        low=low,
        close=close,
        volume=100.0,
        close_time_ms=open_ms + STEP_MS - 1,
        quote_volume=10_000.0,
        trade_count=100,
    )


def _row(
    index: int,
    *,
    high: float,
    low: float,
    delta_ratio: float,
    divergence: float = 0.0,
) -> OrderFlowFeatureRow:
    return OrderFlowFeatureRow(
        candle=_candle(index, high=high, low=low, close=(high + low) / 2.0),
        of_buy_volume=50.0 * (1.0 + delta_ratio),
        of_sell_volume=50.0 * (1.0 - delta_ratio),
        of_delta=100.0 * delta_ratio,
        of_delta_ratio=delta_ratio,
        of_cvd=0.0,
        of_poc_price=(high + low) / 2.0,
        footprint_available_at_ms=index * STEP_MS,
        of_price_delta_divergence=divergence,
        of_bullish_price_delta_divergence=max(0.0, divergence),
        of_bearish_price_delta_divergence=max(0.0, -divergence),
    )


def test_materialized_divergence_uses_only_already_closed_price_bar() -> None:
    rows = (
        _row(0, high=102.0, low=98.0, delta_ratio=-0.4),
        _row(1, high=101.0, low=97.0, delta_ratio=-0.5),
        _row(2, high=100.0, low=95.0, delta_ratio=-0.8),
        _row(3, high=101.0, low=99.0, delta_ratio=-0.1),
        _row(4, high=102.0, low=100.0, delta_ratio=0.0),
    )

    first = apply_price_delta_divergence(rows, lookback=2)
    mutated = list(rows)
    mutated[3] = replace(
        mutated[3],
        candle=_candle(3, high=10_000.0, low=1.0, close=5_000.0),
    )
    second = apply_price_delta_divergence(tuple(mutated), lookback=2)

    assert first[0].of_price_delta_divergence == 0.0
    assert first[1].of_price_delta_divergence == 0.0
    assert first[2].of_price_delta_divergence == 0.0
    assert first[3].of_price_delta_divergence > 0.0
    assert second[3].of_price_delta_divergence == first[3].of_price_delta_divergence


def test_materialized_divergence_requires_minimum_activity() -> None:
    rows = [
        _row(0, high=102.0, low=98.0, delta_ratio=-0.4),
        _row(1, high=101.0, low=97.0, delta_ratio=-0.5),
        _row(2, high=100.0, low=95.0, delta_ratio=-0.8),
        _row(3, high=101.0, low=99.0, delta_ratio=-0.1),
    ]
    rows[3] = replace(rows[3], of_buy_volume=0.0, of_sell_volume=0.0, of_delta=0.0)

    materialized = apply_price_delta_divergence(
        tuple(rows),
        lookback=2,
        min_total_volume=0.0,
    )

    assert materialized[3].of_price_delta_divergence == 0.0


def _series(*, divergence: float) -> tuple[OrderFlowFeatureRow, ...]:
    rows: list[OrderFlowFeatureRow] = []
    price = 100.0
    for index in range(140):
        if index < 40:
            price -= 0.20
        elif index < 95:
            price += 0.80
        else:
            price -= 0.70
        rows.append(
            _row(
                index,
                high=price + 0.6,
                low=price - 0.8,
                delta_ratio=-0.2,
                divergence=divergence,
            )
        )
    return tuple(rows)


def _spec(adapter: str) -> dict[str, object]:
    return {
        "adapter": adapter,
        "fixed": {"initial_cash": 1000.0, "fee_bps": 0.0, "slippage_bps": 0.0},
        "dataset": {
            "symbol": "BTCUSDT",
            "interval": "1m",
            "start_ms": 0,
            "end_ms": 140 * STEP_MS,
        },
    }


def _write(tmp_path: Path, *, divergence: float) -> Path:
    path = tmp_path / "features-v4.csv"
    _write_feature_csv(_series(divergence=divergence), path)
    return path


def test_permissive_divergence_gate_matches_same_dataset_baseline(tmp_path: Path) -> None:
    path = _write(tmp_path, divergence=0.5)
    common = {"fast_ema": 5, "slow_ema": 15}
    baseline = EmaFeatureBaselineV1Adapter().run(
        dataset_path=path,
        strategy_spec=_spec("ema_feature_baseline_v1"),
        experiment_parameters=common,
        stage="development",
    )
    treatment = EmaOrderFlowV1Adapter().run(
        dataset_path=path,
        strategy_spec=_spec("ema_orderflow_v1"),
        experiment_parameters={
            **common,
            "price_delta_divergence_threshold": 0.2,
        },
        stage="development",
    )

    assert treatment.metrics == baseline.metrics
    assert treatment.dataset_metadata["orderflow_features_consumed"] == [
        "of_price_delta_divergence"
    ]


def test_non_bullish_divergence_gate_rejects_long_entries(tmp_path: Path) -> None:
    path = _write(tmp_path, divergence=-0.5)
    treatment = EmaOrderFlowV1Adapter().run(
        dataset_path=path,
        strategy_spec=_spec("ema_orderflow_v1"),
        experiment_parameters={
            "fast_ema": 5,
            "slow_ema": 15,
            "price_delta_divergence_threshold": 0.2,
        },
        stage="development",
    )

    assert treatment.metrics["trade_count"] == 0


@pytest.mark.parametrize("value", [0.0, -0.1, 1.1, float("inf")])
def test_invalid_divergence_threshold_fails_closed(tmp_path: Path, value: float) -> None:
    path = _write(tmp_path, divergence=0.5)
    with pytest.raises(ValueError, match="price_delta_divergence_threshold"):
        EmaOrderFlowV1Adapter().run(
            dataset_path=path,
            strategy_spec=_spec("ema_orderflow_v1"),
            experiment_parameters={
                "fast_ema": 5,
                "slow_ema": 15,
                "price_delta_divergence_threshold": value,
            },
            stage="development",
        )


def test_divergence_gate_rejects_v3_csv_without_physical_divergence_columns(
    tmp_path: Path,
) -> None:
    v4_path = _write(tmp_path, divergence=0.5)
    with v4_path.open("r", newline="", encoding="utf-8") as source:
        reader = csv.DictReader(source)
        payloads = list(reader)
        fields = [
            name
            for name in (reader.fieldnames or [])
            if name
            not in {
                "of_bullish_price_delta_divergence",
                "of_bearish_price_delta_divergence",
                "of_price_delta_divergence",
            }
        ]
    v3_path = tmp_path / "features-v3.csv"
    with v3_path.open("w", newline="", encoding="utf-8") as target:
        writer = csv.DictWriter(target, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(payloads)

    with pytest.raises(ValueError, match="v4 feature CSV"):
        EmaOrderFlowV1Adapter().run(
            dataset_path=v3_path,
            strategy_spec=_spec("ema_orderflow_v1"),
            experiment_parameters={
                "fast_ema": 5,
                "slow_ema": 15,
                "price_delta_divergence_threshold": 0.2,
            },
            stage="development",
        )


def test_ablation_gate_and_feature_registry_accept_divergence_deterministically() -> None:
    first = OrderFlowGate(price_delta_divergence_threshold=0.05)
    second = OrderFlowGate(price_delta_divergence_threshold=0.05)

    assert first.parameters() == {"price_delta_divergence_threshold": 0.05}
    assert first.gate_id == second.gate_id
    feature = DEFAULT_FEATURE_REGISTRY.require("of_price_delta_divergence")
    assert feature.family is FeatureFamily.ORDER_FLOW


@pytest.mark.parametrize("value", [0.0, -0.1, 1.1])
def test_ablation_gate_rejects_unbounded_divergence_thresholds(value: float) -> None:
    with pytest.raises(ValueError, match="price_delta_divergence_threshold"):
        OrderFlowGate(price_delta_divergence_threshold=value).parameters()
