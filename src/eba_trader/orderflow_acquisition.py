from __future__ import annotations

import argparse
import json
import time
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from .history import parse_utc
from .holdout_guard import assert_not_first_cycle_oos_overlap
from .orderflow_dataset import (
    AggregateTradeRecord,
    OrderFlowDatasetManifest,
    OrderFlowDatasetWriter,
    normalize_aggregate_trades,
    parse_binance_agg_trade,
    require_research_ready,
)
from .research_evidence import canonical_json, sha256_text

SPOT_AGG_TRADES_URL = "https://data-api.binance.vision/api/v3/aggTrades"
USDM_AGG_TRADES_URL = "https://fapi.binance.com/fapi/v1/aggTrades"
MAX_PAGE_SIZE = 1000


class OrderFlowVenue(StrEnum):
    SPOT = "spot"
    USD_M_FUTURES = "usd_m_futures"


ENDPOINTS = {
    OrderFlowVenue.SPOT: SPOT_AGG_TRADES_URL,
    OrderFlowVenue.USD_M_FUTURES: USDM_AGG_TRADES_URL,
}


@dataclass(frozen=True, slots=True)
class RequestProvenance:
    endpoint: str
    mode: str
    params: tuple[tuple[str, str], ...]
    response_count: int
    first_trade_id: int | None
    last_trade_id: int | None
    first_timestamp_ms: int | None
    last_timestamp_ms: int | None

    def as_dict(self) -> dict[str, object]:
        return {
            "endpoint": self.endpoint,
            "mode": self.mode,
            "params": dict(self.params),
            "response_count": self.response_count,
            "first_trade_id": self.first_trade_id,
            "last_trade_id": self.last_trade_id,
            "first_timestamp_ms": self.first_timestamp_ms,
            "last_timestamp_ms": self.last_timestamp_ms,
        }


@dataclass(frozen=True, slots=True)
class AggregateTradeDownload:
    symbol: str
    venue: OrderFlowVenue
    start_ms: int
    end_ms: int
    payloads: tuple[dict[str, Any], ...]
    requests: tuple[RequestProvenance, ...]
    source_endpoint: str | None = None

    @property
    def records(self) -> tuple[AggregateTradeRecord, ...]:
        return normalize_aggregate_trades(self.payloads)


@dataclass(frozen=True, slots=True)
class AcquisitionManifest:
    acquisition_id: str
    dataset_id: str
    symbol: str
    venue: str
    endpoint: str
    requested_start_ms: int
    requested_end_ms: int
    record_count: int
    first_trade_id: int | None
    last_trade_id: int | None
    request_count: int
    requests_sha256: str

    def as_dict(self) -> dict[str, object]:
        return {
            "acquisition_id": self.acquisition_id,
            "dataset_id": self.dataset_id,
            "symbol": self.symbol,
            "venue": self.venue,
            "endpoint": self.endpoint,
            "requested_start_ms": self.requested_start_ms,
            "requested_end_ms": self.requested_end_ms,
            "record_count": self.record_count,
            "first_trade_id": self.first_trade_id,
            "last_trade_id": self.last_trade_id,
            "request_count": self.request_count,
            "requests_sha256": self.requests_sha256,
        }


RequestJson = Callable[[str, Mapping[str, object]], object]


def _retry_delay_seconds(error: HTTPError, attempt: int, backoff_seconds: float) -> float:
    retry_after = error.headers.get("Retry-After") if error.headers is not None else None
    if retry_after:
        try:
            return min(max(float(retry_after), 0.0), 120.0)
        except ValueError:
            pass
    return min(backoff_seconds * (2**attempt), 30.0)


def _request_json(
    endpoint: str,
    params: Mapping[str, object],
    *,
    request_timeout: float,
    max_retries: int,
    backoff_seconds: float,
) -> object:
    if max_retries < 0:
        raise ValueError("max_retries cannot be negative")
    if backoff_seconds < 0:
        raise ValueError("backoff_seconds cannot be negative")

    request = Request(
        f"{endpoint}?{urlencode(params)}",
        headers={"User-Agent": "EBA-Trader/0.1 orderflow-research"},
    )
    for attempt in range(max_retries + 1):
        try:
            with urlopen(request, timeout=request_timeout) as response:  # noqa: S310
                return json.loads(response.read().decode("utf-8"))
        except HTTPError as error:
            retryable = error.code in {418, 429} or 500 <= error.code < 600
            if not retryable or attempt >= max_retries:
                raise RuntimeError(f"Binance HTTP error {error.code}") from error
            time.sleep(_retry_delay_seconds(error, attempt, backoff_seconds))
        except (URLError, TimeoutError) as error:
            if attempt >= max_retries:
                raise RuntimeError("Binance network request failed after retries") from error
            time.sleep(min(backoff_seconds * (2**attempt), 30.0))
    raise RuntimeError("Unreachable retry state")


def _normalize_page(payload: object) -> tuple[dict[str, Any], ...]:
    if not isinstance(payload, list):
        raise RuntimeError(f"Unexpected Binance aggregate-trade response: {payload!r}")
    page: list[dict[str, Any]] = []
    for item in payload:
        if not isinstance(item, dict):
            raise RuntimeError("Binance aggregate-trade page contains a non-object row")
        parse_binance_agg_trade(item)
        page.append(dict(item))
    return tuple(page)


