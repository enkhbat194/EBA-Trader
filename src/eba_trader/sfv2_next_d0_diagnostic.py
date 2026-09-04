from __future__ import annotations

import json
import os
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

DIAGNOSTIC_SCHEMA = "sfv2_next_d0_materialization_diagnostic_v1"
DEFAULT_DIAGNOSTIC_PATH = Path(
    "/var/lib/eba-trader/research/sfv2-next-d0-materialization-diagnostic.json"
)
ALLOWED_PHASES = {
    "STARTING",
    "BUILDING",
    "SUCCEEDED",
    "FAILED",
    "DEFERRED",
    "ALREADY_COMPLETE",
}
ALLOWED_FAILURE_CLASSES = {
    "none",
    "archive_network",
    "archive_checksum",
    "candle_network",
    "boundary_guard",
    "data_integrity",
    "builder_contract_changed",
    "plan_contract_changed",
    "killed_or_oom",
    "terminated",
    "python_runtime_failure",
    "unknown",
}


def _atomic_write(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    fd, temp_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_name, path)
    finally:
        Path(temp_name).unlink(missing_ok=True)


def write_next_d0_materialization_diagnostic(
    *,
    phase: str,
    failure_class: str = "none",
    exit_code: int = 0,
    production_build_sha: str,
    builder_contract_sha256: str | None,
    path: str | Path = DEFAULT_DIAGNOSTIC_PATH,
) -> dict[str, Any]:
    if phase not in ALLOWED_PHASES:
        raise ValueError("unsupported next D0 diagnostic phase")
    if failure_class not in ALLOWED_FAILURE_CLASSES:
        raise ValueError("unsupported next D0 diagnostic failure class")
    if phase == "FAILED" and failure_class == "none":
        raise ValueError("failed next D0 diagnostic requires a failure class")
    if phase != "FAILED" and failure_class != "none":
        raise ValueError("non-failed next D0 diagnostic cannot carry a failure class")
    if isinstance(exit_code, bool) or not isinstance(exit_code, int) or not 0 <= exit_code <= 255:
        raise ValueError("next D0 diagnostic exit code must be 0..255")
    if phase == "FAILED" and exit_code == 0:
        raise ValueError("failed next D0 diagnostic requires a nonzero exit code")
    if phase != "FAILED" and exit_code != 0:
        raise ValueError("non-failed next D0 diagnostic requires exit code zero")
    build = production_build_sha.strip()
    if len(build) != 40 or any(char not in "0123456789abcdef" for char in build.lower()):
        raise ValueError("next D0 diagnostic production build SHA is invalid")
    contract = builder_contract_sha256.strip() if builder_contract_sha256 else None
    if contract is not None and (
        len(contract) != 64
        or any(char not in "0123456789abcdef" for char in contract.lower())
    ):
        raise ValueError("next D0 diagnostic builder contract SHA is invalid")

    payload: dict[str, Any] = {
        "schema": DIAGNOSTIC_SCHEMA,
        "phase": phase,
        "failureClass": failure_class,
        "exitCode": exit_code,
        "productionBuildSha": build,
        "builderContractSha256": contract,
        "updatedAt": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        "performanceEvaluationAllowed": False,
        "verificationAuthority": False,
        "d1Opened": False,
        "frozenOosOpened": False,
        "sf4DataAccessAllowed": False,
        "liveExecutionAllowed": False,
        "realExecutionAllowed": False,
    }
    _atomic_write(Path(path), payload)
    return payload


def read_next_d0_materialization_diagnostic(
    path: str | Path = DEFAULT_DIAGNOSTIC_PATH,
) -> dict[str, Any] | None:
    selected = Path(path)
    if not selected.is_file():
        return None
    try:
        payload = json.loads(selected.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(payload, dict):
        return None
    required = {
        "schema",
        "phase",
        "failureClass",
        "exitCode",
        "productionBuildSha",
        "builderContractSha256",
        "updatedAt",
        "performanceEvaluationAllowed",
        "verificationAuthority",
        "d1Opened",
        "frozenOosOpened",
        "sf4DataAccessAllowed",
        "liveExecutionAllowed",
        "realExecutionAllowed",
    }
    if set(payload) != required or payload.get("schema") != DIAGNOSTIC_SCHEMA:
        return None
    if payload.get("phase") not in ALLOWED_PHASES:
        return None
    if payload.get("failureClass") not in ALLOWED_FAILURE_CLASSES:
        return None
    if any(
        payload.get(key) is not False
        for key in (
            "performanceEvaluationAllowed",
            "verificationAuthority",
            "d1Opened",
            "frozenOosOpened",
            "sf4DataAccessAllowed",
            "liveExecutionAllowed",
            "realExecutionAllowed",
        )
    ):
        return None
    return payload
