from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .orderflow import AggressorSide, TradeEvent
from .research_evidence import canonical_json, sha256_file, sha256_text


@dataclass(frozen=True, slots=True)
class AggregateTradeRecord:
    aggregate_trade_id: int
    timestamp_ms: int
    price: float
    quantity: float
    aggressor: AggressorSide

    def to_trade_event(self) -> TradeEvent:
        return TradeEvent(
            timestamp_ms=self.timestamp_ms,
            price=self.price,
            quantity=self.quantity,
            aggressor=self.aggressor,
        )

    def as_dict(self) -> dict[str, object]:
        return {
            "aggregate_trade_id": self.aggregate_trade_id,
            "timestamp_ms": self.timestamp_ms,
            "price": self.price,
            "quantity": self.quantity,
            "aggressor": self.aggressor.value,
        }


@dataclass(frozen=True, slots=True)
class OrderFlowDatasetManifest:
    dataset_id: str
    symbol: str
    source: str
    record_count: int
    first_trade_id: int | None
    last_trade_id: int | None
    start_ms: int | None
    end_ms: int | None
    sequence_gap_count: int
    records_sha256: str
    records_path: str

    def as_dict(self) -> dict[str, object]:
        return {
            "dataset_id": self.dataset_id,
            "symbol": self.symbol,
            "source": self.source,
            "record_count": self.record_count,
            "first_trade_id": self.first_trade_id,
            "last_trade_id": self.last_trade_id,
            "start_ms": self.start_ms,
            "end_ms": self.end_ms,
            "sequence_gap_count": self.sequence_gap_count,
            "records_sha256": self.records_sha256,
            "records_path": self.records_path,
        }


def parse_binance_agg_trade(payload: dict[str, Any]) -> AggregateTradeRecord:
    required = {"a", "p", "q", "T", "m"}
    missing = sorted(required - set(payload))
    if missing:
        raise ValueError(f"aggregate trade missing fields: {', '.join(missing)}")

    aggregate_trade_id = payload["a"]
    timestamp_ms = payload["T"]
    buyer_is_maker = payload["m"]
    if isinstance(aggregate_trade_id, bool) or not isinstance(aggregate_trade_id, int):
        raise ValueError("aggregate trade id must be an integer")
    if aggregate_trade_id < 0:
        raise ValueError("aggregate trade id must be >= 0")
    if isinstance(timestamp_ms, bool) or not isinstance(timestamp_ms, int):
        raise ValueError("aggregate trade timestamp must be an integer")
    if timestamp_ms < 0:
        raise ValueError("aggregate trade timestamp must be >= 0")
    if not isinstance(buyer_is_maker, bool):
        raise ValueError("aggregate trade maker flag must be boolean")

    try:
        price = float(payload["p"])
        quantity = float(payload["q"])
    except (TypeError, ValueError) as exc:
        raise ValueError("aggregate trade price/quantity must be numeric") from exc

    aggressor = AggressorSide.SELL if buyer_is_maker else AggressorSide.BUY
    event = TradeEvent(timestamp_ms, price, quantity, aggressor)
    return AggregateTradeRecord(
        aggregate_trade_id=aggregate_trade_id,
        timestamp_ms=event.timestamp_ms,
        price=event.price,
        quantity=event.quantity,
        aggressor=event.aggressor,
    )


