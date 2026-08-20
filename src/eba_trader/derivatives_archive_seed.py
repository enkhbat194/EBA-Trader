from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import time
import zipfile
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from .derivatives_audit import (
    DerivativeKline,
    FundingRecord,
    _assert_development_range,
    _kline_from_row,
    _save_funding_csv,
    _save_kline_csv,
)
from .derivatives_audit_policy import AUDIT_END_EXCLUSIVE, AUDIT_START, INTERVAL, SYMBOL
from .history import parse_utc

ARCHIVE_BASE_URL = "https://data.binance.vision/data/futures/um/monthly"
ARCHIVE_WORKERS = 6


@dataclass(frozen=True, slots=True)
class ArchiveDataset:
    name: str
    path_segment: str
    interval: str | None
    cache_filename: str
    futures_activity: bool = False
    funding: bool = False


ARCHIVE_DATASETS = (
    ArchiveDataset(
        "funding",
        "fundingRate",
        None,
        "btcusdt_usdm_funding_2021_2024.csv",
        funding=True,
    ),
    ArchiveDataset(
        "premium",
        "premiumIndexKlines",
        INTERVAL,
        "btcusdt_usdm_premium_index_15m_2021_2024.csv",
    ),
    ArchiveDataset(
        "futures",
        "klines",
        INTERVAL,
        "btcusdt_usdm_perpetual_15m_2021_2024.csv",
        futures_activity=True,
    ),
    ArchiveDataset(
        "index",
        "indexPriceKlines",
        INTERVAL,
        "btcusdt_usdm_index_price_15m_2021_2024.csv",
    ),
)


def month_range() -> tuple[tuple[int, int], ...]:
    result: list[tuple[int, int]] = []
    year, month = 2021, 1
    while (year, month) < (2025, 1):
        result.append((year, month))
        if month == 12:
            year += 1
            month = 1
        else:
            month += 1
    return tuple(result)


def archive_url(dataset: ArchiveDataset, year: int, month: int) -> str:
    stamp = f"{year:04d}-{month:02d}"
    if dataset.interval is None:
        filename = f"{SYMBOL}-{dataset.path_segment}-{stamp}.zip"
        return f"{ARCHIVE_BASE_URL}/{dataset.path_segment}/{SYMBOL}/{filename}"
    filename = f"{SYMBOL}-{dataset.interval}-{stamp}.zip"
    return (
        f"{ARCHIVE_BASE_URL}/{dataset.path_segment}/{SYMBOL}/{dataset.interval}/{filename}"
    )


def _request_bytes(
    url: str,
    *,
    allow_missing: bool,
    timeout: float = 30.0,
    max_retries: int = 4,
    backoff_seconds: float = 0.5,
) -> bytes | None:
    request = Request(url, headers={"User-Agent": "EBA-Trader-M6-Archive-Audit/1.0"})
    for attempt in range(max_retries + 1):
        try:
            with urlopen(request, timeout=timeout) as response:  # noqa: S310
                return response.read()
        except HTTPError as error:
            if error.code == 404 and allow_missing:
                return None
            retryable = error.code in {418, 429} or 500 <= error.code < 600
            if not retryable or attempt >= max_retries:
                raise RuntimeError(f"Binance Vision HTTP error {error.code}: {url}") from error
            time.sleep(min(backoff_seconds * (2**attempt), 30.0))
        except (URLError, TimeoutError) as error:
            if attempt >= max_retries:
                raise RuntimeError(f"Binance Vision request failed after retries: {url}") from error
            time.sleep(min(backoff_seconds * (2**attempt), 30.0))
    raise RuntimeError("Unreachable archive request retry state")


def _checksum_value(payload: bytes) -> str:
    text = payload.decode("utf-8-sig").strip()
    if not text:
        raise RuntimeError("Empty Binance Vision CHECKSUM file")
    token = text.split()[0].lower()
    if len(token) != 64 or any(char not in "0123456789abcdef" for char in token):
        raise RuntimeError("Invalid Binance Vision CHECKSUM format")
    return token


def _download_verified_archive(url: str) -> tuple[bytes, str] | None:
    archive = _request_bytes(url, allow_missing=True)
    if archive is None:
        return None
    checksum_payload = _request_bytes(url + ".CHECKSUM", allow_missing=False)
    if checksum_payload is None:
        raise RuntimeError(f"Missing checksum for existing Binance Vision archive: {url}")
    expected = _checksum_value(checksum_payload)
    actual = hashlib.sha256(archive).hexdigest()
    if actual != expected:
        raise RuntimeError(f"Binance Vision checksum mismatch: {url}")
    return archive, actual


def _csv_rows_from_zip(payload: bytes) -> list[list[str]]:
    try:
        with zipfile.ZipFile(io.BytesIO(payload)) as bundle:
            members = [name for name in bundle.namelist() if name.lower().endswith(".csv")]
            if len(members) != 1:
                raise RuntimeError("Expected exactly one CSV inside Binance Vision ZIP")
            with bundle.open(members[0]) as raw:
                text = io.TextIOWrapper(raw, encoding="utf-8-sig", newline="")
                return [row for row in csv.reader(text) if row]
    except zipfile.BadZipFile as error:
        raise RuntimeError("Invalid Binance Vision ZIP payload") from error


def _is_integer(text: str) -> bool:
    try:
        int(text)
    except ValueError:
        return False
    return True


