from __future__ import annotations

import platform
import subprocess
import sys
from pathlib import Path


def _git(args: list[str], *, cwd: str | Path | None = None) -> str:
    try:
        completed = subprocess.run(
            ["git", *args],
            cwd=cwd,
            check=True,
            capture_output=True,
            text=True,
        )
    except (OSError, subprocess.CalledProcessError) as exc:
        raise RuntimeError(f"Git provenance command failed: {' '.join(args)}") from exc
    return completed.stdout.strip()


def collect_source_provenance(
    *,
    cwd: str | Path | None = None,
    require_clean: bool = True,
) -> dict[str, object]:
    commit = _git(["rev-parse", "HEAD"], cwd=cwd)
    branch = _git(["rev-parse", "--abbrev-ref", "HEAD"], cwd=cwd)
    dirty_lines = _git(["status", "--porcelain", "--untracked-files=no"], cwd=cwd)
    clean = dirty_lines == ""
    if require_clean and not clean:
        raise RuntimeError(
            "Tracked working tree is dirty. Commit or discard code changes before "
            "evidence generation."
        )

    return {
        "git_commit": commit,
        "git_branch": branch,
        "tracked_working_tree_clean": clean,
        "python_version": platform.python_version(),
        "python_implementation": platform.python_implementation(),
        "platform": platform.platform(),
        "executable": sys.executable,
    }
