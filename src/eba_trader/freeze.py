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


def freeze_oos_candidate(
    *,
    development_report_path: str | Path = "artifacts/m2_development_evidence.json",
    freeze_path: str | Path = "artifacts/m2_frozen_candidate.json",
) -> dict[str, object]:
    development_path = Path(development_report_path)
    if not development_path.exists():
        raise FileNotFoundError("Development evidence report does not exist")

    development = json.loads(development_path.read_text(encoding="utf-8"))
    if development.get("oos_2025") != "LOCKED_NOT_ACCESSED":
        raise ValueError("Development report does not prove that 2025 OOS stayed locked")

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

    payload: dict[str, object] = {
        "decision": "retain_for_frozen_oos",
        "source": "development_report.frozen_baseline",
        "fast_ema": fast_ema,
        "slow_ema": slow_ema,
        "development_report": str(development_path),
        "development_report_sha256": file_sha256(development_path),
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
) -> dict[str, object]:
    path = Path(freeze_path)
    if not path.exists():
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

    development = json.loads(development_path.read_text(encoding="utf-8"))
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
        description="Freeze the predeclared Trend baseline before opening the 2025 OOS holdout"
    )
    parser.parse_args()

    payload = freeze_oos_candidate()
    print(
        f"frozen fast={payload['fast_ema']} slow={payload['slow_ema']} "
        f"development_sha256={payload['development_report_sha256']}"
    )
    print("source=development_report.frozen_baseline")
    print("retuning_after_freeze=FORBIDDEN")
    print("freeze=artifacts/m2_frozen_candidate.json")
