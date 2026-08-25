from __future__ import annotations

import json
import time
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from .history import (
    INTERVAL_MS,
    Candle,
    candle_from_binance_row,
    load_csv,
    save_csv,
    validate_interval_window,
)
from .research_evidence import canonical_json, sha256_file, sha256_text

SPOT_KLINES_URL = "https://data-api.binance.vision/api/v3/klines"
USDM_KLINES_URL = "https://fapi.binance.com/fapi/v1/klines"
MAX_PAGE_SIZE = 1000
CANDLE_ACQUISITION_SCHEMA = "m5_candle_acquisition_v1"


class CandleVenue(StrEnum):
    SPOT = "spot"
    USD_M_FUTURES = "usd_m_futures"


ENDPOINTS = {
    CandleVenue.SPOT: SPOT_KLINES_URL,
    CandleVenue.USD_M_FUTURES: USDM_KLINES_URL,
}


@dataclass(frozen=True, slots=True)
class CandleRequestProvenance:
    endpoint: str
    params: tuple[tuple[str, str], ...]
    response_count: int
    first_open_ms: int | None
    last_open_ms: int | None

    def as_dict(self) -> dict[str, object]:
        return {
            "endpoint": self.endpoint,
            "params": dict(self.params),
            "response_count": self.response_count,
            "first_open_ms": self.first_open_ms,
            "last_open_ms": self.last_open_ms,
        }


