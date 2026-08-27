from __future__ import annotations

import csv
import hashlib
import io
import tempfile
import time
import zipfile
from collections.abc import Callable
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from .orderflow_acquisition import (
    AggregateTradeDownload,
    OrderFlowVenue,
    RequestProvenance,
)
from .orderflow_dataset import normalize_aggregate_trades, parse_binance_agg_trade

BINANCE_PUBLIC_DATA_BASE = "https://data.binance.vision"
USDM_DAILY_AGG_TRADES_ROOT = (
    f"{BINANCE_PUBLIC_DATA_BASE}/data/futures/um/daily/aggTrades"
)
_ARCHIVE_USER_AGENT = "EBA-Trader/0.1 orderflow-archive-research"
_ARCHIVE_CHUNK_SIZE = 1024 * 1024

ArchiveFetchBytes = Callable[[str], bytes]


def usdm_daily_agg_trades_url(symbol: str, day: date) -> str:
    normalized = symbol.strip().upper()
    if not normalized or not normalized.isalnum():
        raise ValueError("symbol must be non-empty alphanumeric text")
    stamp = day.isoformat()
    filename = f"{normalized}-aggTrades-{stamp}.zip"
    return f"{USDM_DAILY_AGG_TRADES_ROOT}/{normalized}/{filename}"


def _days_covering(start_ms: int, end_ms: int) -> tuple[date, ...]:
    if start_ms < 0 or end_ms <= start_ms:
        raise ValueError("invalid aggregate-trade archive time range")
    first = datetime.fromtimestamp(start_ms / 1000, tz=UTC).date()
    last = datetime.fromtimestamp((end_ms - 1) / 1000, tz=UTC).date()
    days: list[date] = []
    current = first
    while current <= last:
        days.append(current)
        current += timedelta(days=1)
    return tuple(days)


def _retry_delay_seconds(error: HTTPError, attempt: int, backoff_seconds: float) -> float:
    retry_after = error.headers.get("Retry-After") if error.headers is not None else None
    if retry_after:
        try:
            return min(max(float(retry_after), 0.0), 120.0)
        except ValueError:
            pass
    return min(backoff_seconds * (2**attempt), 30.0)


def _request_bytes(
    url: str,
    *,
    request_timeout: float,
    max_retries: int,
    backoff_seconds: float,
) -> bytes:
    request = Request(url, headers={"User-Agent": _ARCHIVE_USER_AGENT})
    for attempt in range(max_retries + 1):
        try:
            with urlopen(request, timeout=request_timeout) as response:  # noqa: S310
                return response.read()
        except HTTPError as error:
            retryable = error.code in {418, 429} or 500 <= error.code < 600
            if not retryable or attempt >= max_retries:
                raise RuntimeError(f"Binance archive HTTP error {error.code}") from error
            time.sleep(_retry_delay_seconds(error, attempt, backoff_seconds))
        except (URLError, TimeoutError) as error:
            if attempt >= max_retries:
                raise RuntimeError(
                    "Binance archive network request failed after retries"
                ) from error
            time.sleep(min(backoff_seconds * (2**attempt), 30.0))
    raise RuntimeError("Unreachable archive retry state")


def _parse_checksum(payload: bytes, expected_filename: str) -> str:
    try:
        text = payload.decode("utf-8").strip()
    except UnicodeDecodeError as exc:
        raise RuntimeError("Binance archive checksum is not UTF-8") from exc
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    if len(lines) != 1:
        raise RuntimeError("Binance archive checksum must contain exactly one record")
    parts = lines[0].split()
    if len(parts) < 2:
        raise RuntimeError("Binance archive checksum record is malformed")
    digest = parts[0].lower()
    filename = parts[-1].lstrip("*")
    if filename != expected_filename:
        raise RuntimeError("Binance archive checksum filename does not match requested archive")
    if len(digest) != 64 or any(char not in "0123456789abcdef" for char in digest):
        raise RuntimeError("Binance archive checksum is not SHA-256")
    return digest


