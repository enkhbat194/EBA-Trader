from __future__ import annotations

from pathlib import Path

import pytest

from eba_trader.candle_acquisition import (
    USDM_KLINES_URL,
    CandleVenue,
    load_candle_acquisition,
)
from eba_trader.history import parse_utc
from eba_trader.m5_dataset_workflow import build_usdm_orderflow_feature_dataset
from eba_trader.m5_study_policy import DEFAULT_M5_STUDY_POLICY
from eba_trader.orderflow_acquisition import USDM_AGG_TRADES_URL
from eba_trader.orderflow_feature_dataset import load_orderflow_feature_csv

STEP = 60_000
START = parse_utc("2026-08-01T00:00:00Z")
END = START + 3 * STEP


def _kline(open_ms: int, price: float) -> list[object]:
    return [
        open_ms,
        str(price),
        str(price + 10),
        str(price - 10),
        str(price + 1),
        "12.5",
        open_ms + STEP - 1,
        "1000000",
        50,
    ]


def _agg(trade_id: int, timestamp_ms: int, *, buyer_is_maker: bool) -> dict[str, object]:
    return {
        "a": trade_id,
        "p": "50000.0",
        "q": "0.25",
        "T": timestamp_ms,
        "m": buyer_is_maker,
    }


def _candle_request(calls: list[tuple[str, dict[str, object]]]):
    rows = [
        _kline(START, 50_000),
        _kline(START + STEP, 50_010),
        _kline(START + 2 * STEP, 50_020),
    ]

    def request(endpoint: str, params):
        calls.append((endpoint, dict(params)))
        return rows

    return request


def _orderflow_request(calls: list[tuple[str, dict[str, object]]]):
    rows = [
        _agg(100, START - STEP + 10_000, buyer_is_maker=False),
        _agg(101, START + 10_000, buyer_is_maker=True),
        _agg(102, START + STEP + 10_000, buyer_is_maker=False),
        _agg(103, START + 2 * STEP + 10_000, buyer_is_maker=True),
    ]

    def request(endpoint: str, params):
        calls.append((endpoint, dict(params)))
        return rows

    return request


def test_real_feature_workflow_is_usdm_causal_and_replay_deterministic(tmp_path) -> None:
    candle_calls: list[tuple[str, dict[str, object]]] = []
    orderflow_calls: list[tuple[str, dict[str, object]]] = []

    first, first_path = build_usdm_orderflow_feature_dataset(
        symbol="btcusdt",
        interval="1m",
        start_ms=START,
        end_ms=END,
        price_bucket=1.0,
        dataset_root=tmp_path,
        candle_request_json=_candle_request(candle_calls),
        orderflow_request_json=_orderflow_request(orderflow_calls),
    )
    second, second_path = build_usdm_orderflow_feature_dataset(
        symbol="BTCUSDT",
        interval="1m",
        start_ms=START,
        end_ms=END,
        price_bucket=1.0,
        dataset_root=tmp_path,
        candle_request_json=_candle_request([]),
        orderflow_request_json=_orderflow_request([]),
    )

    assert first == second
    assert first_path == second_path
    assert first.venue == CandleVenue.USD_M_FUTURES.value
    assert first.symbol == "BTCUSDT"
    assert first.study_policy_id == DEFAULT_M5_STUDY_POLICY.policy_id
    assert first.study_phase == "development"
    assert first.dataset_ref.startswith("m5_orderflow_dev/features/")
    assert not Path(first.dataset_ref).is_absolute()
    assert first_path.is_file()

    assert candle_calls[0][0] == USDM_KLINES_URL
    assert candle_calls[0][1]["startTime"] == START
    assert candle_calls[0][1]["endTime"] == END - 1
    assert orderflow_calls[0][0] == USDM_AGG_TRADES_URL
    assert orderflow_calls[0][1]["startTime"] == START - STEP

    feature_path = tmp_path / first.dataset_ref
    rows = load_orderflow_feature_csv(feature_path)
    assert len(rows) == 3
    assert [row.footprint_available_at_ms for row in rows] == [
        START,
        START + STEP,
        START + 2 * STEP,
    ]
    assert rows[0].of_delta > 0
    assert rows[1].of_delta < 0
    assert rows[2].of_delta > 0

    candle_manifest = load_candle_acquisition(first.candle_manifest_path)
    assert candle_manifest.venue == CandleVenue.USD_M_FUTURES.value
    assert candle_manifest.endpoint == USDM_KLINES_URL
    assert candle_manifest.requested_start_ms == START
    assert candle_manifest.requested_end_ms == END


def test_candle_manifest_tamper_fails_integrity(tmp_path) -> None:
    manifest, _ = build_usdm_orderflow_feature_dataset(
        symbol="BTCUSDT",
        interval="1m",
        start_ms=START,
        end_ms=END,
        price_bucket=1.0,
        dataset_root=tmp_path,
        candle_request_json=_candle_request([]),
        orderflow_request_json=_orderflow_request([]),
    )
    candle_manifest = load_candle_acquisition(manifest.candle_manifest_path)
    csv_path = Path(candle_manifest.csv_path)
    csv_path.write_text(csv_path.read_text(encoding="utf-8") + "\n", encoding="utf-8")

    with pytest.raises(ValueError, match="CSV integrity"):
        load_candle_acquisition(manifest.candle_manifest_path)


def test_feature_workflow_rejects_unsafe_namespace_and_bad_window(tmp_path) -> None:
    kwargs = {
        "symbol": "BTCUSDT",
        "interval": "1m",
        "start_ms": START,
        "end_ms": END,
        "price_bucket": 1.0,
        "dataset_root": tmp_path,
        "candle_request_json": _candle_request([]),
        "orderflow_request_json": _orderflow_request([]),
    }
    with pytest.raises(ValueError, match="safe relative path"):
        build_usdm_orderflow_feature_dataset(**kwargs, namespace="../escape")
    with pytest.raises(ValueError, match="align to interval boundaries"):
        build_usdm_orderflow_feature_dataset(**{**kwargs, "start_ms": START + 1})
    with pytest.raises(ValueError, match="price_bucket must be positive"):
        build_usdm_orderflow_feature_dataset(**{**kwargs, "price_bucket": 0.0})


def test_feature_workflow_rejects_m5_oos_before_any_network_request(tmp_path) -> None:
    candle_calls: list[tuple[str, dict[str, object]]] = []
    orderflow_calls: list[tuple[str, dict[str, object]]] = []
    start = DEFAULT_M5_STUDY_POLICY.frozen_oos_start_ms + STEP

    with pytest.raises(RuntimeError, match="sealed M5 frozen OOS"):
        build_usdm_orderflow_feature_dataset(
            symbol="BTCUSDT",
            interval="1m",
            start_ms=start,
            end_ms=start + 3 * STEP,
            price_bucket=1.0,
            dataset_root=tmp_path,
            candle_request_json=_candle_request(candle_calls),
            orderflow_request_json=_orderflow_request(orderflow_calls),
        )

    assert candle_calls == []
    assert orderflow_calls == []
