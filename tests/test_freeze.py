from __future__ import annotations

import json

import pytest

from eba_trader.freeze import freeze_oos_candidate, load_frozen_candidate


def write_development_report(
    path,
    *,
    oos_status: str = "LOCKED_NOT_ACCESSED",
    fast: int = 20,
    slow: int = 50,
) -> None:
    path.write_text(
        json.dumps(
            {
                "phase": "development_only",
                "oos_2025": oos_status,
                "frozen_baseline": {"fast_ema": fast, "slow_ema": slow},
                "research_robustness": {"example": True},
            },
            sort_keys=True,
        ),
        encoding="utf-8",
    )


def test_freeze_requires_development_report(tmp_path) -> None:
    with pytest.raises(FileNotFoundError):
        freeze_oos_candidate(
            development_report_path=tmp_path / "missing.json",
            freeze_path=tmp_path / "freeze.json",
        )


def test_freeze_requires_proof_oos_was_locked(tmp_path) -> None:
    development = tmp_path / "development.json"
    write_development_report(development, oos_status="OPENED")
    with pytest.raises(ValueError, match="stayed locked"):
        freeze_oos_candidate(
            development_report_path=development,
            freeze_path=tmp_path / "freeze.json",
        )


def test_freeze_uses_only_predeclared_baseline(tmp_path) -> None:
    development = tmp_path / "development.json"
    frozen = tmp_path / "freeze.json"
    write_development_report(development, fast=20, slow=50)

    payload = freeze_oos_candidate(
        development_report_path=development,
        freeze_path=frozen,
    )
    assert payload["fast_ema"] == 20
    assert payload["slow_ema"] == 50
    assert payload["source"] == "development_report.frozen_baseline"


def test_freeze_hash_detects_development_report_mutation(tmp_path) -> None:
    development = tmp_path / "development.json"
    frozen = tmp_path / "freeze.json"
    write_development_report(development)

    freeze_oos_candidate(
        development_report_path=development,
        freeze_path=frozen,
    )
    loaded = load_frozen_candidate(
        freeze_path=frozen,
        development_report_path=development,
    )
    assert loaded["fast_ema"] == 20
    assert loaded["slow_ema"] == 50

    development.write_text(development.read_text(encoding="utf-8") + "\n", encoding="utf-8")
    with pytest.raises(RuntimeError, match="changed after candidate freeze"):
        load_frozen_candidate(
            freeze_path=frozen,
            development_report_path=development,
        )


def test_freeze_file_cannot_be_overwritten(tmp_path) -> None:
    development = tmp_path / "development.json"
    frozen = tmp_path / "freeze.json"
    write_development_report(development)
    freeze_oos_candidate(
        development_report_path=development,
        freeze_path=frozen,
    )
    with pytest.raises(RuntimeError, match="already exists"):
        freeze_oos_candidate(
            development_report_path=development,
            freeze_path=frozen,
        )
