from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

REQUIRED_FILES = {
    "AGENTS.md": ("Mandatory start-of-session protocol", "Mandatory end-of-session protocol"),
    "PROJECT_STATE.md": ("Current goal", "Validation", "Next"),
    "ARCHITECTURE.md": ("System goal", "Safety invariants"),
    "DECISIONS.md": ("Repository continuity is mandatory",),
    "TODO.md": ("## NOW", "## NEXT", "## BLOCKED"),
    "CHANGELOG.md": ("## Unreleased",),
    "SESSION_HANDOFF.md": ("What was completed", "Next exact task"),
    "docs/CONTINUITY_PROTOCOL.md": ("Start of every session", "End of meaningful work"),
}

FORBIDDEN_TEMPLATE_TEXT = (
    "Last updated: YYYY-MM-DD HH:MM",
    "Current branch:\nCurrent commit:",
    "Highest-priority task",
    "### Component 1",
    "What was decided?",
    "path/to/file",
)


def main() -> int:
    failures: list[str] = []
    for relative, markers in REQUIRED_FILES.items():
        path = ROOT / relative
        if not path.is_file():
            failures.append(f"missing required continuity file: {relative}")
            continue
        text = path.read_text(encoding="utf-8")
        if not text.strip():
            failures.append(f"empty continuity file: {relative}")
            continue
        for marker in markers:
            if marker not in text:
                failures.append(f"{relative}: missing required marker {marker!r}")
        for placeholder in FORBIDDEN_TEMPLATE_TEXT:
            if placeholder in text:
                failures.append(f"{relative}: unresolved template placeholder {placeholder!r}")

    agents = ROOT / "AGENTS.md"
    if agents.is_file():
        text = agents.read_text(encoding="utf-8")
        for required in (
            "PROJECT_STATE.md",
            "DECISIONS.md",
            "TODO.md",
            "SESSION_HANDOFF.md",
            "scripts/check_continuity.py",
        ):
            if required not in text:
                failures.append(f"AGENTS.md does not reference {required}")

    if failures:
        print("Continuity guard FAILED:")
        for failure in failures:
            print(f"- {failure}")
        return 1

    print("Continuity guard passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
