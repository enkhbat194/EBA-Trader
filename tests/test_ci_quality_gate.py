from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_linode_bundle_enforces_full_repository_ruff() -> None:
    workflow = (ROOT / ".github/workflows/linode-production.yml").read_text(
        encoding="utf-8"
    )

    assert "run: ruff check ." in workflow
