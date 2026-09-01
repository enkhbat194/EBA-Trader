from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .history import Candle
from .orderflow_feature_dataset import OrderFlowFeatureRow
from .research_evidence import canonical_json, sha256_text

D0_SCHEMA = "strategy_factory_v2_d0_dataset_v1"
D0_AUTHORITY = "DISCOVERY_ONLY"
D0_PROVENANCE_CLASS = "INSPECTED_REUSABLE_DISCOVERY_DATA"
DEFAULT_TEMPORAL_STRATA = 8


@dataclass(frozen=True, slots=True)
class D0TemporalStratum:
    stratum_id: str
    start_index: int
    end_index_exclusive: int
    start_ms: int
    end_ms: int

    @property
    def row_count(self) -> int:
        return self.end_index_exclusive - self.start_index

    def as_dict(self) -> dict[str, object]:
        return {
            "stratum_id": self.stratum_id,
            "start_index": self.start_index,
            "end_index_exclusive": self.end_index_exclusive,
            "start_ms": self.start_ms,
            "end_ms": self.end_ms,
            "row_count": self.row_count,
        }


@dataclass(frozen=True, slots=True)
class D0DatasetManifest:
    symbol: str
    venue: str
    interval: str
    candle_sha256: str
    orderflow_sha256: str | None
    dataset_sha256: str
    row_count: int
    start_ms: int
    end_ms: int
    temporal_strata: tuple[D0TemporalStratum, ...]
    authority: str = D0_AUTHORITY
    provenance_class: str = D0_PROVENANCE_CLASS
    schema: str = D0_SCHEMA

    def __post_init__(self) -> None:
        if self.schema != D0_SCHEMA or self.authority != D0_AUTHORITY:
            raise ValueError("D0 dataset contract authority changed")
        if self.provenance_class != D0_PROVENANCE_CLASS:
            raise ValueError("D0 data must remain explicitly inspected/reusable discovery data")
        if self.row_count < 3:
            raise ValueError("D0 dataset requires at least three rows")
        if self.start_ms >= self.end_ms:
            raise ValueError("D0 dataset time range is invalid")
        if not self.temporal_strata:
            raise ValueError("D0 dataset requires temporal strata")

    def as_dict(self) -> dict[str, Any]:
        return {
            "schema": self.schema,
            "authority": self.authority,
            "provenance_class": self.provenance_class,
            "symbol": self.symbol,
            "venue": self.venue,
            "interval": self.interval,
            "candle_sha256": self.candle_sha256,
            "orderflow_sha256": self.orderflow_sha256,
            "dataset_sha256": self.dataset_sha256,
            "row_count": self.row_count,
            "start_ms": self.start_ms,
            "end_ms": self.end_ms,
            "temporal_strata": [item.as_dict() for item in self.temporal_strata],
        }


def build_d0_dataset_manifest(
    *,
    symbol: str,
    venue: str,
    interval: str,
    candles: tuple[Candle, ...],
    orderflow_rows: tuple[OrderFlowFeatureRow, ...] = (),
    temporal_strata: int = DEFAULT_TEMPORAL_STRATA,
) -> D0DatasetManifest:
    if not symbol.strip() or not venue.strip() or not interval.strip():
        raise ValueError("D0 market identity is required")
    if len(candles) < 3:
        raise ValueError("D0 dataset requires at least three candles")
    if temporal_strata < 2 or temporal_strata > len(candles):
        raise ValueError("D0 temporal_strata must be between 2 and row count")
    _validate_candles(candles)
    if orderflow_rows:
        _validate_orderflow(candles, orderflow_rows)

    candle_payload = [_candle_payload(candle) for candle in candles]
    candle_sha = sha256_text(canonical_json(candle_payload))
    orderflow_sha = None
    if orderflow_rows:
        orderflow_payload = [_orderflow_payload(row) for row in orderflow_rows]
        orderflow_sha = sha256_text(canonical_json(orderflow_payload))

    strata = _temporal_strata(candles, temporal_strata)
    identity = {
        "schema": D0_SCHEMA,
        "authority": D0_AUTHORITY,
        "provenance_class": D0_PROVENANCE_CLASS,
        "symbol": symbol.strip().upper(),
        "venue": venue.strip().lower(),
        "interval": interval.strip(),
        "candle_sha256": candle_sha,
        "orderflow_sha256": orderflow_sha,
        "row_count": len(candles),
        "start_ms": candles[0].open_time_ms,
        "end_ms": candles[-1].close_time_ms,
        "temporal_strata": [item.as_dict() for item in strata],
    }
    dataset_sha = sha256_text(canonical_json(identity))
    return D0DatasetManifest(
        symbol=identity["symbol"],
        venue=identity["venue"],
        interval=identity["interval"],
        candle_sha256=candle_sha,
        orderflow_sha256=orderflow_sha,
        dataset_sha256=dataset_sha,
        row_count=len(candles),
        start_ms=candles[0].open_time_ms,
        end_ms=candles[-1].close_time_ms,
        temporal_strata=strata,
    )


