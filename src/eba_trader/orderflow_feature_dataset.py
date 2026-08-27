from __future__ import annotations

import csv
import json
import math
from dataclasses import dataclass, replace
from pathlib import Path

from .footprint_dataset import FootprintDatasetBuilder
from .history import INTERVAL_MS, Candle, load_csv, validate_interval_window
from .orderflow_alignment import align_closed_footprints_to_candles
from .orderflow_dataset import (
    load_orderflow_manifest,
    load_orderflow_records,
    require_research_ready,
)
from .orderflow_divergence import price_delta_divergence
from .research_evidence import canonical_json, sha256_file, sha256_text

FEATURE_DATASET_SCHEMA = "m5_orderflow_feature_dataset_v4"
RESPONSE_FEATURE_DATASET_SCHEMA = "m5_orderflow_feature_dataset_v3"
STACKED_FEATURE_DATASET_SCHEMA = "m5_orderflow_feature_dataset_v2"
LEGACY_FEATURE_DATASET_SCHEMA = "m5_orderflow_feature_dataset_v1"
SUPPORTED_FEATURE_DATASET_SCHEMAS = {
    LEGACY_FEATURE_DATASET_SCHEMA,
    STACKED_FEATURE_DATASET_SCHEMA,
    RESPONSE_FEATURE_DATASET_SCHEMA,
    FEATURE_DATASET_SCHEMA,
}
DEFAULT_DIVERGENCE_LOOKBACK = 3
DEFAULT_DIVERGENCE_MIN_TOTAL_VOLUME = 0.0


@dataclass(frozen=True, slots=True)
class OrderFlowFeatureRow:
    candle: Candle
    of_buy_volume: float
    of_sell_volume: float
    of_delta: float
    of_delta_ratio: float
    of_cvd: float
    of_poc_price: float | None
    footprint_available_at_ms: int
    of_stacked_buy_levels: int = 0
    of_stacked_sell_levels: int = 0
    of_stacked_imbalance: int = 0
    of_absorption: float = 0.0
    of_exhaustion: float = 0.0
    of_bullish_price_delta_divergence: float = 0.0
    of_bearish_price_delta_divergence: float = 0.0
    of_price_delta_divergence: float = 0.0


@dataclass(frozen=True, slots=True)
class OrderFlowFeatureDatasetManifest:
    dataset_id: str
    schema: str
    symbol: str
    interval: str
    start_ms: int
    end_ms: int
    row_count: int
    price_bucket: float
    imbalance_ratio: float
    imbalance_min_volume: float
    divergence_lookback: int
    divergence_min_total_volume: float
    venue: str
    acquisition_id: str
    candle_sha256: str
    orderflow_dataset_id: str
    orderflow_records_sha256: str
    feature_csv_sha256: str
    feature_csv_path: str

    def as_dict(self) -> dict[str, object]:
        return {
            "dataset_id": self.dataset_id,
            "schema": self.schema,
            "symbol": self.symbol,
            "interval": self.interval,
            "start_ms": self.start_ms,
            "end_ms": self.end_ms,
            "row_count": self.row_count,
            "price_bucket": self.price_bucket,
            "imbalance_ratio": self.imbalance_ratio,
            "imbalance_min_volume": self.imbalance_min_volume,
            "divergence_lookback": self.divergence_lookback,
            "divergence_min_total_volume": self.divergence_min_total_volume,
            "venue": self.venue,
            "acquisition_id": self.acquisition_id,
            "candle_sha256": self.candle_sha256,
            "orderflow_dataset_id": self.orderflow_dataset_id,
            "orderflow_records_sha256": self.orderflow_records_sha256,
            "feature_csv_sha256": self.feature_csv_sha256,
            "feature_csv_path": self.feature_csv_path,
        }