def _request_provenance(
    endpoint: str,
    mode: str,
    params: Mapping[str, object],
    page: tuple[dict[str, Any], ...],
) -> RequestProvenance:
    records = tuple(parse_binance_agg_trade(item) for item in page)
    return RequestProvenance(
        endpoint=endpoint,
        mode=mode,
        params=tuple(sorted((str(key), str(value)) for key, value in params.items())),
        response_count=len(records),
        first_trade_id=records[0].aggregate_trade_id if records else None,
        last_trade_id=records[-1].aggregate_trade_id if records else None,
        first_timestamp_ms=records[0].timestamp_ms if records else None,
        last_timestamp_ms=records[-1].timestamp_ms if records else None,
    )


def fetch_binance_agg_trades(
    symbol: str,
    start_ms: int,
    end_ms: int,
    *,
    venue: OrderFlowVenue = OrderFlowVenue.USD_M_FUTURES,
    request_timeout: float = 20.0,
    pause_seconds: float = 0.08,
    max_retries: int = 5,
    backoff_seconds: float = 0.5,
    request_json: RequestJson | None = None,
) -> AggregateTradeDownload:
    symbol = symbol.strip().upper()
    if not symbol:
        raise ValueError("symbol is required")
    if start_ms < 0 or end_ms <= start_ms:
        raise ValueError("invalid aggregate-trade time range")
    if pause_seconds < 0:
        raise ValueError("pause_seconds cannot be negative")

    endpoint = ENDPOINTS[venue]

    def do_request(params: Mapping[str, object]) -> object:
        if request_json is not None:
            return request_json(endpoint, params)
        return _request_json(
            endpoint,
            params,
            request_timeout=request_timeout,
            max_retries=max_retries,
            backoff_seconds=backoff_seconds,
        )

    all_payloads: list[dict[str, Any]] = []
    provenance: list[RequestProvenance] = []
    params: dict[str, object] = {
        "symbol": symbol,
        "startTime": start_ms,
        "limit": MAX_PAGE_SIZE,
    }
    mode = "time_bootstrap"
    previous_last_id: int | None = None

    while True:
        page = _normalize_page(do_request(params))
        provenance.append(_request_provenance(endpoint, mode, params, page))
        if not page:
            break

        parsed = tuple(parse_binance_agg_trade(item) for item in page)
        if previous_last_id is not None and parsed[0].aggregate_trade_id < previous_last_id + 1:
            raise RuntimeError("Binance aggregate-trade pagination moved backward")

        in_range = [
            item
            for item, record in zip(page, parsed, strict=True)
            if start_ms <= record.timestamp_ms < end_ms
        ]
        all_payloads.extend(in_range)

        if parsed[-1].timestamp_ms >= end_ms:
            break
        if len(page) < MAX_PAGE_SIZE:
            break

        next_from_id = parsed[-1].aggregate_trade_id + 1
        if previous_last_id is not None and next_from_id <= previous_last_id + 1:
            raise RuntimeError("Binance aggregate-trade pagination did not advance")
        previous_last_id = parsed[-1].aggregate_trade_id
        params = {
            "symbol": symbol,
            "fromId": next_from_id,
            "limit": MAX_PAGE_SIZE,
        }
        mode = "from_id"
        if pause_seconds:
            time.sleep(pause_seconds)

    records = normalize_aggregate_trades(tuple(all_payloads)) if all_payloads else ()
    return AggregateTradeDownload(
        symbol=symbol,
        venue=venue,
        start_ms=start_ms,
        end_ms=end_ms,
        payloads=tuple(record_payload(record) for record in records),
        requests=tuple(provenance),
        source_endpoint=endpoint,
    )


def record_payload(record: AggregateTradeRecord) -> dict[str, Any]:
    return {
        "a": record.aggregate_trade_id,
        "p": repr(record.price),
        "q": repr(record.quantity),
        "T": record.timestamp_ms,
        "m": record.aggressor.value == "sell",
    }


def find_missing_id_ranges(
    records: tuple[AggregateTradeRecord, ...],
) -> tuple[tuple[int, int], ...]:
    gaps: list[tuple[int, int]] = []
    for previous, current in zip(records, records[1:], strict=False):
        if current.aggregate_trade_id > previous.aggregate_trade_id + 1:
            gaps.append((previous.aggregate_trade_id + 1, current.aggregate_trade_id - 1))
    return tuple(gaps)


