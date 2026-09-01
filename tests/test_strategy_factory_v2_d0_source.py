from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pytest

from eba_trader.history import Candle
from eba_trader.m5_corpus_materializer import (
    M5CorpusWindowReceipt,
    M5DevelopmentCorpusMaterialization,
)
from eba_trader.m5_study_policy import DEFAULT_M5_DEVELOPMENT_CORPUS, DEFAULT_M5_STUDY_POLICY
from eba_trader.orderflow_feature_dataset import OrderFlowFeatureRow
from eba_trader.strategy_factory_v2_d0 import D0_PROVENANCE_CLASS
from eba_trader.strategy_factory_v2_d0_source import declare_d0_from_inspected_m5_development


def _rows(start_ms: int, count: int = 240) -> tuple[OrderFlowFeatureRow, ...]:
    output: list[OrderFlowFeatureRow] = []
    for index in range(count):
        open_time = start_ms + index * 60_000
        price = 100.0 + index * 0.01
        candle = Candle(
            open_time_ms=open_time,
            open=price,
            high=price + 1.0,
            low=price - 1.0,
            close=price + 0.1,
            volume=10.0,
            close_time_ms=open_time + 59_999,
            quote_volume=1000.0,
            trade_count=20,
        )
        output.append(
            OrderFlowFeatureRow(
                candle=candle,
                of_buy_volume=6.0,
                of_sell_volume=4.0,
                of_delta=2.0,
                of_delta_ratio=0.2,
                of_cvd=float(index),
                of_poc_price=price,
                footprint_available_at_ms=open_time,
            )
        )
    return tuple(output)


def _materialization(tmp_path: Path) -> tuple[M5DevelopmentCorpusMaterialization, dict[Path, object]]:
    receipts: list[M5CorpusWindowReceipt] = []
    rows_by_path: dict[Path, object] = {}
    for index, window in enumerate(DEFAULT_M5_DEVELOPMENT_CORPUS.windows, start=1):
        relative = Path(f"window-{index:02d}.csv")
        path = tmp_path / relative
        path.write_text("placeholder", encoding="utf-8")
        feature_sha = f"sha-{index:02d}"
        rows_by_path[path.resolve()] = _rows(window.start_ms)
        receipts.append(
            M5CorpusWindowReceipt(
                materialization_id="m5-inspected-materialization",
                policy_id=DEFAULT_M5_DEVELOPMENT_CORPUS.policy_id,
                corpus_id=DEFAULT_M5_DEVELOPMENT_CORPUS.corpus_id,
                window_name=window.name,
                start_ms=window.start_ms,
                end_ms=window.end_ms,
                orderflow_source="archive",
                workflow_id=f"workflow-{index:02d}",
                workflow_manifest_ref=f"workflow-{index:02d}.json",
                feature_dataset_id=f"feature-{index:02d}",
                dataset_ref=str(relative),
                feature_csv_sha256=feature_sha,
            )
        )
    materialization = M5DevelopmentCorpusMaterialization(
        materialization_id="m5-inspected-materialization",
        policy_id=DEFAULT_M5_DEVELOPMENT_CORPUS.policy_id,
        corpus_id=DEFAULT_M5_DEVELOPMENT_CORPUS.corpus_id,
        symbol=DEFAULT_M5_STUDY_POLICY.symbol,
        venue=DEFAULT_M5_STUDY_POLICY.venue,
        interval=DEFAULT_M5_STUDY_POLICY.interval,
        price_bucket=1.0,
        namespace="m5_orderflow_dev",
        orderflow_source="archive",
        windows=tuple(receipts),
    )
    return materialization, rows_by_path


def test_d0_source_uses_only_inspected_default_m5_development_windows(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    materialization, rows_by_path = _materialization(tmp_path)
    sha_by_path = {
        (tmp_path / receipt.dataset_ref).resolve(): receipt.feature_csv_sha256
        for receipt in materialization.windows
    }
    monkeypatch.setattr(
        "eba_trader.strategy_factory_v2_d0_source.sha256_file",
        lambda path: sha_by_path[Path(path).resolve()],
    )
    monkeypatch.setattr(
        "eba_trader.strategy_factory_v2_d0_source.load_orderflow_feature_csv",
        lambda path: rows_by_path[Path(path).resolve()],
    )

    declaration, rows = declare_d0_from_inspected_m5_development(
        materialization=materialization,
        dataset_root=tmp_path,
    )

    assert declaration.provenance_class == D0_PROVENANCE_CLASS
    assert declaration.source_corpus_id == DEFAULT_M5_DEVELOPMENT_CORPUS.corpus_id
    assert declaration.manifest.row_count == 12 * 240
    assert len(rows) == 12 * 240
    assert len(declaration.manifest.temporal_strata) == 12
    for stratum, window in zip(
        declaration.manifest.temporal_strata,
        DEFAULT_M5_DEVELOPMENT_CORPUS.windows,
        strict=True,
    ):
        assert stratum.start_ms == window.start_ms
        assert stratum.end_ms + 1 == window.end_ms
    assert declaration.as_dict()["frozen_oos_opened"] is False
    assert declaration.as_dict()["live_execution_allowed"] is False


def test_alternate_corpus_cannot_be_relabelled_as_d0(
    tmp_path: Path,
) -> None:
    materialization, _ = _materialization(tmp_path)
    changed = replace(materialization, corpus_id="some-other-corpus")

    with pytest.raises(ValueError, match="already-inspected default M5 development corpus"):
        declare_d0_from_inspected_m5_development(
            materialization=changed,
            dataset_root=tmp_path,
        )


def test_d0_source_fails_closed_when_feature_hash_changes(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    materialization, _ = _materialization(tmp_path)
    monkeypatch.setattr(
        "eba_trader.strategy_factory_v2_d0_source.sha256_file",
        lambda path: "tampered",
    )

    with pytest.raises(RuntimeError, match="integrity mismatch"):
        declare_d0_from_inspected_m5_development(
            materialization=materialization,
            dataset_root=tmp_path,
        )


def test_dataset_ref_cannot_escape_dataset_root(tmp_path: Path) -> None:
    materialization, _ = _materialization(tmp_path)
    receipts = list(materialization.windows)
    receipts[0] = replace(receipts[0], dataset_ref="../escape.csv")
    changed = replace(materialization, windows=tuple(receipts))

    with pytest.raises(ValueError, match="inside dataset root"):
        declare_d0_from_inspected_m5_development(
            materialization=changed,
            dataset_root=tmp_path,
        )
