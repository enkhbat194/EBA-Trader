from __future__ import annotations

import subprocess
from pathlib import PurePosixPath


FORBIDDEN_PREFIXES = (
    "artifacts/",
    "logs/",
    "data/raw/",
    "data/cache/",
    "data/catalog/",
    ".pytest_cache/",
    ".ruff_cache/",
    ".mypy_cache/",
    ".venv/",
    "venv/",
    "node_modules/",
)

FORBIDDEN_SUFFIXES = (
    ".db",
    ".db-journal",
    ".db-shm",
    ".db-wal",
    ".sqlite",
    ".sqlite3",
    ".log",
    ".pid",
    ".tmp",
    ".swp",
    ".pem",
    ".key",
)

FORBIDDEN_NAMES = {
    ".DS_Store",
    ".coverage",
    "coverage.xml",
}

ALLOWED_SECRET_EXAMPLES = {
    ".env.example",
}


def tracked_files() -> list[str]:
    result = subprocess.run(
        ["git", "ls-files", "-z"],
        check=True,
        capture_output=True,
    )
    return [item.decode("utf-8") for item in result.stdout.split(b"\0") if item]


def violations(paths: list[str]) -> list[str]:
    problems: list[str] = []
    for raw_path in paths:
        path = PurePosixPath(raw_path)
        normalized = path.as_posix()
        if normalized in ALLOWED_SECRET_EXAMPLES:
            continue
        if any(normalized.startswith(prefix) for prefix in FORBIDDEN_PREFIXES):
            problems.append(f"runtime/cache path is tracked: {normalized}")
            continue
        if path.name in FORBIDDEN_NAMES:
            problems.append(f"local/generated file is tracked: {normalized}")
            continue
        if normalized.endswith(FORBIDDEN_SUFFIXES):
            problems.append(f"runtime/secret-like file is tracked: {normalized}")
            continue
        if path.name == ".env" or path.name.startswith(".env."):
            problems.append(f"environment file is tracked: {normalized}")
    return problems


def main() -> None:
    problems = violations(tracked_files())
    if problems:
        print("Repository hygiene check FAILED")
        for problem in problems:
            print(f"- {problem}")
        raise SystemExit(1)
    print("Repository hygiene check PASS")


if __name__ == "__main__":
    main()