def _load_acquisition(path: str | Path) -> dict[str, object]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("order-flow acquisition manifest must be an object")
    required = {
        "acquisition_id",
        "dataset_id",
        "symbol",
        "venue",
        "endpoint",
        "requested_start_ms",
        "requested_end_ms",
        "record_count",
        "first_trade_id",
        "last_trade_id",
        "request_count",
        "requests_sha256",
        "requests",
    }
    if set(payload) != required:
        raise ValueError("invalid order-flow acquisition manifest fields")
    if not isinstance(payload["requested_start_ms"], int) or isinstance(
        payload["requested_start_ms"], bool
    ):
        raise ValueError("acquisition requested_start_ms must be an integer")
    if not isinstance(payload["requested_end_ms"], int) or isinstance(
        payload["requested_end_ms"], bool
    ):
        raise ValueError("acquisition requested_end_ms must be an integer")
    return payload


def apply_price_delta_divergence(
    rows: tuple[OrderFlowFeatureRow, ...] | list[OrderFlowFeatureRow],
    *,
    lookback: int = DEFAULT_DIVERGENCE_LOOKBACK,
    min_total_volume: float = DEFAULT_DIVERGENCE_MIN_TOTAL_VOLUME,
) -> tuple[OrderFlowFeatureRow, ...]:
    """Attach causal divergence using only price bars already closed at feature availability.

    Row ``i`` is available at candle open ``t`` and contains footprint flow from
    ``[t-step, t)``. Therefore that flow belongs to the price candle stored on row
    ``i-1``. The candle attached to row ``i`` is just opening at ``t`` and its future
    high/low/close must never participate in the divergence available at ``t``.
    """

    if isinstance(lookback, bool) or not isinstance(lookback, int) or lookback < 1:
        raise ValueError("divergence lookback must be an integer >= 1")
    if not math.isfinite(min_total_volume) or min_total_volume < 0.0:
        raise ValueError("divergence min_total_volume must be finite and >= 0")

    source = tuple(rows)
    output: list[OrderFlowFeatureRow] = []
    for index, row in enumerate(source):
        divergence = None
        if index >= lookback + 1:
            current_price = source[index - 1].candle
            reference_indexes = range(index - lookback, index)
            reference_price_rows = [source[ref_index - 1].candle for ref_index in reference_indexes]
            reference_flow_rows = [source[ref_index] for ref_index in reference_indexes]
            divergence = price_delta_divergence(
                current_high=current_price.high,
                current_low=current_price.low,
                current_delta_ratio=row.of_delta_ratio,
                current_total_volume=row.of_buy_volume + row.of_sell_volume,
                reference_highs=tuple(candle.high for candle in reference_price_rows),
                reference_lows=tuple(candle.low for candle in reference_price_rows),
                reference_delta_ratios=tuple(flow.of_delta_ratio for flow in reference_flow_rows),
                reference_total_volumes=tuple(
                    flow.of_buy_volume + flow.of_sell_volume for flow in reference_flow_rows
                ),
                min_total_volume=min_total_volume,
            )
        if divergence is None:
            output.append(row)
        else:
            output.append(
                replace(
                    row,
                    of_bullish_price_delta_divergence=divergence.bullish,
                    of_bearish_price_delta_divergence=divergence.bearish,
                    of_price_delta_divergence=divergence.signed_score,
                )
            )
    return tuple(output)


