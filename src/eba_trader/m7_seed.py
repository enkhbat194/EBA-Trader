from __future__ import annotations

import argparse
import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from .data_policy import allowed_source_close_times, allowed_source_gap_ranges
from .derivatives_archive_seed import ARCHIVE_DATASETS, _download_month, month_range
from .derivatives_audit import _save_funding_csv, _save_kline_csv
from .history import fetch_binance_klines, parse_utc, save_csv, validate_interval_window
from .holdout_guard import assert_not_first_cycle_oos_overlap
from .m7_funding_flow_policy import (
    CHALLENGE_END_EXCLUSIVE,
    CHALLENGE_START,
    DISCOVERY_END_EXCLUSIVE,
    DISCOVERY_START,
    FUNDING_SHA256,
    FUTURES_SHA256,
    SPOT_CHALLENGE_SHA256,
    SPOT_RESEARCH_SHA256,
    sha256_file,
)
from .study_policy import FIRST_CYCLE_INTERVAL, FIRST_CYCLE_SYMBOL

M7_ARCHIVE_DATASETS = tuple(
    dataset for dataset in ARCHIVE_DATASETS if dataset.name in {"funding", "futures"}
)


def _hash_matches(path: Path, expected: str) -> bool:
    return path.is_file() and sha256_file(path) == expected


def _guard_window(start: str, end: str, *, context: str) -> tuple[int, int]:
    start_ms = parse_utc(start)
    end_ms = parse_utc(end)
    assert_not_first_cycle_oos_overlap(
        symbol=FIRST_CYCLE_SYMBOL,
        interval=FIRST_CYCLE_INTERVAL,
        start_ms=start_ms,
        end_ms=end_ms,
        context=context,
    )
    return start_ms, end_ms


def _seed_derivatives(cache: Path, *, workers: int) -> dict[str, object]:
    if workers < 1 or workers > 12:
        raise ValueError("workers must be between 1 and 12")
    periods = month_range()
    report: dict[str, object] = {}
    expected_hashes = {"funding": FUNDING_SHA256, "futures": FUTURES_SHA256}

    for dataset in M7_ARCHIVE_DATASETS:
        cache_path = cache / dataset.cache_filename
        if _hash_matches(cache_path, expected_hashes[dataset.name]):
            report[dataset.name] = {"status": "REUSED_FROZEN_HASH", "path": str(cache_path)}
            continue

        futures_map = {}
        with ThreadPoolExecutor(max_workers=workers) as executor:
            for year, month in periods:
                future = executor.submit(_download_month, dataset, year, month)
                futures_map[future] = (year, month)
            downloaded = [future.result() for future in as_completed(futures_map)]

        missing = [
            f"{year:04d}-{month:02d}"
            for year, month, _, checksum, _, _ in downloaded
            if checksum is None
        ]
        if missing:
            raise RuntimeError(
                f"M7 frozen {dataset.name} archive has missing months: {', '.join(sorted(missing))}"
            )

        if dataset.funding:
            rows = [item for *_, monthly_rows in sorted(downloaded) for item in monthly_rows]
            rows.sort(key=lambda item: item.funding_time_ms)
            _save_funding_csv(rows, cache_path)
        else:
            rows = [item for *_, monthly_rows in sorted(downloaded) for item in monthly_rows]
            rows.sort(key=lambda item: item.open_time_ms)
            _save_kline_csv(rows, cache_path)

        actual = sha256_file(cache_path)
        expected = expected_hashes[dataset.name]
        if actual != expected:
            raise RuntimeError(
                f"M7 frozen {dataset.name} hash mismatch after checksum-verified "
                f"archive seed: {actual}"
            )
        report[dataset.name] = {
            "status": "SEEDED_AND_FROZEN_HASH_VERIFIED",
            "path": str(cache_path),
            "sha256": actual,
            "months": len(periods),
        }
    return report