def low_fidelity_strata(manifest: D0DatasetManifest) -> tuple[str, ...]:
    """Return all declared temporal strata; low-fidelity racing may not use first-N chronology."""
    return tuple(item.stratum_id for item in manifest.temporal_strata)


def _temporal_strata(
    candles: tuple[Candle, ...],
    count: int,
) -> tuple[D0TemporalStratum, ...]:
    output: list[D0TemporalStratum] = []
    total = len(candles)
    for index in range(count):
        start = index * total // count
        end = (index + 1) * total // count
        if start >= end:
            raise RuntimeError("D0 temporal stratum is empty")
        output.append(
            D0TemporalStratum(
                stratum_id=f"d0-t{index + 1:02d}",
                start_index=start,
                end_index_exclusive=end,
                start_ms=candles[start].open_time_ms,
                end_ms=candles[end - 1].close_time_ms,
            )
        )
    return tuple(output)


def _validate_candles(candles: tuple[Candle, ...]) -> None:
    previous: int | None = None
    for candle in candles:
        if previous is not None and candle.open_time_ms <= previous:
            raise ValueError("D0 candles must be strictly chronological")
        previous = candle.open_time_ms


def _validate_orderflow(
    candles: tuple[Candle, ...],
    rows: tuple[OrderFlowFeatureRow, ...],
) -> None:
    if len(rows) != len(candles):
        raise ValueError("D0 order-flow rows must align one-to-one with candles")
    for candle, row in zip(candles, rows, strict=True):
        if row.candle.open_time_ms != candle.open_time_ms:
            raise ValueError("D0 order-flow rows are time-misaligned")
        if row.footprint_available_at_ms > candle.open_time_ms:
            raise ValueError("D0 order-flow feature is not causal at candle open")


def _candle_payload(candle: Candle) -> dict[str, object]:
    return {
        "open_time_ms": candle.open_time_ms,
        "open": candle.open,
        "high": candle.high,
        "low": candle.low,
        "close": candle.close,
        "volume": candle.volume,
        "close_time_ms": candle.close_time_ms,
        "quote_volume": candle.quote_volume,
        "trade_count": candle.trade_count,
    }


def _orderflow_payload(row: OrderFlowFeatureRow) -> dict[str, object]:
    return {
        "open_time_ms": row.candle.open_time_ms,
        "of_buy_volume": row.of_buy_volume,
        "of_sell_volume": row.of_sell_volume,
        "of_delta": row.of_delta,
        "of_delta_ratio": row.of_delta_ratio,
        "of_cvd": row.of_cvd,
        "of_poc_price": row.of_poc_price,
        "footprint_available_at_ms": row.footprint_available_at_ms,
        "of_stacked_buy_levels": row.of_stacked_buy_levels,
        "of_stacked_sell_levels": row.of_stacked_sell_levels,
        "of_stacked_imbalance": row.of_stacked_imbalance,
        "of_absorption": row.of_absorption,
        "of_exhaustion": row.of_exhaustion,
        "of_bullish_price_delta_divergence": row.of_bullish_price_delta_divergence,
        "of_bearish_price_delta_divergence": row.of_bearish_price_delta_divergence,
        "of_price_delta_divergence": row.of_price_delta_divergence,
    }