def materialize_orderflow_feature_dataset(
    *,
    candle_path: str | Path,
    orderflow_manifest_path: str | Path,
    acquisition_manifest_path: str | Path,
    symbol: str,
    interval: str,
    start_ms: int,
    end_ms: int,
    price_bucket: float,
    output_root: str | Path,
    imbalance_ratio: float = 3.0,
    imbalance_min_volume: float = 0.0,
    divergence_lookback: int = DEFAULT_DIVERGENCE_LOOKBACK,
    divergence_min_total_volume: float = DEFAULT_DIVERGENCE_MIN_TOTAL_VOLUME,
) -> OrderFlowFeatureDatasetManifest:
    symbol = symbol.strip().upper()
    if not symbol:
        raise ValueError("symbol is required")
    if interval not in INTERVAL_MS:
        raise ValueError(f"Unsupported interval: {interval}")
    if price_bucket <= 0:
        raise ValueError("price_bucket must be positive")
    if not math.isfinite(imbalance_ratio) or imbalance_ratio <= 1.0:
        raise ValueError("imbalance_ratio must be finite and > 1")
    if not math.isfinite(imbalance_min_volume) or imbalance_min_volume < 0.0:
        raise ValueError("imbalance_min_volume must be finite and >= 0")
    if (
        isinstance(divergence_lookback, bool)
        or not isinstance(divergence_lookback, int)
        or divergence_lookback < 1
    ):
        raise ValueError("divergence_lookback must be an integer >= 1")
    if (
        not math.isfinite(divergence_min_total_volume)
        or divergence_min_total_volume < 0.0
    ):
        raise ValueError("divergence_min_total_volume must be finite and >= 0")
    step = INTERVAL_MS[interval]
    if start_ms < step:
        raise ValueError("start_ms must allow one prior footprint window")

    candle_file = Path(candle_path)
    candles = validate_interval_window(
        load_csv(candle_file),
        interval,
        start_ms,
        end_ms,
    )

    orderflow_manifest = load_orderflow_manifest(orderflow_manifest_path)
    require_research_ready(orderflow_manifest)
    if orderflow_manifest.symbol != symbol:
        raise ValueError("order-flow symbol does not match feature dataset symbol")

    acquisition = _load_acquisition(acquisition_manifest_path)
    if str(acquisition["dataset_id"]) != orderflow_manifest.dataset_id:
        raise ValueError("acquisition dataset_id does not match order-flow manifest")
    if str(acquisition["symbol"]).upper() != symbol:
        raise ValueError("acquisition symbol does not match feature dataset symbol")
    acquisition_start = int(acquisition["requested_start_ms"])
    acquisition_end = int(acquisition["requested_end_ms"])
    required_start = start_ms - step
    if acquisition_start > required_start or acquisition_end < end_ms:
        raise ValueError(
            "order-flow acquisition does not cover the prior closed footprint plus candle range"
        )

    records = load_orderflow_records(orderflow_manifest.records_path)
    footprints = FootprintDatasetBuilder(
        window_ms=step,
        price_bucket=price_bucket,
        imbalance_ratio=imbalance_ratio,
        imbalance_min_volume=imbalance_min_volume,
    ).build(
        records,
        start_ms=required_start,
        end_ms=end_ms,
    )
    aligned = align_closed_footprints_to_candles(
        candles,
        footprints,
        interval=interval,
        require_complete=True,
    )

    base_rows = tuple(
        OrderFlowFeatureRow(
            candle=item.candle,
            of_buy_volume=item.footprint.buy_volume,
            of_sell_volume=item.footprint.sell_volume,
            of_delta=item.footprint.delta,
            of_delta_ratio=item.footprint.delta_ratio,
            of_cvd=item.footprint.cumulative_delta,
            of_poc_price=item.footprint.poc_price,
            footprint_available_at_ms=item.available_at_ms,
            of_stacked_buy_levels=item.footprint.stacked_buy_levels,
            of_stacked_sell_levels=item.footprint.stacked_sell_levels,
            of_stacked_imbalance=item.footprint.stacked_imbalance,
            of_absorption=item.footprint.absorption,
            of_exhaustion=item.footprint.exhaustion,
        )
        for item in aligned
    )
    rows = apply_price_delta_divergence(
        base_rows,
        lookback=divergence_lookback,
        min_total_volume=divergence_min_total_volume,
    )
    if len(rows) != len(candles):
        raise RuntimeError("aligned feature dataset row count does not match candle count")

    output_root_path = Path(output_root)
    output_root_path.mkdir(parents=True, exist_ok=True)
    identity = canonical_json(
        {
            "schema": FEATURE_DATASET_SCHEMA,
            "symbol": symbol,
            "interval": interval,
            "start_ms": start_ms,
            "end_ms": end_ms,
            "price_bucket": price_bucket,
            "imbalance_ratio": imbalance_ratio,
            "imbalance_min_volume": imbalance_min_volume,
            "divergence_lookback": divergence_lookback,
            "divergence_min_total_volume": divergence_min_total_volume,
            "candle_sha256": sha256_file(candle_file),
            "orderflow_dataset_id": orderflow_manifest.dataset_id,
            "orderflow_records_sha256": orderflow_manifest.records_sha256,
            "acquisition_id": str(acquisition["acquisition_id"]),
        }
    )
    dataset_id = f"off_{sha256_text(identity)[:24]}"
    csv_path = output_root_path / f"{dataset_id}.csv"
    _write_feature_csv(rows, csv_path)
    feature_csv_sha256 = sha256_file(csv_path)

    manifest = OrderFlowFeatureDatasetManifest(
        dataset_id=dataset_id,
        schema=FEATURE_DATASET_SCHEMA,
        symbol=symbol,
        interval=interval,
        start_ms=start_ms,
        end_ms=end_ms,
        row_count=len(rows),
        price_bucket=price_bucket,
        imbalance_ratio=imbalance_ratio,
        imbalance_min_volume=imbalance_min_volume,
        divergence_lookback=divergence_lookback,
        divergence_min_total_volume=divergence_min_total_volume,
        venue=str(acquisition["venue"]),
        acquisition_id=str(acquisition["acquisition_id"]),
        candle_sha256=sha256_file(candle_file),
        orderflow_dataset_id=orderflow_manifest.dataset_id,
        orderflow_records_sha256=orderflow_manifest.records_sha256,
        feature_csv_sha256=feature_csv_sha256,
        feature_csv_path=str(csv_path),
    )
    manifest_path = output_root_path / f"{dataset_id}.manifest.json"
    text = canonical_json(manifest.as_dict())
    if manifest_path.exists() and manifest_path.read_text(encoding="utf-8") != text:
        raise RuntimeError("immutable order-flow feature manifest collision")
    manifest_path.write_text(text, encoding="utf-8")
    return manifest


