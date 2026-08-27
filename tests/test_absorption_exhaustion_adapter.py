from __future__ import annotations

import csv
from pathlib import Path

import pytest

from eba_trader.backtest_adapter import EmaFeatureBaselineV1Adapter, EmaOrderFlowV1Adapter
from eba_trader.history import Candle
from eba_trader.m5_ablation import OrderFlowGate
from eba_trader.orderflow_feature_dataset import OrderFlowFeatureRow, _write_feature_csv

STEP_MS = 60_000


def _series(*, absorption: float, exhaustion: float) -> tuple[OrderFlowFeatureRow, ...]:
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
        rows.append(
            OrderFlowFeatureRow(
                candle=Candle(
                    open_time_ms=open_ms,
                    open=price - 0.2,
                    high=price + 0.6,
                    low=price - 0.8,
                    close=price,
                    volume=100.0,
                    close_time_ms=open_ms + STEP_MS - 1,
                    quote_volume=10_000.0,
                    trade_count=100,
                ),
                of_buy_volume=40.0,
                of_sell_volume=60.0,
                of_delta=-20.0,
                of_delta_ratio=-0.2,
                of_cvd=-100.0,
                of_poc_price=price,
                footprint_available_at_ms=open_ms,
                of_absorption=absorption,
                of_exhaustion=exhaustion,
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


def _write(tmp_path: Path, *, absorption: float, exhaustion: float) -> Path:
    path = tmp_path / "features-v3.csv"
    _write_feature_csv(_series(absorption=absorption, exhaustion=exhaustion), path)
    return path


@pytest.mark.parametrize(
    ("parameter", "value", "consumed"),
    [
        ("absorption_threshold", 0.2, "of_absorption"),
        ("exhaustion_threshold", 0.05, "of_exhaustion"),
    ],
)
def test_permissive_response_gate_matches_same_dataset_baseline(
    tmp_path: Path,
    parameter: str,
    value: float,
    consumed: str,
) -> None:
    path = _write(tmp_path, absorption=0.5, exhaustion=0.2)
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
        experiment_parameters={**common, parameter: value},
        stage="development",
    )

    assert treatment.metrics == baseline.metrics
    assert treatment.dataset_metadata["orderflow_features_consumed"] == [consumed]


@pytest.mark.parametrize(
    ("parameter", "value"),
    [
        ("absorption_threshold", 0.2),
        ("exhaustion_threshold", 0.05),
    ],
)
def test_non_bullish_response_gate_rejects_entries(
    tmp_path: Path,
    parameter: str,
    value: float,
) -> None:
    path = _write(tmp_path, absorption=-0.5, exhaustion=-0.2)
    treatment = EmaOrderFlowV1Adapter().run(
        dataset_path=path,
        strategy_spec=_spec("ema_orderflow_v1"),
        experiment_parameters={"fast_ema": 5, "slow_ema": 15, parameter: value},
        stage="development",
    )

    assert treatment.metrics["trade_count"] == 0


@pytest.mark.parametrize(
    ("parameter", "value"),
    [
        ("absorption_threshold", 0.0),
        ("absorption_threshold", -0.1),
        ("absorption_threshold", 1.1),
        ("exhaustion_threshold", 0.0),
        ("exhaustion_threshold", 2.0),
        ("exhaustion_threshold", float("inf")),
    ],
)
def test_invalid_response_threshold_fails_closed(
    tmp_path: Path,
    parameter: str,
    value: float,
) -> None:
    path = _write(tmp_path, absorption=0.5, exhaustion=0.2)
    with pytest.raises(ValueError, match=parameter):
        EmaOrderFlowV1Adapter().run(
            dataset_path=path,
            strategy_spec=_spec("ema_orderflow_v1"),
            experiment_parameters={"fast_ema": 5, "slow_ema": 15, parameter: value},
            stage="development",
        )


def test_response_gate_rejects_v2_csv_without_physical_response_columns(tmp_path: Path) -> None:
    v3_path = _write(tmp_path, absorption=0.5, exhaustion=0.2)
    with v3_path.open("r", newline="", encoding="utf-8") as source:
        reader = csv.DictReader(source)
        payloads = list(reader)
        fields = [
            name
            for name in (reader.fieldnames or [])
            if name not in {"of_absorption", "of_exhaustion"}
        ]
    v2_path = tmp_path / "features-v2.csv"
    with v2_path.open("w", newline="", encoding="utf-8") as target:
        writer = csv.DictWriter(target, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(payloads)

    with pytest.raises(ValueError, match="v3 feature CSV"):
        EmaOrderFlowV1Adapter().run(
            dataset_path=v2_path,
            strategy_spec=_spec("ema_orderflow_v1"),
            experiment_parameters={
                "fast_ema": 5,
                "slow_ema": 15,
                "absorption_threshold": 0.2,
            },
            stage="development",
        )


def test_ablation_gate_accepts_bounded_response_parameters_deterministically() -> None:
    first = OrderFlowGate(absorption_threshold=0.2, exhaustion_threshold=0.05)
    second = OrderFlowGate(absorption_threshold=0.2, exhaustion_threshold=0.05)

    assert first.parameters() == {
        "absorption_threshold": 0.2,
        "exhaustion_threshold": 0.05,
    }
    assert first.gate_id == second.gate_id


@pytest.mark.parametrize("value", [0.0, -0.1, 1.1])
def test_ablation_gate_rejects_unbounded_response_thresholds(value: float) -> None:
    with pytest.raises(ValueError, match="absorption_threshold"):
        OrderFlowGate(absorption_threshold=value).parameters()