def aggregate_trade_record_from_mapping(payload: dict[str, Any]) -> AggregateTradeRecord:
    required = {"aggregate_trade_id", "timestamp_ms", "price", "quantity", "aggressor"}
    if set(payload) != required:
        missing = sorted(required - set(payload))
        unknown = sorted(set(payload) - required)
        details = []
        if missing:
            details.append(f"missing={','.join(missing)}")
        if unknown:
            details.append(f"unknown={','.join(unknown)}")
        raise ValueError("invalid stored aggregate-trade fields: " + " ".join(details))

    aggregate_trade_id = payload["aggregate_trade_id"]
    timestamp_ms = payload["timestamp_ms"]
    if isinstance(aggregate_trade_id, bool) or not isinstance(aggregate_trade_id, int):
        raise ValueError("stored aggregate trade id must be an integer")
    if isinstance(timestamp_ms, bool) or not isinstance(timestamp_ms, int):
        raise ValueError("stored aggregate trade timestamp must be an integer")
    try:
        aggressor = AggressorSide(str(payload["aggressor"]))
        price = float(payload["price"])
        quantity = float(payload["quantity"])
    except (TypeError, ValueError) as exc:
        raise ValueError("invalid stored aggregate-trade value") from exc
    event = TradeEvent(timestamp_ms, price, quantity, aggressor)
    if aggregate_trade_id < 0:
        raise ValueError("stored aggregate trade id must be >= 0")
    return AggregateTradeRecord(
        aggregate_trade_id=aggregate_trade_id,
        timestamp_ms=event.timestamp_ms,
        price=event.price,
        quantity=event.quantity,
        aggressor=event.aggressor,
    )


def normalize_aggregate_trades(
    payloads: list[dict[str, Any]] | tuple[dict[str, Any], ...],
) -> tuple[AggregateTradeRecord, ...]:
    records = tuple(
        sorted(
            (parse_binance_agg_trade(item) for item in payloads),
            key=lambda item: item.aggregate_trade_id,
        )
    )
    return validate_aggregate_trade_records(records)


def validate_aggregate_trade_records(
    records: tuple[AggregateTradeRecord, ...] | list[AggregateTradeRecord],
) -> tuple[AggregateTradeRecord, ...]:
    ordered = tuple(records)
    seen: dict[int, AggregateTradeRecord] = {}
    previous_id: int | None = None
    previous_timestamp: int | None = None
    for record in ordered:
        existing = seen.get(record.aggregate_trade_id)
        if existing is not None:
            if existing != record:
                raise ValueError("conflicting duplicate aggregate trade id")
            raise ValueError("duplicate aggregate trade id")
        if previous_id is not None and record.aggregate_trade_id <= previous_id:
            raise ValueError("aggregate trade IDs must be strictly increasing")
        seen[record.aggregate_trade_id] = record
        if previous_timestamp is not None and record.timestamp_ms < previous_timestamp:
            raise ValueError("aggregate trade timestamps move backward after id ordering")
        previous_id = record.aggregate_trade_id
        previous_timestamp = record.timestamp_ms
    return ordered


def sequence_gap_count(records: tuple[AggregateTradeRecord, ...]) -> int:
    return sum(
        max(current.aggregate_trade_id - previous.aggregate_trade_id - 1, 0)
        for previous, current in zip(records, records[1:], strict=False)
    )


def orderflow_manifest_from_mapping(payload: dict[str, Any]) -> OrderFlowDatasetManifest:
    required = {
        "dataset_id",
        "symbol",
        "source",
        "record_count",
        "first_trade_id",
        "last_trade_id",
        "start_ms",
        "end_ms",
        "sequence_gap_count",
        "records_sha256",
        "records_path",
    }
    if set(payload) != required:
        raise ValueError("invalid order-flow dataset manifest fields")

    integer_fields = ("record_count", "sequence_gap_count")
    for field in integer_fields:
        value = payload[field]
        if isinstance(value, bool) or not isinstance(value, int) or value < 0:
            raise ValueError(f"manifest {field} must be a non-negative integer")
    optional_integer_fields = ("first_trade_id", "last_trade_id", "start_ms", "end_ms")
    for field in optional_integer_fields:
        value = payload[field]
        if value is not None and (isinstance(value, bool) or not isinstance(value, int)):
            raise ValueError(f"manifest {field} must be an integer or null")

    return OrderFlowDatasetManifest(
        dataset_id=str(payload["dataset_id"]),
        symbol=str(payload["symbol"]),
        source=str(payload["source"]),
        record_count=int(payload["record_count"]),
        first_trade_id=payload["first_trade_id"],
        last_trade_id=payload["last_trade_id"],
        start_ms=payload["start_ms"],
        end_ms=payload["end_ms"],
        sequence_gap_count=int(payload["sequence_gap_count"]),
        records_sha256=str(payload["records_sha256"]),
        records_path=str(payload["records_path"]),
    )


