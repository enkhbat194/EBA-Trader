from __future__ import annotations

from dataclasses import dataclass

from .orderflow import FootprintFeatures, TradeFlowAggregator
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


class FootprintDatasetBuilder:
    """Build closed, fixed-width footprint windows without future-event leakage."""

    def __init__(self, *, window_ms: int, price_bucket: float) -> None:
        if window_ms < 1:
            raise ValueError("window_ms must be >= 1")
        self.window_ms = window_ms
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
                )
            )
        return tuple(rows)
