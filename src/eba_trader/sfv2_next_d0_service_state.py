from __future__ import annotations

import subprocess
from collections.abc import Callable
from typing import Any

SERVICE_NAME = "eba-sfv2-next-d0-materialization.service"

Runner = Callable[..., subprocess.CompletedProcess[str]]


def _unavailable(reason: str) -> dict[str, Any]:
    return {"available": False, "reason": reason}


def _parse_systemctl_show(text: str) -> dict[str, str]:
    values: dict[str, str] = {}
    for raw_line in text.splitlines():
        if "=" not in raw_line:
            continue
        key, value = raw_line.split("=", 1)
        if key:
            values[key] = value
    return values


def _optional_int(value: str | None) -> int | None:
    if value is None or value == "":
        return None
    try:
        return int(value)
    except ValueError:
        return None


def read_sfv2_next_d0_service_state(
    *,
    service_name: str = SERVICE_NAME,
    runner: Runner | None = None,
) -> dict[str, Any]:
    """Return sanitized, read-only systemd state for the local next-D0 service."""

    invoke = runner or subprocess.run
    command = [
        "systemctl",
        "show",
        service_name,
        "--no-pager",
        "--property=LoadState,ActiveState,SubState,Result,ExecMainCode,ExecMainStatus,ExecMainStartTimestamp,ExecMainExitTimestamp",
    ]
    try:
        completed = invoke(
            command,
            capture_output=True,
            text=True,
            timeout=2,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return _unavailable("systemd_query_failed")
    if completed.returncode != 0:
        return _unavailable("systemd_query_failed")

    values = _parse_systemctl_show(completed.stdout)
    if values.get("LoadState") != "loaded":
        return _unavailable("service_not_loaded")

    return {
        "available": True,
        "service": service_name,
        "loadState": values.get("LoadState"),
        "activeState": values.get("ActiveState"),
        "subState": values.get("SubState"),
        "result": values.get("Result"),
        "execMainCode": values.get("ExecMainCode") or None,
        "execMainStatus": _optional_int(values.get("ExecMainStatus")),
        "execMainStartTimestamp": values.get("ExecMainStartTimestamp") or None,
        "execMainExitTimestamp": values.get("ExecMainExitTimestamp") or None,
    }
