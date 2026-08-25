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


def normalize_aggregate_trades(
    payloads: list[dict[str, Any]] | tuple[dict[str, Any], ...],
) -> tuple[AggregateTradeRecord, ...]:
    records = tuple(sorted((parse_binance_agg_trade(item) for item in payloads), key=lambda x: x.aggregate_trade_id))
    seen: dict[int, AggregateTradeRecord] = {}
    previous_timestamp: int | None = None
    for record in records:
        existing = seen.get(record.aggregate_trade_id)
        if existing is not None:
            if existing != record:
                raise ValueError("conflicting duplicate aggregate trade id")
            raise ValueError("duplicate aggregate trade id")
        seen[record.aggregate_trade_id] = record
        if previous_timestamp is not None and record.timestamp_ms < previous_timestamp:
            raise ValueError("aggregate trade timestamps move backward after id ordering")
        previous_timestamp = record.timestamp_ms
    return records


def sequence_gap_count(records: tuple[AggregateTradeRecord, ...]) -> int:
    return sum(
        max(current.aggregate_trade_id - previous.aggregate_trade_id - 1, 0)
        for previous, current in zip(records, records[1:], strict=False)
    )


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
        records_text = "".join(canonical_json(record.as_dict()) + "\n" for record in records)
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
        if manifest_path.exists() and manifest_path.read_text(encoding="utf-8") != manifest_text:
            raise RuntimeError("immutable order-flow manifest collision")
        manifest_path.write_text(manifest_text, encoding="utf-8")
        return manifest
