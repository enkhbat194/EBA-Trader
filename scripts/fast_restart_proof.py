#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sqlite3
import subprocess
import tempfile
import time
import urllib.request
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from eba_trader.persistence import DEFAULT_DB_PATH

WEB_API = "http://127.0.0.1:8000"
DEFAULT_STATE = Path("/var/lib/eba-trader/proofs/fast-restart.json")
FAST_STRATEGY = "FAST_MOMENTUM"
WEB_SERVICE = "eba-web.service"


def _now() -> str:
    return datetime.now(tz=UTC).isoformat()


def _get_json(path: str, *, timeout: float = 8.0) -> dict[str, Any]:
    request = urllib.request.Request(
        WEB_API + path,
        headers={"Accept": "application/json"},
        method="GET",
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        payload = json.loads(response.read().decode("utf-8"))
    if not isinstance(payload, dict):
        raise RuntimeError(f"{path} returned non-object JSON")
    return payload


def _runner_status() -> dict[str, Any]:
    status = _get_json("/api/runner/status")
    if status.get("liveExecutionAllowed") is not False:
        raise RuntimeError("runner safety lock is not explicit")
    return status


def _position_id(status: dict[str, Any]) -> str | None:
    fast = status.get("fastState")
    if not isinstance(fast, dict):
        return None
    position = fast.get("openPosition")
    if not isinstance(position, dict):
        return None
    value = str(position.get("position_id") or "").strip()
    return value or None


def _load_state(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {
            "schemaVersion": 1,
            "phase": "WAITING_FOR_OPEN",
            "passed": False,
            "liveExecutionAllowed": False,
        }
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {
            "schemaVersion": 1,
            "phase": "WAITING_FOR_OPEN",
            "passed": False,
            "liveExecutionAllowed": False,
        }
    return payload if isinstance(payload, dict) else {}


def _atomic_write(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload["updatedAt"] = _now()
    payload["liveExecutionAllowed"] = False
    serialized = json.dumps(payload, sort_keys=True, indent=2) + "\n"
    with tempfile.NamedTemporaryFile(
        mode="w",
        encoding="utf-8",
        dir=path.parent,
        prefix=f".{path.name}.",
        delete=False,
    ) as handle:
        handle.write(serialized)
        temp = Path(handle.name)
    temp.chmod(0o640)
    temp.replace(path)


def _read_position(ledger_path: Path, position_id: str) -> dict[str, Any] | None:
    uri = f"file:{ledger_path.resolve().as_posix()}?mode=ro"
    connection = sqlite3.connect(uri, uri=True, timeout=5)
    connection.row_factory = sqlite3.Row
    try:
        row = connection.execute(
            "SELECT * FROM positions WHERE position_id = ?",
            (position_id,),
        ).fetchone()
    finally:
        connection.close()
    return dict(row) if row is not None else None


def _events_for(ledger_path: Path, position_id: str) -> list[dict[str, Any]]:
    uri = f"file:{ledger_path.resolve().as_posix()}?mode=ro"
    connection = sqlite3.connect(uri, uri=True, timeout=5)
    connection.row_factory = sqlite3.Row
    try:
        rows = connection.execute(
            """
            SELECT id, event_type, position_id, created_at
            FROM events
            WHERE position_id = ?
            ORDER BY id
            """,
            (position_id,),
        ).fetchall()
    finally:
        connection.close()
    return [dict(row) for row in rows]


def _validate_open_position(ledger_path: Path, position_id: str) -> dict[str, Any]:
    row = _read_position(ledger_path, position_id)
    if row is None:
        raise RuntimeError("runner position is missing from TradeLedger")
    if row.get("status") != "OPEN":
        raise RuntimeError("runner position is not OPEN in TradeLedger")
    if row.get("strategy") != FAST_STRATEGY:
        raise RuntimeError("runner position is not FAST_MOMENTUM")
    events = _events_for(ledger_path, position_id)
    opens = [event for event in events if event.get("event_type") == "FAST_MOMENTUM_OPEN"]
    if not opens:
        raise RuntimeError("FAST_MOMENTUM_OPEN event is missing")
    return row


def _restart_web() -> None:
    subprocess.run(
        ["systemctl", "restart", WEB_SERVICE],
        check=True,
        capture_output=True,
        timeout=30,
    )
    deadline = time.time() + 45
    last_error = "web service did not answer"
    while time.time() < deadline:
        try:
            health = _get_json("/api/health", timeout=5)
            if health.get("ok") is True:
                return
            last_error = "web health returned ok=false"
        except Exception as exc:  # noqa: BLE001 - bounded operational retry
            last_error = str(exc)[:240]
        time.sleep(2)
    raise RuntimeError(last_error)


def advance(*, state_path: Path, ledger_path: Path) -> dict[str, Any]:
    state = _load_state(state_path)
    if state.get("passed") is True:
        return state

    if not ledger_path.is_file():
        raise RuntimeError("TradeLedger database does not exist")
    phase = str(state.get("phase") or "WAITING_FOR_OPEN")

    if phase == "WAITING_FOR_OPEN":
        runner = _runner_status()
        position_id = _position_id(runner)
        if position_id is None:
            state.update(
                {
                    "phase": "WAITING_FOR_OPEN",
                    "passed": False,
                    "message": "Waiting for a natural Fast Momentum paper position",
                }
            )
            _atomic_write(state_path, state)
            return state

        row = _validate_open_position(ledger_path, position_id)
        events = _events_for(ledger_path, position_id)
        before_event_id = max(int(event["id"]) for event in events)
        state.update(
            {
                "phase": "RESTARTING",
                "passed": False,
                "positionId": position_id,
                "symbol": row.get("symbol"),
                "side": row.get("side"),
                "openedAt": row.get("opened_at"),
                "beforeRestartEventId": before_event_id,
                "restartStartedAt": _now(),
                "openEventProved": True,
            }
        )
        _atomic_write(state_path, state)

        _restart_web()
        recovered = _runner_status()
        recovered_position_id = _position_id(recovered)
        if recovered_position_id != position_id:
            state.update(
                {
                    "phase": "RECOVERY_FAILED",
                    "passed": False,
                    "message": "Fast position did not recover with the same position ID",
                    "recoveredPositionId": recovered_position_id,
                }
            )
            _atomic_write(state_path, state)
            return state

        _validate_open_position(ledger_path, position_id)
        state.update(
            {
                "phase": "WAITING_FOR_MARK_CLOSE",
                "passed": False,
                "recoveryProved": True,
                "restartCompletedAt": _now(),
                "message": "OPEN and restart recovery proved; waiting for post-restart management/CLOSE",
            }
        )
        _atomic_write(state_path, state)
        return state

    if phase == "RESTARTING":
        # A process/server interruption during the proof itself is recovered fail-closed:
        # never restart twice blindly. Confirm whether the recorded position is present.
        position_id = str(state.get("positionId") or "")
        runner = _runner_status()
        if position_id and _position_id(runner) == position_id:
            state.update(
                {
                    "phase": "WAITING_FOR_MARK_CLOSE",
                    "recoveryProved": True,
                    "restartCompletedAt": state.get("restartCompletedAt") or _now(),
                    "message": "Recovered an interrupted restart proof",
                }
            )
        else:
            state.update(
                {
                    "phase": "RECOVERY_FAILED",
                    "passed": False,
                    "message": "Interrupted restart proof could not confirm position recovery",
                }
            )
        _atomic_write(state_path, state)
        return state

    if phase == "WAITING_FOR_MARK_CLOSE":
        position_id = str(state.get("positionId") or "")
        if not position_id:
            raise RuntimeError("restart proof state is missing positionId")
        before_event_id = int(state.get("beforeRestartEventId") or 0)
        events = _events_for(ledger_path, position_id)
        post_restart = [event for event in events if int(event["id"]) > before_event_id]
        mark_seen = any(
            event.get("event_type") == "FAST_MOMENTUM_MARK" for event in post_restart
        )
        close_seen = any(
            event.get("event_type") == "FAST_MOMENTUM_CLOSE" for event in post_restart
        )
        row = _read_position(ledger_path, position_id)
        if row is not None and row.get("status") == "CLOSED":
            close_seen = True

        state.update(
            {
                "postRestartMarkSeen": mark_seen,
                "postRestartCloseSeen": close_seen,
                "postRestartManaged": mark_seen or close_seen,
            }
        )
        if close_seen:
            state.update(
                {
                    "phase": "PASS",
                    "passed": bool(state.get("recoveryProved") and (mark_seen or close_seen)),
                    "closedAt": (row or {}).get("closed_at"),
                    "message": "OPEN -> restart recovery -> post-restart MARK/CLOSE persistence proved",
                }
            )
        else:
            state["message"] = (
                "Restart recovery proved; post-restart MARK observed, waiting for natural CLOSE"
                if mark_seen
                else "Restart recovery proved; waiting for post-restart MARK/CLOSE"
            )
        _atomic_write(state_path, state)
        return state

    return state


def main() -> int:
    parser = argparse.ArgumentParser(description="Prove Fast Momentum restart persistence")
    parser.add_argument("--state", type=Path, default=DEFAULT_STATE)
    parser.add_argument("--ledger", type=Path, default=DEFAULT_DB_PATH)
    args = parser.parse_args()
    try:
        result = advance(state_path=args.state, ledger_path=args.ledger)
    except Exception as exc:  # noqa: BLE001 - persisted operational failure
        result = _load_state(args.state)
        result.update(
            {
                "phase": "ERROR",
                "passed": False,
                "message": str(exc)[:300],
            }
        )
        _atomic_write(args.state, result)
        print(json.dumps(result, sort_keys=True, separators=(",", ":")))
        return 2
    print(json.dumps(result, sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