@dataclass(frozen=True, slots=True)
class CandleAcquisitionManifest:
    schema: str
    acquisition_id: str
    symbol: str
    venue: str
    endpoint: str
    interval: str
    requested_start_ms: int
    requested_end_ms: int
    row_count: int
    csv_sha256: str
    csv_path: str
    request_count: int
    requests_sha256: str

    def as_dict(self) -> dict[str, object]:
        return {
            "schema": self.schema,
            "acquisition_id": self.acquisition_id,
            "symbol": self.symbol,
            "venue": self.venue,
            "endpoint": self.endpoint,
            "interval": self.interval,
            "requested_start_ms": self.requested_start_ms,
            "requested_end_ms": self.requested_end_ms,
            "row_count": self.row_count,
            "csv_sha256": self.csv_sha256,
            "csv_path": self.csv_path,
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
    request = Request(
        f"{endpoint}?{urlencode(params)}",
        headers={"User-Agent": "EBA-Trader/0.1 candle-research"},
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
                raise RuntimeError("Binance candle request failed after retries") from error
            time.sleep(min(backoff_seconds * (2**attempt), 30.0))
    raise RuntimeError("unreachable candle retry state")


def fetch_binance_candles(
    symbol: str,
    interval: str,
    start_ms: int,
    end_ms: int,
    *,
    venue: CandleVenue = CandleVenue.USD_M_FUTURES,
    request_timeout: float = 20.0,
    pause_seconds: float = 0.08,
    max_retries: int = 5,
    backoff_seconds: float = 0.5,
    request_json: RequestJson | None = None,
) -> tuple[tuple[Candle, ...], tuple[CandleRequestProvenance, ...]]:
    symbol = symbol.strip().upper()
    if not symbol:
        raise ValueError("symbol is required")
    if interval not in INTERVAL_MS:
        raise ValueError(f"Unsupported interval: {interval}")
    if start_ms < 0 or end_ms <= start_ms:
        raise ValueError("invalid candle time range")
    if pause_seconds < 0:
        raise ValueError("pause_seconds cannot be negative")
    if max_retries < 0:
        raise ValueError("max_retries cannot be negative")
    if backoff_seconds < 0:
        raise ValueError("backoff_seconds cannot be negative")

    step = INTERVAL_MS[interval]
    if start_ms % step != 0 or end_ms % step != 0:
        raise ValueError("candle acquisition range must align to interval boundaries")
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

    candles: list[Candle] = []
    provenance: list[CandleRequestProvenance] = []
    cursor = start_ms
    while cursor < end_ms:
        params: dict[str, object] = {
            "symbol": symbol,
            "interval": interval,
            "startTime": cursor,
            "endTime": end_ms - 1,
            "limit": MAX_PAGE_SIZE,
        }
        payload = do_request(params)
        if not isinstance(payload, list):
            raise RuntimeError(f"Unexpected Binance candle response: {payload!r}")
        page: list[Candle] = []
        for item in payload:
            if not isinstance(item, list):
                raise RuntimeError("Binance candle page contains a non-array row")
            candle = candle_from_binance_row(item)
            if start_ms <= candle.open_time_ms < end_ms:
                page.append(candle)
        provenance.append(
            CandleRequestProvenance(
                endpoint=endpoint,
                params=tuple(sorted((str(key), str(value)) for key, value in params.items())),
                response_count=len(page),
                first_open_ms=page[0].open_time_ms if page else None,
                last_open_ms=page[-1].open_time_ms if page else None,
            )
        )
        if not page:
            break
        candles.extend(page)
        next_cursor = page[-1].open_time_ms + step
        if next_cursor <= cursor:
            raise RuntimeError("candle pagination did not advance")
        cursor = next_cursor
        if len(payload) < MAX_PAGE_SIZE:
            break
        if pause_seconds:
            time.sleep(pause_seconds)

    validated = validate_interval_window(candles, interval, start_ms, end_ms)
    return tuple(validated), tuple(provenance)


def write_candle_acquisition(
    root: str | Path,
    *,
    symbol: str,
    interval: str,
    start_ms: int,
    end_ms: int,
    venue: CandleVenue,
    candles: tuple[Candle, ...],
    requests: tuple[CandleRequestProvenance, ...],
) -> tuple[CandleAcquisitionManifest, Path]:
    symbol = symbol.strip().upper()
    root_path = Path(root)
    root_path.mkdir(parents=True, exist_ok=True)
    validate_interval_window(candles, interval, start_ms, end_ms)

    requests_payload = [request.as_dict() for request in requests]
    requests_sha256 = sha256_text(canonical_json(requests_payload))
    candle_identity = [
        [
            row.open_time_ms,
            row.open,
            row.high,
            row.low,
            row.close,
            row.volume,
            row.close_time_ms,
            row.quote_volume,
            row.trade_count,
        ]
        for row in candles
    ]
    acquisition_identity = canonical_json(
        {
            "schema": CANDLE_ACQUISITION_SCHEMA,
            "symbol": symbol,
            "venue": venue.value,
            "interval": interval,
            "start_ms": start_ms,
            "end_ms": end_ms,
            "requests_sha256": requests_sha256,
            "candles_sha256": sha256_text(canonical_json(candle_identity)),
        }
    )
    acquisition_id = f"cda_{sha256_text(acquisition_identity)[:24]}"
    csv_path = root_path / f"{acquisition_id}.csv"
    manifest_path = root_path / f"{acquisition_id}.acquisition.json"

    if csv_path.exists():
        existing = load_csv(csv_path)
        if tuple(existing) != candles:
            raise RuntimeError("immutable candle acquisition CSV collision")
    else:
        save_csv(candles, csv_path)
    csv_sha256 = sha256_file(csv_path)

    manifest = CandleAcquisitionManifest(
        schema=CANDLE_ACQUISITION_SCHEMA,
        acquisition_id=acquisition_id,
        symbol=symbol,
        venue=venue.value,
        endpoint=ENDPOINTS[venue],
        interval=interval,
        requested_start_ms=start_ms,
        requested_end_ms=end_ms,
        row_count=len(candles),
        csv_sha256=csv_sha256,
        csv_path=str(csv_path),
        request_count=len(requests),
        requests_sha256=requests_sha256,
    )
    text = canonical_json({**manifest.as_dict(), "requests": requests_payload})
    if manifest_path.exists() and manifest_path.read_text(encoding="utf-8") != text:
        raise RuntimeError("immutable candle acquisition manifest collision")
    manifest_path.write_text(text, encoding="utf-8")
    return manifest, manifest_path


def load_candle_acquisition(path: str | Path) -> CandleAcquisitionManifest:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("candle acquisition manifest must be an object")
    required = {
        "schema",
        "acquisition_id",
        "symbol",
        "venue",
        "endpoint",
        "interval",
        "requested_start_ms",
        "requested_end_ms",
        "row_count",
        "csv_sha256",
        "csv_path",
        "request_count",
        "requests_sha256",
        "requests",
    }
    if set(payload) != required:
        raise ValueError("invalid candle acquisition manifest fields")
    manifest = CandleAcquisitionManifest(
        schema=str(payload["schema"]),
        acquisition_id=str(payload["acquisition_id"]),
        symbol=str(payload["symbol"]),
        venue=str(payload["venue"]),
        endpoint=str(payload["endpoint"]),
        interval=str(payload["interval"]),
        requested_start_ms=int(payload["requested_start_ms"]),
        requested_end_ms=int(payload["requested_end_ms"]),
        row_count=int(payload["row_count"]),
        csv_sha256=str(payload["csv_sha256"]),
        csv_path=str(payload["csv_path"]),
        request_count=int(payload["request_count"]),
        requests_sha256=str(payload["requests_sha256"]),
    )
    if manifest.schema != CANDLE_ACQUISITION_SCHEMA:
        raise ValueError("unsupported candle acquisition schema")
    if manifest.venue not in {item.value for item in CandleVenue}:
        raise ValueError("unsupported candle venue")
    if manifest.endpoint != ENDPOINTS[CandleVenue(manifest.venue)]:
        raise ValueError("candle acquisition endpoint does not match venue")
    csv_path = Path(manifest.csv_path)
    if not csv_path.is_file() or sha256_file(csv_path) != manifest.csv_sha256:
        raise ValueError("candle acquisition CSV integrity check failed")
    candles = validate_interval_window(
        load_csv(csv_path),
        manifest.interval,
        manifest.requested_start_ms,
        manifest.requested_end_ms,
    )
    if len(candles) != manifest.row_count:
        raise ValueError("candle acquisition row count does not match manifest")
    requests = payload["requests"]
    if not isinstance(requests, list):
        raise ValueError("candle acquisition requests must be an array")
    if len(requests) != manifest.request_count:
        raise ValueError("candle acquisition request count does not match manifest")
    if sha256_text(canonical_json(requests)) != manifest.requests_sha256:
        raise ValueError("candle acquisition request provenance SHA-256 mismatch")
    return manifest