def repair_missing_id_ranges(
    download: AggregateTradeDownload,
    *,
    request_json: RequestJson | None = None,
    request_timeout: float = 20.0,
    max_retries: int = 5,
    backoff_seconds: float = 0.5,
) -> AggregateTradeDownload:
    records = download.records
    gaps = find_missing_id_ranges(records)
    if not gaps:
        return download

    endpoint = ENDPOINTS[download.venue]

    def do_request(params: Mapping[str, object]) -> object:
        if request_json is not None:
            return request_json(endpoint, params)
        return _request_json(
            endpoint,
            params,
            request_timeout=request_timeout,
            max_retries=max_retries,
            backoff_seconds=backoff_seconds,
        )

    payload_by_id = {record.aggregate_trade_id: record_payload(record) for record in records}
    provenance = list(download.requests)

    for gap_start, gap_end in gaps:
        cursor = gap_start
        while cursor <= gap_end:
            limit = min(MAX_PAGE_SIZE, gap_end - cursor + 1)
            params = {"symbol": download.symbol, "fromId": cursor, "limit": limit}
            page = _normalize_page(do_request(params))
            provenance.append(_request_provenance(endpoint, "repair_from_id", params, page))
            if not page:
                break
            parsed = tuple(parse_binance_agg_trade(item) for item in page)
            accepted = [
                record
                for record in parsed
                if cursor <= record.aggregate_trade_id <= gap_end
            ]
            if not accepted or accepted[0].aggregate_trade_id != cursor:
                break
            for record in accepted:
                payload_by_id[record.aggregate_trade_id] = record_payload(record)
            next_cursor = accepted[-1].aggregate_trade_id + 1
            if next_cursor <= cursor:
                raise RuntimeError("Aggregate-trade gap repair did not advance")
            cursor = next_cursor

    repaired_payloads = tuple(payload_by_id[key] for key in sorted(payload_by_id))
    repaired_records = normalize_aggregate_trades(repaired_payloads)
    return AggregateTradeDownload(
        symbol=download.symbol,
        venue=download.venue,
        start_ms=download.start_ms,
        end_ms=download.end_ms,
        payloads=tuple(record_payload(record) for record in repaired_records),
        requests=tuple(provenance),
        source_endpoint=download.source_endpoint or endpoint,
    )


def write_acquisition_manifest(
    root: str | Path,
    *,
    download: AggregateTradeDownload,
    dataset: OrderFlowDatasetManifest,
) -> tuple[AcquisitionManifest, Path]:
    root_path = Path(root)
    root_path.mkdir(parents=True, exist_ok=True)
    requests_text = canonical_json([request.as_dict() for request in download.requests])
    requests_sha256 = sha256_text(requests_text)
    identity = canonical_json(
        {
            "dataset_id": dataset.dataset_id,
            "venue": download.venue.value,
            "start_ms": download.start_ms,
            "end_ms": download.end_ms,
            "requests_sha256": requests_sha256,
        }
    )
    acquisition_id = f"ofa_{sha256_text(identity)[:24]}"
    manifest = AcquisitionManifest(
        acquisition_id=acquisition_id,
        dataset_id=dataset.dataset_id,
        symbol=download.symbol,
        venue=download.venue.value,
        endpoint=download.source_endpoint or ENDPOINTS[download.venue],
        requested_start_ms=download.start_ms,
        requested_end_ms=download.end_ms,
        record_count=dataset.record_count,
        first_trade_id=dataset.first_trade_id,
        last_trade_id=dataset.last_trade_id,
        request_count=len(download.requests),
        requests_sha256=requests_sha256,
    )
    path = root_path / f"{acquisition_id}.acquisition.json"
    text = canonical_json(
        {**manifest.as_dict(), "requests": [r.as_dict() for r in download.requests]}
    )
    if path.exists() and path.read_text(encoding="utf-8") != text:
        raise RuntimeError("immutable order-flow acquisition manifest collision")
    path.write_text(text, encoding="utf-8")
    return manifest, path


def download_orderflow_cli() -> None:
    parser = argparse.ArgumentParser(
        description="Download Binance aggregate trades for order-flow research only"
    )
    parser.add_argument("--symbol", default="BTCUSDT")
    parser.add_argument(
        "--venue",
        choices=[item.value for item in OrderFlowVenue],
        default=OrderFlowVenue.USD_M_FUTURES.value,
    )
    parser.add_argument("--start", required=True, help="UTC ISO date/time")
    parser.add_argument("--end", required=True, help="Exclusive UTC end")
    parser.add_argument("--out", default="data/cache/orderflow")
    args = parser.parse_args()

    start_ms = parse_utc(args.start)
    end_ms = parse_utc(args.end)
    assert_not_first_cycle_oos_overlap(
        symbol=args.symbol,
        interval="orderflow",
        start_ms=start_ms,
        end_ms=end_ms,
        context="Order-flow historical downloader",
    )
    download = fetch_binance_agg_trades(
        args.symbol,
        start_ms,
        end_ms,
        venue=OrderFlowVenue(args.venue),
    )
    download = repair_missing_id_ranges(download)
    writer = OrderFlowDatasetWriter(args.out)
    dataset = writer.write(
        symbol=download.symbol,
        payloads=download.payloads,
        source=f"binance_{download.venue.value}_aggTrades",
    )
    require_research_ready(dataset)
    acquisition, path = write_acquisition_manifest(args.out, download=download, dataset=dataset)
    print(
        f"dataset={dataset.dataset_id} acquisition={acquisition.acquisition_id} "
        f"records={dataset.record_count} requests={acquisition.request_count} manifest={path}"
    )