def load_orderflow_manifest(path: str | Path) -> OrderFlowDatasetManifest:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("order-flow manifest must be an object")
    return orderflow_manifest_from_mapping(payload)


def load_orderflow_records(path: str | Path) -> tuple[AggregateTradeRecord, ...]:
    records: list[AggregateTradeRecord] = []
    with Path(path).open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                raise ValueError(f"blank order-flow record line: {line_number}")
            payload = json.loads(line)
            if not isinstance(payload, dict):
                raise ValueError(f"order-flow record line {line_number} must be an object")
            records.append(aggregate_trade_record_from_mapping(payload))
    return validate_aggregate_trade_records(records)


def require_research_ready(manifest: OrderFlowDatasetManifest) -> None:
    if manifest.record_count < 1:
        raise ValueError("order-flow dataset is empty")
    if manifest.sequence_gap_count != 0:
        raise ValueError(
            "order-flow dataset has aggregate-trade sequence gaps; "
            "repair/re-download before research"
        )
    records_path = Path(manifest.records_path)
    if not records_path.is_file():
        raise ValueError("order-flow dataset records file is missing")
    if sha256_file(records_path) != manifest.records_sha256:
        raise ValueError("order-flow dataset records SHA-256 mismatch")
    records = load_orderflow_records(records_path)
    if len(records) != manifest.record_count:
        raise ValueError("order-flow dataset record count does not match manifest")
    if sequence_gap_count(records) != 0:
        raise ValueError("order-flow records contain aggregate-trade sequence gaps")
    if records[0].aggregate_trade_id != manifest.first_trade_id:
        raise ValueError("order-flow first trade ID does not match manifest")
    if records[-1].aggregate_trade_id != manifest.last_trade_id:
        raise ValueError("order-flow last trade ID does not match manifest")


class OrderFlowDatasetWriter:
    def __init__(self, root: str | Path) -> None:
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    def write(
        self,
        *,
        symbol: str,
        payloads: list[dict[str, Any]] | tuple[dict[str, Any], ...],
        source: str = "binance_aggTrades",
    ) -> OrderFlowDatasetManifest:
        symbol = symbol.strip().upper()
        source = source.strip()
        if not symbol:
            raise ValueError("symbol is required")
        if not source:
            raise ValueError("source is required")

        records = normalize_aggregate_trades(payloads)
        records_text = "".join(
            canonical_json(record.as_dict()) + "\n" for record in records
        )
        records_sha256 = sha256_text(records_text)
        identity = canonical_json(
            {
                "symbol": symbol,
                "source": source,
                "records_sha256": records_sha256,
            }
        )
        dataset_id = f"ofd_{sha256_text(identity)[:24]}"
        records_path = self.root / f"{dataset_id}.jsonl"
        manifest_path = self.root / f"{dataset_id}.manifest.json"

        if records_path.exists():
            if sha256_file(records_path) != records_sha256:
                raise RuntimeError("immutable order-flow dataset collision")
        else:
            records_path.write_text(records_text, encoding="utf-8")

        manifest = OrderFlowDatasetManifest(
            dataset_id=dataset_id,
            symbol=symbol,
            source=source,
            record_count=len(records),
            first_trade_id=records[0].aggregate_trade_id if records else None,
            last_trade_id=records[-1].aggregate_trade_id if records else None,
            start_ms=records[0].timestamp_ms if records else None,
            end_ms=records[-1].timestamp_ms if records else None,
            sequence_gap_count=sequence_gap_count(records),
            records_sha256=records_sha256,
            records_path=str(records_path),
        )
        manifest_text = canonical_json(manifest.as_dict())
        if (
            manifest_path.exists()
            and manifest_path.read_text(encoding="utf-8") != manifest_text
        ):
            raise RuntimeError("immutable order-flow manifest collision")
        manifest_path.write_text(manifest_text, encoding="utf-8")
        return manifest