def _write_feature_csv(rows: tuple[OrderFlowFeatureRow, ...], path: Path) -> None:
    fieldnames = [
        "open_time_ms",
        "open",
        "high",
        "low",
        "close",
        "volume",
        "close_time_ms",
        "quote_volume",
        "trade_count",
        "of_buy_volume",
        "of_sell_volume",
        "of_delta",
        "of_delta_ratio",
        "of_cvd",
        "of_poc_price",
        "of_stacked_buy_levels",
        "of_stacked_sell_levels",
        "of_stacked_imbalance",
        "of_absorption",
        "of_exhaustion",
        "of_bullish_price_delta_divergence",
        "of_bearish_price_delta_divergence",
        "of_price_delta_divergence",
        "footprint_available_at_ms",
    ]
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            candle = row.candle
            writer.writerow(
                {
                    "open_time_ms": candle.open_time_ms,
                    "open": candle.open,
                    "high": candle.high,
                    "low": candle.low,
                    "close": candle.close,
                    "volume": candle.volume,
                    "close_time_ms": candle.close_time_ms,
                    "quote_volume": candle.quote_volume,
                    "trade_count": candle.trade_count,
                    "of_buy_volume": row.of_buy_volume,
                    "of_sell_volume": row.of_sell_volume,
                    "of_delta": row.of_delta,
                    "of_delta_ratio": row.of_delta_ratio,
                    "of_cvd": row.of_cvd,
                    "of_poc_price": "" if row.of_poc_price is None else row.of_poc_price,
                    "of_stacked_buy_levels": row.of_stacked_buy_levels,
                    "of_stacked_sell_levels": row.of_stacked_sell_levels,
                    "of_stacked_imbalance": row.of_stacked_imbalance,
                    "of_absorption": row.of_absorption,
                    "of_exhaustion": row.of_exhaustion,
                    "of_bullish_price_delta_divergence": row.of_bullish_price_delta_divergence,
                    "of_bearish_price_delta_divergence": row.of_bearish_price_delta_divergence,
                    "of_price_delta_divergence": row.of_price_delta_divergence,
                    "footprint_available_at_ms": row.footprint_available_at_ms,
                }
            )


