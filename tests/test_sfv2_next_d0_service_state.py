from __future__ import annotations

import subprocess

from eba_trader.sfv2_next_d0_service_state import read_sfv2_next_d0_service_state


def test_service_state_reports_sanitized_running_state() -> None:
    def runner(*args, **kwargs):  # type: ignore[no-untyped-def]
        return subprocess.CompletedProcess(
            args=args[0],
            returncode=0,
            stdout=(
                "LoadState=loaded\n"
                "ActiveState=activating\n"
                "SubState=start\n"
                "Result=success\n"
                "ExecMainCode=0\n"
                "ExecMainStatus=0\n"
                "ExecMainStartTimestamp=Fri 2026-09-04 23:20:00 +08\n"
                "ExecMainExitTimestamp=\n"
            ),
            stderr="",
        )

    state = read_sfv2_next_d0_service_state(runner=runner)

    assert state == {
        "available": True,
        "service": "eba-sfv2-next-d0-materialization.service",
        "loadState": "loaded",
        "activeState": "activating",
        "subState": "start",
        "result": "success",
        "execMainCode": "0",
        "execMainStatus": 0,
        "execMainStartTimestamp": "Fri 2026-09-04 23:20:00 +08",
        "execMainExitTimestamp": None,
    }


def test_service_state_fails_closed_when_systemd_query_fails() -> None:
    def runner(*args, **kwargs):  # type: ignore[no-untyped-def]
        return subprocess.CompletedProcess(
            args=args[0],
            returncode=1,
            stdout="",
            stderr="not available",
        )

    assert read_sfv2_next_d0_service_state(runner=runner) == {
        "available": False,
        "reason": "systemd_query_failed",
    }


def test_service_state_reports_unloaded_unit_without_exposing_stderr() -> None:
    def runner(*args, **kwargs):  # type: ignore[no-untyped-def]
        return subprocess.CompletedProcess(
            args=args[0],
            returncode=0,
            stdout="LoadState=not-found\nActiveState=inactive\n",
            stderr="sensitive diagnostics",
        )

    assert read_sfv2_next_d0_service_state(runner=runner) == {
        "available": False,
        "reason": "service_not_loaded",
    }