def _download_archive_to_temp(
    url: str,
    *,
    expected_sha256: str,
    request_timeout: float,
    max_retries: int,
    backoff_seconds: float,
) -> Path:
    request = Request(url, headers={"User-Agent": _ARCHIVE_USER_AGENT})
    last_error: Exception | None = None
    for attempt in range(max_retries + 1):
        temp_path: Path | None = None
        try:
            digest = hashlib.sha256()
            with tempfile.NamedTemporaryFile(
                prefix="eba-binance-archive-",
                suffix=".zip",
                delete=False,
            ) as handle:
                temp_path = Path(handle.name)
                with urlopen(request, timeout=request_timeout) as response:  # noqa: S310
                    while True:
                        chunk = response.read(_ARCHIVE_CHUNK_SIZE)
                        if not chunk:
                            break
                        digest.update(chunk)
                        handle.write(chunk)
            if digest.hexdigest() != expected_sha256:
                temp_path.unlink(missing_ok=True)
                raise RuntimeError("Binance archive ZIP SHA-256 mismatch")
            return temp_path
        except HTTPError as error:
            if temp_path is not None:
                temp_path.unlink(missing_ok=True)
            last_error = error
            retryable = error.code in {418, 429} or 500 <= error.code < 600
            if not retryable or attempt >= max_retries:
                raise RuntimeError(f"Binance archive HTTP error {error.code}") from error
            time.sleep(_retry_delay_seconds(error, attempt, backoff_seconds))
        except (URLError, TimeoutError) as error:
            if temp_path is not None:
                temp_path.unlink(missing_ok=True)
            last_error = error
            if attempt >= max_retries:
                raise RuntimeError(
                    "Binance archive network request failed after retries"
                ) from error
            time.sleep(min(backoff_seconds * (2**attempt), 30.0))
    raise RuntimeError("Binance archive download failed") from last_error


def _bytes_archive_to_temp(payload: bytes, expected_sha256: str) -> Path:
    if hashlib.sha256(payload).hexdigest() != expected_sha256:
        raise RuntimeError("Binance archive ZIP SHA-256 mismatch")
    with tempfile.NamedTemporaryFile(
        prefix="eba-binance-archive-",
        suffix=".zip",
        delete=False,
    ) as handle:
        handle.write(payload)
        return Path(handle.name)


def _maker_flag(raw: str) -> bool:
    value = raw.strip().lower()
    if value == "true":
        return True
    if value == "false":
        return False
    raise RuntimeError("Binance archive maker flag is not boolean")


def _is_header(row: list[str]) -> bool:
    if not row:
        return False
    return row[0].strip().lower() in {
        "agg_trade_id",
        "aggregate_trade_id",
        "aggregate tradeid",
    }


def _read_archive_window(
    path: Path,
    *,
    expected_csv_name: str,
    start_ms: int,
    end_ms: int,
) -> tuple[dict[str, object], ...]:
    try:
        archive = zipfile.ZipFile(path)
    except (OSError, zipfile.BadZipFile) as exc:
        raise RuntimeError("Binance aggregate-trade archive is not a valid ZIP") from exc
    with archive:
        members = [item for item in archive.infolist() if not item.is_dir()]
        if len(members) != 1 or members[0].filename != expected_csv_name:
            raise RuntimeError("Binance aggregate-trade archive contains unexpected files")
        payloads: list[dict[str, object]] = []
        with (
            archive.open(members[0], "r") as raw_handle,
            io.TextIOWrapper(raw_handle, encoding="utf-8-sig", newline="") as text_handle,
        ):
            reader = csv.reader(text_handle)
            for line_number, row in enumerate(reader, start=1):
                if not row:
                    raise RuntimeError(
                        f"Binance aggregate-trade archive has blank row {line_number}"
                    )
                if line_number == 1 and _is_header(row):
                    continue
                if len(row) != 7:
                    raise RuntimeError(
                        "Binance aggregate-trade archive row "
                        f"{line_number} has {len(row)} columns"
                    )
                try:
                    aggregate_trade_id = int(row[0])
                    price = row[1].strip()
                    quantity = row[2].strip()
                    int(row[3])
                    int(row[4])
                    timestamp_ms = int(row[5])
                    buyer_is_maker = _maker_flag(row[6])
                except ValueError as exc:
                    raise RuntimeError(
                        f"Binance aggregate-trade archive row {line_number} is malformed"
                    ) from exc
                if timestamp_ms >= end_ms:
                    break
                if timestamp_ms < start_ms:
                    continue
                payload: dict[str, object] = {
                    "a": aggregate_trade_id,
                    "p": price,
                    "q": quantity,
                    "T": timestamp_ms,
                    "m": buyer_is_maker,
                }
                parse_binance_agg_trade(payload)
                payloads.append(payload)
    return tuple(payloads)


