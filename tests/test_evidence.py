from __future__ import annotations

import inspect

import pytest

from eba_trader import evidence


def test_first_cycle_baseline_is_predeclared_20_50() -> None:
    assert evidence.FIRST_CYCLE_FAST_EMA == 20
    assert evidence.FIRST_CYCLE_SLOW_EMA == 50


def test_development_evidence_function_has_no_ema_override_parameters() -> None:
    parameters = inspect.signature(evidence.run_development_evidence).parameters
    assert "fast_ema" not in parameters
    assert "slow_ema" not in parameters


def test_development_cli_source_has_no_fast_slow_arguments() -> None:
    source = inspect.getsource(evidence.development_evidence_cli)
    assert 'add_argument("--fast"' not in source
    assert 'add_argument("--slow"' not in source


def test_development_evidence_requires_clean_provenance_before_data_access(
    monkeypatch,
) -> None:
    def reject_dirty_tree(*, require_clean: bool):
        assert require_clean is True
        raise RuntimeError("dirty tracked tree")

    def should_not_run(*args, **kwargs):
        pytest.fail("development data must not be accessed before provenance passes")

    monkeypatch.setattr(evidence, "collect_source_provenance", reject_dirty_tree)
    monkeypatch.setattr(evidence, "run_baseline_study", should_not_run)

    with pytest.raises(RuntimeError, match="dirty tracked tree"):
        evidence.run_development_evidence()
