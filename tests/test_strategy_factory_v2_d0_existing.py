from __future__ import annotations

from pathlib import Path

import pytest

from eba_trader.strategy_factory_v2_d0_existing import load_existing_d0_from_inspected_m5


def test_existing_only_d0_fails_before_any_build_when_materialization_is_absent(
    tmp_path: Path,
) -> None:
    with pytest.raises(RuntimeError, match="complete pre-existing M5 development materialization"):
        load_existing_d0_from_inspected_m5(dataset_root=tmp_path)


def test_existing_only_d0_does_not_create_feature_evidence_when_absent(tmp_path: Path) -> None:
    with pytest.raises(RuntimeError):
        load_existing_d0_from_inspected_m5(dataset_root=tmp_path)

    assert not list(tmp_path.rglob("*.csv"))
    assert not list(tmp_path.rglob("*.manifest.json"))
