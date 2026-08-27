from __future__ import annotations

import math
from dataclasses import dataclass

from .orderflow import (
    FootprintFeatures,
    TradeFlowAggregator,
    diagonal_imbalance_stacks,
)
from .orderflow_dataset import AggregateTradeRecord


@dataclass(frozen=True, slots=True)
class FootprintWindowRow:
    start_ms: int
    end_ms: int
    buy_volume: float
    sell_volume: float
    delta: float
    delta_ratio: float
    total_volume: float
    trade_count: int
    poc_price: float | None
    cumulative_delta: float
    stacked_buy_levels: int = 0
    stacked_sell_levels: int = 0
    stacked_imbalance: int = 0


class FootprintDatasetBuilder:
    """Build closed, fixed-width footprint windows without future-event leakage."""

    def __init__(
        self,
        *,
        window_ms: int,
        price_bucket: float,
        imbalance_ratio: float = 3.0,
        imbalance_min_volume: float = 0.0,
    ) -> None:
        if window_ms < 1:
            raise ValueError("window_ms must be >= 1")
        if not math.isfinite(imbalance_ratio) or imbalance_ratio <= 1.0:
            raise ValueError("imbalance_ratio must be finite and > 1")
        if not math.isfinite(imbalance_min_volume) or imbalance_min_volume < 0.0:
            raise ValueError("imbalance_min_volume must be finite and >= 0")
        self.window_ms = window_ms
        self.imbalance_ratio = imbalance_ratio
        self.imbalance_min_volume = imbalance_min_volume
        self.aggregator = TradeFlowAggregator(price_bucket=price_bucket)

    def build(
        self,
        records: tuple[AggregateTradeRecord, ...],
        *,
        start_ms: int,
        end_ms: int,
    ) -> tuple[FootprintWindowRow, ...]:
        if start_ms < 0 or end_ms <= start_ms:
            raise ValueError("invalid footprint dataset window")
        if (end_ms - start_ms) % self.window_ms != 0:
            raise ValueError("dataset range must align exactly to window_ms")

        events = tuple(record.to_trade_event() for record in records)
        rows: list[FootprintWindowRow] = []
        running_delta = 0.0
        for window_start in range(start_ms, end_ms, self.window_ms):
            window_end = window_start + self.window_ms
            features: FootprintFeatures = self.aggregator.aggregate(
                events,
                start_ms=window_start,
                end_ms=window_end,
            )
            stacks = diagonal_imbalance_stacks(
                features.levels,
                ratio_threshold=self.imbalance_ratio,
                min_volume=self.imbalance_min_volume,
            )
            running_delta += features.delta
            rows.append(
                FootprintWindowRow(
                    start_ms=window_start,
                    end_ms=window_end,
                    buy_volume=features.buy_volume,
                    sell_volume=features.sell_volume,
                    delta=features.delta,
                    delta_ratio=features.delta_ratio,
                    total_volume=features.total_volume,
                    trade_count=features.trade_count,
                    poc_price=features.poc_price,
                    cumulative_delta=running_delta,
                    stacked_buy_levels=stacks.buy_levels,
                    stacked_sell_levels=stacks.sell_levels,
                    stacked_imbalance=stacks.signed_score,
                )
            )
        return tuple(rows)
