from __future__ import annotations

from dataclasses import replace

import pytest

from eba_trader.history import Candle
from eba_trader.orderflow_feature_dataset import OrderFlowFeatureRow
from eba_trader.strategy_factory_v2_d0 import (
    D0_AUTHORITY,
    D0_PROVENANCE_CLASS,
    build_d0_dataset_manifest,
    low_fidelity_strata,
)

STEP = 60_000


def _candles(count: int = 16) -> tuple[Candle, ...]:
    return tuple(
        Candle(
            open_time_ms=index * STEP,
            open=100.0 + index,
            high=101.0 + index,
            low=99.0 + index,
            close=100.5 + index,
            volume=10.0 + index,
            close_time_ms=(index + 1) * STEP - 1,
            quote_volume=1000.0 + index,
            trade_count=20 + index,
        )
        for index in range(count)
    )


def _rows(candles: tuple[Candle, ...]) -> tuple[OrderFlowFeatureRow, ...]:
    return tuple(
        OrderFlowFeatureRow(
            candle=candle,
            of_buy_volume=6.0 + index,
            of_sell_volume=4.0 + index,
            of_delta=2.0,
            of_delta_ratio=0.2,
            of_cvd=float(index),
            of_poc_price=candle.open,
            footprint_available_at_ms=candle.open_time_ms,
        )
        for index, candle in enumerate(candles)
    )


def test_d0_manifest_is_deterministic_and_explicitly_non_fresh() -> None:
    candles = _candles()
    rows = _rows(candles)
    first = build_d0_dataset_manifest(
        symbol="BTCUSDT",
        venue="usd_m_futures",
        interval="1m",
        candles=candles,
        orderflow_rows=rows,
    )
    replay = build_d0_dataset_manifest(
        symbol="btcusdt",
        venue="USD_M_FUTURES",
        interval="1m",
        candles=candles,
        orderflow_rows=rows,
    )

    assert first == replay
    assert first.authority == D0_AUTHORITY == "DISCOVERY_ONLY"
    assert first.provenance_class == D0_PROVENANCE_CLASS
    assert "FRESH" not in first.provenance_class
    assert len(first.temporal_strata) == 8
    assert low_fidelity_strata(first) == tuple(f"d0-t{index:02d}" for index in range(1, 9))


def test_dataset_hash_changes_when_market_content_changes() -> None:
    candles = _candles()
    baseline = build_d0_dataset_manifest(
        symbol="BTCUSDT",
        venue="usd_m_futures",
        interval="1m",
        candles=candles,
        orderflow_rows=_rows(candles),
    )
    changed_candles = list(candles)
    changed_candles[8] = replace(changed_candles[8], close=changed_candles[8].close + 0.25)
    changed = tuple(changed_candles)
    modified = build_d0_dataset_manifest(
        symbol="BTCUSDT",
        venue="usd_m_futures",
        interval="1m",
        candles=changed,
        orderflow_rows=_rows(changed),
    )

    assert baseline.candle_sha256 != modified.candle_sha256
    assert baseline.dataset_sha256 != modified.dataset_sha256


def test_dataset_hash_changes_when_orderflow_content_changes() -> None:
    candles = _candles()
    rows = _rows(candles)
    baseline = build_d0_dataset_manifest(
        symbol="BTCUSDT",
        venue="usd_m_futures",
        interval="1m",
        candles=candles,
        orderflow_rows=rows,
    )
    changed_rows = list(rows)
    changed_rows[5] = replace(changed_rows[5], of_delta_ratio=0.3)
    modified = build_d0_dataset_manifest(
        symbol="BTCUSDT",
        venue="usd_m_futures",
        interval="1m",
        candles=candles,
        orderflow_rows=tuple(changed_rows),
    )

    assert baseline.orderflow_sha256 != modified.orderflow_sha256
    assert baseline.dataset_sha256 != modified.dataset_sha256


def test_temporal_strata_cover_all_rows_without_first_n_racing() -> None:
    manifest = build_d0_dataset_manifest(
        symbol="BTCUSDT",
        venue="usd_m_futures",
        interval="1m",
        candles=_candles(19),
        temporal_strata=8,
    )
    assert sum(item.row_count for item in manifest.temporal_strata) == 19
    assert manifest.temporal_strata[0].start_index == 0
    assert manifest.temporal_strata[-1].end_index_exclusive == 19
    assert all(item.row_count >= 2 for item in manifest.temporal_strata)


def test_orderflow_alignment_and_causality_fail_closed() -> None:
    candles = _candles()
    rows = list(_rows(candles))
    rows[3] = replace(rows[3], footprint_available_at_ms=candles[3].open_time_ms + 1)
    with pytest.raises(ValueError, match="not causal"):
        build_d0_dataset_manifest(
            symbol="BTCUSDT",
            venue="usd_m_futures",
            interval="1m",
            candles=candles,
            orderflow_rows=tuple(rows),
        )
