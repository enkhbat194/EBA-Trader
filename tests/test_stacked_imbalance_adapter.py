from __future__ import annotations

import csv
from pathlib import Path

import pytest

from eba_trader.backtest_adapter import EmaFeatureBaselineV1Adapter, EmaOrderFlowV1Adapter
from eba_trader.history import Candle
from eba_trader.m5_features import DEFAULT_FEATURE_REGISTRY, FeatureFamily
from eba_trader.orderflow_feature_dataset import (
    OrderFlowFeatureRow,
    _write_feature_csv,
    load_orderflow_feature_csv,
)

STEP_MS = 60_000


def _series(stacked: int) -> tuple[OrderFlowFeatureRow, ...]:
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
                of_delta_ratio=0.2,
                of_cvd=100.0,
                of_poc_price=price,
                footprint_available_at_ms=open_ms,
                of_stacked_buy_levels=max(stacked, 0),
                of_stacked_sell_levels=max(-stacked, 0),
                of_stacked_imbalance=stacked,
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


def _write(tmp_path: Path, stacked: int) -> Path:
    path = tmp_path / "features-v4.csv"
    _write_feature_csv(_series(stacked), path)
    return path


def test_orderflow_research_features_are_enabled_but_lob_remains_locked() -> None:
    for name in (
        "of_stacked_imbalance",
        "of_absorption",
        "of_exhaustion",
        "of_price_delta_divergence",
    ):
        feature = DEFAULT_FEATURE_REGISTRY.require(name)
        assert feature.family is FeatureFamily.ORDER_FLOW
    with pytest.raises(ValueError, match="not enabled"):
        DEFAULT_FEATURE_REGISTRY.require("lob_depth_imbalance")


def test_v4_feature_csv_round_trips_stacked_fields(tmp_path: Path) -> None:
    path = _write(tmp_path, 3)

    rows = load_orderflow_feature_csv(path)

    assert rows[0].of_stacked_buy_levels == 3
    assert rows[0].of_stacked_sell_levels == 0
    assert rows[0].of_stacked_imbalance == 3
    assert rows[0].footprint_available_at_ms == rows[0].candle.open_time_ms


def test_permissive_stacked_gate_matches_same_dataset_baseline(tmp_path: Path) -> None:
    path = _write(tmp_path, 3)
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
        experiment_parameters={**common, "stacked_imbalance_threshold": 1},
        stage="development",
    )

    assert treatment.metrics == baseline.metrics
    assert treatment.dataset_metadata["orderflow_features_consumed"] == [
        "of_stacked_imbalance"
    ]


def test_non_bullish_stacked_gate_rejects_entries(tmp_path: Path) -> None:
    path = _write(tmp_path, -3)
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
        experiment_parameters={**common, "stacked_imbalance_threshold": 1},
        stage="development",
    )

    assert baseline.metrics["trade_count"] >= 1
    assert treatment.metrics["trade_count"] == 0


@pytest.mark.parametrize("threshold", [0, -1, 1.5, True])
def test_invalid_stacked_threshold_fails_closed(tmp_path: Path, threshold: object) -> None:
    path = _write(tmp_path, 3)
    with pytest.raises(ValueError, match="stacked_imbalance_threshold"):
        EmaOrderFlowV1Adapter().run(
            dataset_path=path,
            strategy_spec=_spec("ema_orderflow_v1"),
            experiment_parameters={
                "fast_ema": 5,
                "slow_ema": 15,
                "stacked_imbalance_threshold": threshold,
            },
            stage="development",
        )


def test_stacked_gate_rejects_legacy_csv_without_stacked_columns(tmp_path: Path) -> None:
    v4_path = _write(tmp_path, 3)
    with v4_path.open("r", newline="", encoding="utf-8") as source:
        reader = csv.DictReader(source)
        payloads = list(reader)
        fields = [
            name
            for name in (reader.fieldnames or [])
            if name
            not in {
                "of_stacked_buy_levels",
                "of_stacked_sell_levels",
                "of_stacked_imbalance",
                "of_absorption",
                "of_exhaustion",
                "of_bullish_price_delta_divergence",
                "of_bearish_price_delta_divergence",
                "of_price_delta_divergence",
            }
        ]
    legacy_path = tmp_path / "features-v1.csv"
    with legacy_path.open("w", newline="", encoding="utf-8") as target:
        writer = csv.DictWriter(target, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(payloads)

    legacy_rows = load_orderflow_feature_csv(legacy_path)
    assert legacy_rows[0].of_stacked_imbalance == 0

    with pytest.raises(ValueError, match="v2 feature CSV"):
        EmaOrderFlowV1Adapter().run(
            dataset_path=legacy_path,
            strategy_spec=_spec("ema_orderflow_v1"),
            experiment_parameters={
                "fast_ema": 5,
                "slow_ema": 15,
                "stacked_imbalance_threshold": 1,
            },
            stage="development",
        )


def test_noncausal_stacked_feature_row_is_rejected(tmp_path: Path) -> None:
    rows = list(_series(3))
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
        of_stacked_buy_levels=first.of_stacked_buy_levels,
        of_stacked_sell_levels=first.of_stacked_sell_levels,
        of_stacked_imbalance=first.of_stacked_imbalance,
    )
    path = tmp_path / "noncausal-v4.csv"
    _write_feature_csv(tuple(rows), path)

    with pytest.raises(ValueError, match="availability"):
        EmaOrderFlowV1Adapter().run(
            dataset_path=path,
            strategy_spec=_spec("ema_orderflow_v1"),
            experiment_parameters={
                "fast_ema": 5,
                "slow_ema": 15,
                "stacked_imbalance_threshold": 1,
            },
            stage="development",
        )