def fetch_binance_usdm_agg_trades_archive(
    symbol: str,
    start_ms: int,
    end_ms: int,
    *,
    request_timeout: float = 30.0,
    max_retries: int = 5,
    backoff_seconds: float = 0.5,
    fetch_bytes: ArchiveFetchBytes | None = None,
) -> AggregateTradeDownload:
    normalized = symbol.strip().upper()
    if not normalized or not normalized.isalnum():
        raise ValueError("symbol must be non-empty alphanumeric text")
    if start_ms < 0 or end_ms <= start_ms:
        raise ValueError("invalid aggregate-trade archive time range")
    if max_retries < 0:
        raise ValueError("max_retries cannot be negative")
    if backoff_seconds < 0:
        raise ValueError("backoff_seconds cannot be negative")

    all_payloads: list[dict[str, object]] = []
    provenance: list[RequestProvenance] = []
    for day in _days_covering(start_ms, end_ms):
        url = usdm_daily_agg_trades_url(normalized, day)
        filename = url.rsplit("/", 1)[-1]
        checksum_url = f"{url}.CHECKSUM"
        if fetch_bytes is None:
            checksum_bytes = _request_bytes(
                checksum_url,
                request_timeout=request_timeout,
                max_retries=max_retries,
                backoff_seconds=backoff_seconds,
            )
        else:
            checksum_bytes = fetch_bytes(checksum_url)
        expected_sha256 = _parse_checksum(checksum_bytes, filename)

        temp_path: Path | None = None
        try:
            if fetch_bytes is None:
                temp_path = _download_archive_to_temp(
                    url,
                    expected_sha256=expected_sha256,
                    request_timeout=request_timeout,
                    max_retries=max_retries,
                    backoff_seconds=backoff_seconds,
                )
            else:
                temp_path = _bytes_archive_to_temp(fetch_bytes(url), expected_sha256)
            page = _read_archive_window(
                temp_path,
                expected_csv_name=filename.removesuffix(".zip") + ".csv",
                start_ms=start_ms,
                end_ms=end_ms,
            )
        finally:
            if temp_path is not None:
                temp_path.unlink(missing_ok=True)

        typed_page = tuple(dict(item) for item in page)
        records = tuple(parse_binance_agg_trade(item) for item in typed_page)
        provenance.append(
            RequestProvenance(
                endpoint=url,
                mode="archive_daily_verified",
                params=(("date", day.isoformat()), ("sha256", expected_sha256)),
                response_count=len(records),
                first_trade_id=records[0].aggregate_trade_id if records else None,
                last_trade_id=records[-1].aggregate_trade_id if records else None,
                first_timestamp_ms=records[0].timestamp_ms if records else None,
                last_timestamp_ms=records[-1].timestamp_ms if records else None,
            )
        )
        all_payloads.extend(typed_page)

    records = normalize_aggregate_trades(tuple(all_payloads)) if all_payloads else ()
    if not records:
        raise RuntimeError("Binance historical archive returned no trades for requested window")
    return AggregateTradeDownload(
        symbol=normalized,
        venue=OrderFlowVenue.USD_M_FUTURES,
        start_ms=start_ms,
        end_ms=end_ms,
        payloads=tuple(
            {
                "a": record.aggregate_trade_id,
                "p": repr(record.price),
                "q": repr(record.quantity),
                "T": record.timestamp_ms,
                "m": record.aggressor.value == "sell",
            }
            for record in records
        ),
        requests=tuple(provenance),
        source_endpoint=USDM_DAILY_AGG_TRADES_ROOT,
    )
