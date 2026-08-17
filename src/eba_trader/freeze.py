from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


def file_sha256(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _oos_cache_from_development(development: dict[str, object]) -> Path:
    try:
        symbol = str(development["symbol"]).lower()
        interval = str(development["interval"])
        data_dir = Path(str(development["data_dir"]))
    except KeyError as exc:
        raise ValueError("Development report is missing data location metadata") from exc
    if not symbol or not interval:
        raise ValueError("Development report data location metadata is invalid")
    return data_dir / f"{symbol}_{interval}_out_of_sample.csv"


def _assert_oos_cache_absent(development: dict[str, object]) -> Path:
    oos_cache = _oos_cache_from_development(development)
    if oos_cache.exists():
        raise RuntimeError(
            "Frozen 2025 OOS cache exists before authorized OOS opening; holdout is contaminated"
        )
    return oos_cache


def _load_eligible_verdict(
    *,
    verdict_path: str | Path,
    development_report_path: Path,
) -> dict[str, object]:
    path = Path(verdict_path)
    if not path.is_file():
        raise FileNotFoundError("Development screening verdict does not exist")
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("screening_version") != 1:
        raise ValueError("Unsupported development screening verdict version")
    if payload.get("status") != "ELIGIBLE_FOR_FROZEN_OOS":
        raise RuntimeError("Development cycle is not eligible for frozen OOS")
    if payload.get("all_gates_passed") is not True:
        raise RuntimeError("Development screening gates did not all pass")

    expected_report_hash = file_sha256(development_report_path)
    if payload.get("development_report_sha256") != expected_report_hash:
        raise RuntimeError("Development verdict does not match current development evidence")
    return payload


def freeze_oos_candidate(
    *,
    development_report_path: str | Path = "artifacts/m2_development_evidence.json",
    verdict_path: str | Path = "artifacts/m2_development_verdict.json",
    freeze_path: str | Path = "artifacts/m2_frozen_candidate.json",
) -> dict[str, object]:
    development_path = Path(development_report_path)
    if not development_path.is_file():
        raise FileNotFoundError("Development evidence report does not exist")

    development = json.loads(development_path.read_text(encoding="utf-8"))
    if development.get("oos_2025") != "LOCKED_NOT_ACCESSED":
        raise ValueError("Development report does not prove that 2025 OOS stayed locked")
    oos_cache = _assert_oos_cache_absent(development)
    verdict = _load_eligible_verdict(
        verdict_path=verdict_path,
        development_report_path=development_path,
    )

    baseline = development.get("frozen_baseline")
    if not isinstance(baseline, dict):
        raise ValueError("Development report does not contain a frozen baseline")
    try:
        fast_ema = int(baseline["fast_ema"])
        slow_ema = int(baseline["slow_ema"])
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError("Frozen baseline EMA parameters are invalid") from exc
    if fast_ema <= 1 or slow_ema <= fast_ema:
        raise ValueError("Frozen baseline requires 1 < fast_ema < slow_ema")

    output = Path(freeze_path)
    if output.exists():
        raise RuntimeError("Frozen candidate already exists; do not overwrite before OOS")

    verdict_file = Path(verdict_path)
    payload: dict[str, object] = {
        "decision": "retain_for_frozen_oos",
        "source": "development_report.frozen_baseline",
        "fast_ema": fast_ema,
        "slow_ema": slow_ema,
        "development_report": str(development_path),
        "development_report_sha256": file_sha256(development_path),
        "development_verdict": str(verdict_file),
        "development_verdict_sha256": file_sha256(verdict_file),
        "screening_status": verdict["status"],
        "oos_cache": str(oos_cache),
        "oos_cache_verified_absent_at_freeze": True,
        "oos_window": {
            "start": "2025-01-01",
            "end_exclusive": "2026-01-01",
        },
        "retuning_after_freeze": "forbidden",
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    return payload


def load_frozen_candidate(
    *,
    freeze_path: str | Path = "artifacts/m2_frozen_candidate.json",
    development_report_path: str | Path | None = None,
    verdict_path: str | Path | None = None,
) -> dict[str, object]:
    path = Path(freeze_path)
    if not path.is_file():
        raise FileNotFoundError("Frozen candidate does not exist")
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("decision") != "retain_for_frozen_oos":
        raise ValueError("Frozen candidate decision is invalid")

    development_path = Path(
        development_report_path
        if development_report_path is not None
        else str(payload.get("development_report", ""))
    )
    if not development_path.is_file():
        raise FileNotFoundError("Development evidence referenced by freeze file is missing")

    expected = str(payload.get("development_report_sha256", ""))
    actual = file_sha256(development_path)
    if not expected or actual != expected:
        raise RuntimeError("Development evidence changed after candidate freeze")

    resolved_verdict_path = Path(
        verdict_path
        if verdict_path is not None
        else str(payload.get("development_verdict", ""))
    )
    if not resolved_verdict_path.is_file():
        raise FileNotFoundError("Development verdict referenced by freeze file is missing")
    if payload.get("development_verdict_sha256") != file_sha256(resolved_verdict_path):
        raise RuntimeError("Development verdict changed after candidate freeze")
    _load_eligible_verdict(
        verdict_path=resolved_verdict_path,
        development_report_path=development_path,
    )

    development = json.loads(development_path.read_text(encoding="utf-8"))
    oos_cache = _assert_oos_cache_absent(development)
    if str(payload.get("oos_cache", "")) != str(oos_cache):
        raise RuntimeError("Frozen candidate OOS cache path no longer matches development evidence")
    if payload.get("oos_cache_verified_absent_at_freeze") is not True:
        raise RuntimeError("Frozen candidate lacks OOS cache absence proof")

    baseline = development.get("frozen_baseline")
    if not isinstance(baseline, dict):
        raise ValueError("Development report frozen baseline is missing")
    fast = int(payload["fast_ema"])
    slow = int(payload["slow_ema"])
    if fast != int(baseline["fast_ema"]) or slow != int(baseline["slow_ema"]):
        raise RuntimeError("Frozen candidate no longer matches development frozen baseline")
    if fast <= 1 or slow <= fast:
        raise ValueError("Frozen EMA parameters are invalid")
    return payload


def freeze_candidate_cli() -> None:
    parser = argparse.ArgumentParser(
        description="Freeze the screened predeclared Trend baseline before 2025 OOS"
    )
    parser.parse_args()

    payload = freeze_oos_candidate()
    print(
        f"frozen fast={payload['fast_ema']} slow={payload['slow_ema']} "
        f"development_sha256={payload['development_report_sha256']}"
    )
    print(f"screening={payload['screening_status']}")
    print("source=development_report.frozen_baseline")
    print("oos_cache_absent=VERIFIED")
    print("retuning_after_freeze=FORBIDDEN")
    print("freeze=artifacts/m2_frozen_candidate.json")
