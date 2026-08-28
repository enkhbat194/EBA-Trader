from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

DEFAULT_PROOF_PATH = Path("/var/lib/eba-trader/proofs/latest.json")
DEFAULT_FAST_RESTART_PROOF_PATH = Path("/var/lib/eba-trader/proofs/fast-restart.json")
DEFAULT_M5_ROBUSTNESS_PROOF_PATH = Path(
    "/var/lib/eba-trader/research/m5-absorption-robustness-latest.json"
)
DEFAULT_DEMO_EXECUTION_PROOF_PATH = Path("/var/lib/eba-trader/proofs/binance-demo-execution.json")
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


def _read_optional_json(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(payload, dict):
        return None
    sanitized = _sanitize(payload)
    return sanitized if isinstance(sanitized, dict) else None


def read_production_proof(
    path: str | Path | None = None,
    *,
    fast_restart_path: str | Path | None = None,
    m5_robustness_path: str | Path | None = None,
    demo_execution_path: str | Path | None = None,
) -> dict[str, Any]:
    chosen = Path(
        path
        or os.getenv("EBA_PRODUCTION_PROOF_FILE", "").strip()
        or DEFAULT_PROOF_PATH
    )
    chosen_fast = Path(
        fast_restart_path
        or os.getenv("EBA_FAST_RESTART_PROOF_FILE", "").strip()
        or DEFAULT_FAST_RESTART_PROOF_PATH
    )
    chosen_robustness = Path(
        m5_robustness_path
        or os.getenv("EBA_M5_ROBUSTNESS_STATUS", "").strip()
        or DEFAULT_M5_ROBUSTNESS_PROOF_PATH
    )
    chosen_demo_execution = Path(
        demo_execution_path
        or os.getenv("EBA_DEMO_EXECUTION_PROOF_FILE", "").strip()
        or DEFAULT_DEMO_EXECUTION_PROOF_PATH
    )
    fast_restart = _read_optional_json(chosen_fast) or {
        "phase": "WAITING_FOR_OPEN",
        "passed": False,
        "liveExecutionAllowed": False,
    }
    m5_robustness = _read_optional_json(chosen_robustness) or {
        "phase": "WAITING",
        "complete": False,
        "robustnessVerified": False,
        "developmentEvidenceOnly": True,
        "edgeClaimAllowed": False,
        "promotionAuthority": False,
        "frozenOosOpened": False,
        "m5FrozenOosOpened": False,
        "liveExecutionAllowed": False,
    }
    demo_execution = _read_optional_json(chosen_demo_execution) or {
        "phase": "NOT_RUN",
        "passed": False,
        "environment": "demo",
        "liveExecutionAllowed": False,
    }

    sidecars = {
        "fastRestart": fast_restart,
        "m5Robustness": m5_robustness,
        "demoExecution": demo_execution,
    }

    if not chosen.is_file():
        return {
            "ok": True,
            "available": False,
            "localContractPassed": False,
            "productionSmokePassed": False,
            **sidecars,
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
            **sidecars,
            "message": f"production proof unavailable: {exc}",
            "liveExecutionAllowed": False,
        }
    if not isinstance(payload, dict):
        return {
            "ok": False,
            "available": False,
            "localContractPassed": False,
            "productionSmokePassed": False,
            **sidecars,
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
            **sidecars,
            "liveExecutionAllowed": False,
        }
    )
    return sanitized
