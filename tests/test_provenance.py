from __future__ import annotations

import pytest

import eba_trader.provenance as provenance


def test_collect_source_provenance_records_commit_and_runtime(monkeypatch) -> None:
    responses = {
        ("rev-parse", "HEAD"): "0123456789abcdef0123456789abcdef01234567",
        ("rev-parse", "--abbrev-ref", "HEAD"): "main",
        ("status", "--porcelain", "--untracked-files=no"): "",
    }

    monkeypatch.setattr(
        provenance,
        "_git",
        lambda args, cwd=None: responses[tuple(args)],
    )
    payload = provenance.collect_source_provenance(require_clean=True)
    assert payload["git_commit"].startswith("01234567")
    assert payload["git_branch"] == "main"
    assert payload["tracked_working_tree_clean"] is True
    assert payload["python_version"]


def test_collect_source_provenance_rejects_dirty_tracked_tree(monkeypatch) -> None:
    responses = {
        ("rev-parse", "HEAD"): "0123456789abcdef0123456789abcdef01234567",
        ("rev-parse", "--abbrev-ref", "HEAD"): "main",
        ("status", "--porcelain", "--untracked-files=no"): " M src/eba_trader/backtest.py",
    }
    monkeypatch.setattr(
        provenance,
        "_git",
        lambda args, cwd=None: responses[tuple(args)],
    )
    with pytest.raises(RuntimeError, match="dirty"):
        provenance.collect_source_provenance(require_clean=True)
