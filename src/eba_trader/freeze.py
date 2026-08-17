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
    fast_ema: int,
    slow_ema: int,
    development_report_path: str | Path = "artifacts/m2_development_evidence.json",
    freeze_path: str | Path = "artifacts/m2_frozen_candidate.json",
) -> dict[str, object]:
    if fast_ema <= 1 or slow_ema <= fast_ema:
        raise ValueError("Require 1 < fast_ema < slow_ema")

    development_path = Path(development_report_path)
    if not development_path.exists():
        raise FileNotFoundError("Development evidence report does not exist")

    development = json.loads(development_path.read_text(encoding="utf-8"))
    if development.get("oos_2025") != "LOCKED_NOT_ACCESSED":
        raise ValueError("Development report does not prove that 2025 OOS stayed locked")

    output = Path(freeze_path)
    if output.exists():
        raise RuntimeError("Frozen candidate already exists; do not overwrite before OOS")

    payload: dict[str, object] = {
        "decision": "retain_for_frozen_oos",
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
    if not development_path.exists():
        raise FileNotFoundError("Development evidence referenced by freeze file is missing")

    expected = str(payload.get("development_report_sha256", ""))
    actual = file_sha256(development_path)
    if not expected or actual != expected:
        raise RuntimeError("Development evidence changed after candidate freeze")

    fast = int(payload["fast_ema"])
    slow = int(payload["slow_ema"])
    if fast <= 1 or slow <= fast:
        raise ValueError("Frozen EMA parameters are invalid")
    return payload


def freeze_candidate_cli() -> None:
    parser = argparse.ArgumentParser(
        description="Freeze the final Trend candidate before opening the 2025 OOS holdout"
    )
    parser.add_argument("--fast", type=int, required=True)
    parser.add_argument("--slow", type=int, required=True)
    args = parser.parse_args()

    payload = freeze_oos_candidate(fast_ema=args.fast, slow_ema=args.slow)
    print(
        f"frozen fast={payload['fast_ema']} slow={payload['slow_ema']} "
        f"development_sha256={payload['development_report_sha256']}"
    )
    print("retuning_after_freeze=FORBIDDEN")
    print("freeze=artifacts/m2_frozen_candidate.json")
