from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

DEFAULT_PROOF_PATH = Path("/var/lib/eba-trader/proofs/latest.json")
_BLOCKED_KEYS = {
    "apikey",
    "apisecret",
    "secret",
    "sessiontoken",
    "token",
    "credentials",
}


def _sanitize(value: Any) -> Any:
    if isinstance(value, dict):
        result: dict[str, Any] = {}
        for key, item in value.items():
            normalized = str(key).replace("_", "").lower()
            if normalized in _BLOCKED_KEYS:
                continue
            result[str(key)] = _sanitize(item)
        return result
    if isinstance(value, list):
        return [_sanitize(item) for item in value]
    return value


def read_production_proof(path: str | Path | None = None) -> dict[str, Any]:
    chosen = Path(
        path
        or os.getenv("EBA_PRODUCTION_PROOF_FILE", "").strip()
        or DEFAULT_PROOF_PATH
    )
    if not chosen.is_file():
        return {
            "ok": True,
            "available": False,
            "localContractPassed": False,
            "productionSmokePassed": False,
            "liveExecutionAllowed": False,
        }
    try:
        payload = json.loads(chosen.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return {
            "ok": False,
            "available": False,
            "localContractPassed": False,
            "productionSmokePassed": False,
            "message": f"production proof unavailable: {exc}",
            "liveExecutionAllowed": False,
        }
    if not isinstance(payload, dict):
        return {
            "ok": False,
            "available": False,
            "localContractPassed": False,
            "productionSmokePassed": False,
            "message": "production proof payload is not an object",
            "liveExecutionAllowed": False,
        }

    sanitized = _sanitize(payload)
    if not isinstance(sanitized, dict):  # pragma: no cover - defensive
        raise RuntimeError("sanitized production proof is not an object")
    sanitized.update(
        {
            "ok": True,
            "available": True,
            "liveExecutionAllowed": False,
        }
    )
    return sanitized
