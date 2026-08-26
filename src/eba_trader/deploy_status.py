from __future__ import annotations

import os
import subprocess
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

DEFAULT_REPO_DIR = Path("/opt/Eba-Trader")
DEFAULT_DEPLOY_STATE_DIR = Path("/var/lib/eba-trader/deploy-state")
UPDATE_REQUEST_FILE = "update-requested"


def _read_optional(path: Path) -> str | None:
    try:
        value = path.read_text(encoding="utf-8").strip()
    except OSError:
        return None
    return value or None


def _git_output(repo_dir: Path, *args: str) -> str | None:
    try:
        result = subprocess.run(
            ["git", *args],
            cwd=repo_dir,
            capture_output=True,
            check=True,
            text=True,
            timeout=3,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    return result.stdout.strip() or None


def build_deploy_status(
    *,
    repo_dir: str | Path = DEFAULT_REPO_DIR,
    state_dir: str | Path = DEFAULT_DEPLOY_STATE_DIR,
) -> dict[str, Any]:
    repo = Path(repo_dir)
    state = Path(state_dir)
    current_sha = _git_output(repo, "rev-parse", "HEAD")
    dirty = _git_output(repo, "status", "--porcelain")
    return {
        "ok": True,
        "currentSha": current_sha,
        "dirtyCheckout": bool(dirty),
        "currentRecordedSha": _read_optional(state / "current_sha"),
        "targetSha": _read_optional(state / "target_sha"),
        "previousSha": _read_optional(state / "previous_sha"),
        "lastAttemptAt": _read_optional(state / "last_attempt_at"),
        "lastSuccessAt": _read_optional(state / "succeeded_at"),
        "lastFailureAt": _read_optional(state / "failed_at"),
        "lastError": _read_optional(state / "last_error"),
        "updateRequested": (state / UPDATE_REQUEST_FILE).exists(),
        "runtime": "linode",
        "liveExecutionAllowed": False,
    }


def request_deploy_update(
    *,
    state_dir: str | Path = DEFAULT_DEPLOY_STATE_DIR,
) -> dict[str, Any]:
    state = Path(state_dir)
    state.mkdir(parents=True, exist_ok=True)
    request = state / UPDATE_REQUEST_FILE
    timestamp = datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    fd = os.open(request, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o640)
    with os.fdopen(fd, "w", encoding="utf-8") as handle:
        handle.write(timestamp + "\n")
        handle.flush()
        os.fsync(handle.fileno())
    return {
        "ok": True,
        "requested": True,
        "requestedAt": timestamp,
        "runtime": "linode",
        "liveExecutionAllowed": False,
    }