def _seed_spot(spot_cache: Path) -> dict[str, object]:
    research_path = spot_cache / "btcusdt_15m_research.csv"
    challenge_path = spot_cache / "btcusdt_15m_validation.csv"
    report: dict[str, object] = {}
    gaps = allowed_source_gap_ranges(FIRST_CYCLE_SYMBOL, FIRST_CYCLE_INTERVAL)
    close_times = allowed_source_close_times(FIRST_CYCLE_SYMBOL, FIRST_CYCLE_INTERVAL)

    windows = (
        (
            "research",
            research_path,
            SPOT_RESEARCH_SHA256,
            DISCOVERY_START,
            DISCOVERY_END_EXCLUSIVE,
        ),
        (
            "challenge",
            challenge_path,
            SPOT_CHALLENGE_SHA256,
            CHALLENGE_START,
            CHALLENGE_END_EXCLUSIVE,
        ),
    )
    for name, path, expected_hash, start, end in windows:
        if _hash_matches(path, expected_hash):
            report[name] = {"status": "REUSED_FROZEN_HASH", "path": str(path)}
            continue
        start_ms, end_ms = _guard_window(start, end, context=f"M7 {name} Spot seed")
        candles = fetch_binance_klines(
            FIRST_CYCLE_SYMBOL,
            FIRST_CYCLE_INTERVAL,
            start_ms,
            end_ms,
        )
        validated = validate_interval_window(
            candles,
            FIRST_CYCLE_INTERVAL,
            start_ms,
            end_ms,
            allowed_missing_ranges=gaps,
            allowed_close_times=close_times,
        )
        save_csv(validated, path)
        actual = sha256_file(path)
        if actual != expected_hash:
            raise RuntimeError(
                f"M7 frozen Spot {name} hash mismatch after source download: {actual}"
            )
        report[name] = {
            "status": "SEEDED_AND_FROZEN_HASH_VERIFIED",
            "path": str(path),
            "sha256": actual,
            "rows": len(validated),
        }
    return report


def ensure_m7_frozen_inputs(
    *,
    m6_dir: str | Path = "data/cache/m6",
    spot_dir: str | Path = "data/cache/m2",
    manifest_path: str | Path = "data/cache/m7/input_seed_manifest.json",
    workers: int = 6,
) -> dict[str, object]:
    _guard_window(DISCOVERY_START, DISCOVERY_END_EXCLUSIVE, context="M7 discovery seed guard")
    _guard_window(CHALLENGE_START, CHALLENGE_END_EXCLUSIVE, context="M7 challenge seed guard")
    m6_cache = Path(m6_dir)
    spot_cache = Path(spot_dir)
    m6_cache.mkdir(parents=True, exist_ok=True)
    spot_cache.mkdir(parents=True, exist_ok=True)

    manifest: dict[str, object] = {
        "phase": "m7_frozen_input_seed",
        "derivatives": _seed_derivatives(m6_cache, workers=workers),
        "spot": _seed_spot(spot_cache),
        "oos_2025": "LOCKED_NOT_ACCESSED",
    }
    output = Path(manifest_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed and verify only the four frozen M7 inputs")
    parser.add_argument("--m6-dir", default="data/cache/m6")
    parser.add_argument("--spot-dir", default="data/cache/m2")
    parser.add_argument("--manifest", default="data/cache/m7/input_seed_manifest.json")
    parser.add_argument("--workers", type=int, default=6)
    args = parser.parse_args()
    manifest = ensure_m7_frozen_inputs(
        m6_dir=args.m6_dir,
        spot_dir=args.spot_dir,
        manifest_path=args.manifest,
        workers=args.workers,
    )
    print("M7 frozen input seed complete")
    for family, section in (("derivatives", manifest["derivatives"]), ("spot", manifest["spot"])):
        for name, item in section.items():
            print(family, name, item["status"])
    print("2025 OOS remains LOCKED_NOT_ACCESSED")


if __name__ == "__main__":
    main()