def load_orderflow_feature_csv(path: str | Path) -> tuple[OrderFlowFeatureRow, ...]:
    rows: list[OrderFlowFeatureRow] = []
    with Path(path).open("r", newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        legacy_fields = {
            "open_time_ms",
            "open",
            "high",
            "low",
            "close",
            "volume",
            "close_time_ms",
            "quote_volume",
            "trade_count",
            "of_buy_volume",
            "of_sell_volume",
            "of_delta",
            "of_delta_ratio",
            "of_cvd",
            "of_poc_price",
            "footprint_available_at_ms",
        }
        stacked_fields = {
            "of_stacked_buy_levels",
            "of_stacked_sell_levels",
            "of_stacked_imbalance",
        }
        response_fields = {"of_absorption", "of_exhaustion"}
        divergence_fields = {
            "of_bullish_price_delta_divergence",
            "of_bearish_price_delta_divergence",
            "of_price_delta_divergence",
        }
        actual_fields = set(reader.fieldnames or ())
        supported_fields = {
            frozenset(legacy_fields),
            frozenset(legacy_fields | stacked_fields),
            frozenset(legacy_fields | stacked_fields | response_fields),
            frozenset(legacy_fields | stacked_fields | response_fields | divergence_fields),
        }
        if actual_fields not in supported_fields:
            raise ValueError("invalid order-flow feature CSV columns")
        has_stacked = stacked_fields <= actual_fields
        has_response = response_fields <= actual_fields
        has_divergence = divergence_fields <= actual_fields
        for payload in reader:
            poc_text = payload["of_poc_price"].strip()
            candle = Candle(
                open_time_ms=int(payload["open_time_ms"]),
                open=float(payload["open"]),
                high=float(payload["high"]),
                low=float(payload["low"]),
                close=float(payload["close"]),
                volume=float(payload["volume"]),
                close_time_ms=int(payload["close_time_ms"]),
                quote_volume=float(payload["quote_volume"]),
                trade_count=int(payload["trade_count"]),
            )
            available_at_ms = int(payload["footprint_available_at_ms"])
            if available_at_ms != candle.open_time_ms:
                raise ValueError("footprint availability must equal candle open timestamp")
            rows.append(
                OrderFlowFeatureRow(
                    candle=candle,
                    of_buy_volume=float(payload["of_buy_volume"]),
                    of_sell_volume=float(payload["of_sell_volume"]),
                    of_delta=float(payload["of_delta"]),
                    of_delta_ratio=float(payload["of_delta_ratio"]),
                    of_cvd=float(payload["of_cvd"]),
                    of_poc_price=float(poc_text) if poc_text else None,
                    footprint_available_at_ms=available_at_ms,
                    of_stacked_buy_levels=(
                        int(payload["of_stacked_buy_levels"]) if has_stacked else 0
                    ),
                    of_stacked_sell_levels=(
                        int(payload["of_stacked_sell_levels"]) if has_stacked else 0
                    ),
                    of_stacked_imbalance=(
                        int(payload["of_stacked_imbalance"]) if has_stacked else 0
                    ),
                    of_absorption=(float(payload["of_absorption"]) if has_response else 0.0),
                    of_exhaustion=(float(payload["of_exhaustion"]) if has_response else 0.0),
                    of_bullish_price_delta_divergence=(
                        float(payload["of_bullish_price_delta_divergence"])
                        if has_divergence
                        else 0.0
                    ),
                    of_bearish_price_delta_divergence=(
                        float(payload["of_bearish_price_delta_divergence"])
                        if has_divergence
                        else 0.0
                    ),
                    of_price_delta_divergence=(
                        float(payload["of_price_delta_divergence"])
                        if has_divergence
                        else 0.0
                    ),
                )
            )
    validate_interval_window(
        [row.candle for row in rows],
        _infer_interval(rows),
        rows[0].candle.open_time_ms,
        rows[-1].candle.close_time_ms + 1,
    )
    return tuple(rows)


def _infer_interval(rows: list[OrderFlowFeatureRow]) -> str:
    if len(rows) < 2:
        raise ValueError("at least two feature rows are required")
    delta = rows[1].candle.open_time_ms - rows[0].candle.open_time_ms
    matches = [name for name, value in INTERVAL_MS.items() if value == delta]
    if len(matches) != 1:
        raise ValueError("cannot infer a supported feature dataset interval")
    return matches[0]