def parse_funding_archive(payload: bytes) -> list[FundingRecord]:
    rows = _csv_rows_from_zip(payload)
    parsed: list[FundingRecord] = []
    for row in rows:
        if not _is_integer(row[0].strip()):
            continue
        if len(row) < 3:
            raise RuntimeError("Funding archive row has fewer than three columns")
        interval_hours = row[1].strip()
        parsed.append(
            FundingRecord(
                symbol=SYMBOL,
                funding_time_ms=int(row[0]),
                funding_rate=float(row[2]),
                mark_price=None,
                rate_type=f"archive_interval_hours={interval_hours}",
            )
        )
    return parsed


def parse_kline_archive(
    payload: bytes,
    *,
    futures_activity: bool,
) -> list[DerivativeKline]:
    rows = _csv_rows_from_zip(payload)
    parsed: list[DerivativeKline] = []
    for row in rows:
        if not _is_integer(row[0].strip()):
            continue
        if len(row) < 7:
            raise RuntimeError("Kline archive row has fewer than seven columns")
        parsed.append(_kline_from_row(row, futures_activity=futures_activity))
    return parsed


def _download_month(
    dataset: ArchiveDataset,
    year: int,
    month: int,
) -> tuple[int, int, str, str | None, int, list[FundingRecord] | list[DerivativeKline]]:
    url = archive_url(dataset, year, month)
    downloaded = _download_verified_archive(url)
    if downloaded is None:
        return year, month, url, None, 0, []
    payload, checksum = downloaded
    if dataset.funding:
        rows: list[FundingRecord] | list[DerivativeKline] = parse_funding_archive(payload)
    else:
        rows = parse_kline_archive(payload, futures_activity=dataset.futures_activity)
    return year, month, url, checksum, len(payload), rows


def seed_binance_vision_archives(
    *,
    cache_dir: str | Path = "data/cache/m6",
    manifest_path: str | Path = "data/cache/m6/binance_vision_manifest.json",
    workers: int = ARCHIVE_WORKERS,
) -> dict[str, object]:
    start_ms = parse_utc(AUDIT_START)
    end_ms = parse_utc(AUDIT_END_EXCLUSIVE)
    _assert_development_range(start_ms, end_ms, context="M6 Binance Vision archive seed")
    if workers < 1 or workers > 12:
        raise ValueError("workers must be between 1 and 12")

    cache = Path(cache_dir)
    cache.mkdir(parents=True, exist_ok=True)
    periods = month_range()
    dataset_manifest: dict[str, object] = {}

    for dataset in ARCHIVE_DATASETS:
        collected_funding: list[FundingRecord] = []
        collected_klines: list[DerivativeKline] = []
        files: list[dict[str, object]] = []
        futures = {}
        with ThreadPoolExecutor(max_workers=workers) as executor:
            for year, month in periods:
                future = executor.submit(_download_month, dataset, year, month)
                futures[future] = (year, month)
            results = [future.result() for future in as_completed(futures)]

        for year, month, url, checksum, byte_count, rows in sorted(results):
            files.append(
                {
                    "period": f"{year:04d}-{month:02d}",
                    "url": url,
                    "status": "VERIFIED" if checksum is not None else "MISSING",
                    "sha256": checksum,
                    "zip_bytes": byte_count,
                    "row_count": len(rows),
                }
            )
            if dataset.funding:
                collected_funding.extend(rows)  # type: ignore[arg-type]
            else:
                collected_klines.extend(rows)  # type: ignore[arg-type]

        cache_path = cache / dataset.cache_filename
        if dataset.funding:
            collected_funding.sort(key=lambda item: item.funding_time_ms)
            _save_funding_csv(collected_funding, cache_path)
            total_rows = len(collected_funding)
        else:
            collected_klines.sort(key=lambda item: item.open_time_ms)
            _save_kline_csv(collected_klines, cache_path)
            total_rows = len(collected_klines)

        dataset_manifest[dataset.name] = {
            "cache_path": str(cache_path),
            "total_rows": total_rows,
            "verified_files": sum(item["status"] == "VERIFIED" for item in files),
            "missing_files": sum(item["status"] == "MISSING" for item in files),
            "files": files,
        }

    manifest: dict[str, object] = {
        "phase": "m6_binance_vision_archive_seed",
        "archive_base": ARCHIVE_BASE_URL,
        "audit_start": AUDIT_START,
        "audit_end_exclusive": AUDIT_END_EXCLUSIVE,
        "month_count": len(periods),
        "datasets": dataset_manifest,
        "integrity": "every_present_zip_verified_against_binance_vision_checksum",
        "oos_2025": "LOCKED_NOT_ACCESSED",
    }
    output = Path(manifest_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Seed frozen M6 2021-2024 caches from official Binance Vision monthly archives"
    )
    parser.add_argument("--cache-dir", default="data/cache/m6")
    parser.add_argument("--manifest", default="data/cache/m6/binance_vision_manifest.json")
    parser.add_argument("--workers", type=int, default=ARCHIVE_WORKERS)
    args = parser.parse_args()
    manifest = seed_binance_vision_archives(
        cache_dir=args.cache_dir,
        manifest_path=args.manifest,
        workers=args.workers,
    )
    print("M6 Binance Vision archive seed complete")
    for name, section in manifest["datasets"].items():
        print(
            name,
            "rows=", section["total_rows"],
            "verified_files=", section["verified_files"],
            "missing_files=", section["missing_files"],
        )
    print("2025 OOS remains LOCKED_NOT_ACCESSED")


if __name__ == "__main__":
    main()
