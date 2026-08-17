from __future__ import annotations

import json

import pytest

from eba_trader.freeze import file_sha256, freeze_oos_candidate, load_frozen_candidate


def write_development_report(
    path,
    *,
    data_dir,
    oos_status: str = "LOCKED_NOT_ACCESSED",
    fast: int = 20,
    slow: int = 50,
) -> None:
    path.write_text(
        json.dumps(
            {
                "phase": "development_only",
                "symbol": "BTCUSDT",
                "interval": "15m",
                "data_dir": str(data_dir),
                "oos_2025": oos_status,
                "frozen_baseline": {"fast_ema": fast, "slow_ema": slow},
                "research_robustness": {"example": True},
            },
            sort_keys=True,
        ),
        encoding="utf-8",
    )


def write_verdict(path, development, *, eligible: bool = True) -> None:
    path.write_text(
        json.dumps(
            {
                "screening_version": 1,
                "development_report_sha256": file_sha256(development),
                "status": (
                    "ELIGIBLE_FOR_FROZEN_OOS" if eligible else "REJECT_DEVELOPMENT_CYCLE"
                ),
                "all_gates_passed": eligible,
            },
            sort_keys=True,
        ),
        encoding="utf-8",
    )


def freeze_fixture(tmp_path, *, fast: int = 20, slow: int = 50):
    data_dir = tmp_path / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    development = tmp_path / "development.json"
    verdict = tmp_path / "verdict.json"
    frozen = tmp_path / "freeze.json"
    write_development_report(development, data_dir=data_dir, fast=fast, slow=slow)
    write_verdict(verdict, development)
    return data_dir, development, verdict, frozen


def test_freeze_requires_development_report(tmp_path) -> None:
    with pytest.raises(FileNotFoundError):
        freeze_oos_candidate(
            development_report_path=tmp_path / "missing.json",
            verdict_path=tmp_path / "verdict.json",
            freeze_path=tmp_path / "freeze.json",
        )


def test_freeze_requires_proof_oos_was_locked(tmp_path) -> None:
    data_dir = tmp_path / "data"
    development = tmp_path / "development.json"
    verdict = tmp_path / "verdict.json"
    write_development_report(development, data_dir=data_dir, oos_status="OPENED")
    write_verdict(verdict, development)
    with pytest.raises(ValueError, match="stayed locked"):
        freeze_oos_candidate(
            development_report_path=development,
            verdict_path=verdict,
            freeze_path=tmp_path / "freeze.json",
        )


def test_freeze_requires_eligible_screening_verdict(tmp_path) -> None:
    data_dir = tmp_path / "data"
    development = tmp_path / "development.json"
    verdict = tmp_path / "verdict.json"
    write_development_report(development, data_dir=data_dir)
    write_verdict(verdict, development, eligible=False)
    with pytest.raises(RuntimeError, match="not eligible"):
        freeze_oos_candidate(
            development_report_path=development,
            verdict_path=verdict,
            freeze_path=tmp_path / "freeze.json",
        )


def test_freeze_rejects_verdict_for_different_development_hash(tmp_path) -> None:
    data_dir, development, verdict, frozen = freeze_fixture(tmp_path)
    development.write_text(development.read_text(encoding="utf-8") + "\n", encoding="utf-8")
    with pytest.raises(RuntimeError, match="does not match"):
        freeze_oos_candidate(
            development_report_path=development,
            verdict_path=verdict,
            freeze_path=frozen,
        )


def test_freeze_uses_only_predeclared_baseline(tmp_path) -> None:
    _, development, verdict, frozen = freeze_fixture(tmp_path, fast=20, slow=50)
    payload = freeze_oos_candidate(
        development_report_path=development,
        verdict_path=verdict,
        freeze_path=frozen,
    )
    assert payload["fast_ema"] == 20
    assert payload["slow_ema"] == 50
    assert payload["source"] == "development_report.frozen_baseline"
    assert payload["screening_status"] == "ELIGIBLE_FOR_FROZEN_OOS"
    assert payload["oos_cache_verified_absent_at_freeze"] is True


def test_freeze_refuses_oos_cache_created_after_development(tmp_path) -> None:
    data_dir, development, verdict, frozen = freeze_fixture(tmp_path)
    (data_dir / "btcusdt_15m_out_of_sample.csv").write_text("opened", encoding="utf-8")

    with pytest.raises(RuntimeError, match="contaminated"):
        freeze_oos_candidate(
            development_report_path=development,
            verdict_path=verdict,
            freeze_path=frozen,
        )


def test_freeze_hash_detects_development_report_mutation(tmp_path) -> None:
    _, development, verdict, frozen = freeze_fixture(tmp_path)
    freeze_oos_candidate(
        development_report_path=development,
        verdict_path=verdict,
        freeze_path=frozen,
    )
    loaded = load_frozen_candidate(
        freeze_path=frozen,
        development_report_path=development,
        verdict_path=verdict,
    )
    assert loaded["fast_ema"] == 20
    assert loaded["slow_ema"] == 50

    development.write_text(development.read_text(encoding="utf-8") + "\n", encoding="utf-8")
    with pytest.raises(RuntimeError, match="changed after candidate freeze"):
        load_frozen_candidate(
            freeze_path=frozen,
            development_report_path=development,
            verdict_path=verdict,
        )


def test_frozen_candidate_refuses_verdict_mutation_after_freeze(tmp_path) -> None:
    _, development, verdict, frozen = freeze_fixture(tmp_path)
    freeze_oos_candidate(
        development_report_path=development,
        verdict_path=verdict,
        freeze_path=frozen,
    )
    verdict.write_text(verdict.read_text(encoding="utf-8") + "\n", encoding="utf-8")
    with pytest.raises(RuntimeError, match="verdict changed"):
        load_frozen_candidate(
            freeze_path=frozen,
            development_report_path=development,
            verdict_path=verdict,
        )


def test_frozen_candidate_refuses_oos_cache_created_after_freeze(tmp_path) -> None:
    data_dir, development, verdict, frozen = freeze_fixture(tmp_path)
    freeze_oos_candidate(
        development_report_path=development,
        verdict_path=verdict,
        freeze_path=frozen,
    )

    (data_dir / "btcusdt_15m_out_of_sample.csv").write_text("opened", encoding="utf-8")
    with pytest.raises(RuntimeError, match="contaminated"):
        load_frozen_candidate(
            freeze_path=frozen,
            development_report_path=development,
            verdict_path=verdict,
        )


def test_freeze_file_cannot_be_overwritten(tmp_path) -> None:
    _, development, verdict, frozen = freeze_fixture(tmp_path)
    freeze_oos_candidate(
        development_report_path=development,
        verdict_path=verdict,
        freeze_path=frozen,
    )
    with pytest.raises(RuntimeError, match="already exists"):
        freeze_oos_candidate(
            development_report_path=development,
            verdict_path=verdict,
            freeze_path=frozen,
        )
