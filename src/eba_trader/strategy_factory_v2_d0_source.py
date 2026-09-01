from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .m5_corpus_materializer import M5DevelopmentCorpusMaterialization
from .m5_study_policy import DEFAULT_M5_DEVELOPMENT_CORPUS, DEFAULT_M5_STUDY_POLICY
from .orderflow_feature_dataset import OrderFlowFeatureRow, load_orderflow_feature_csv
from .research_evidence import canonical_json, sha256_file, sha256_text
from .strategy_factory_v2_d0 import (
    D0_AUTHORITY,
    D0_PROVENANCE_CLASS,
    D0DatasetManifest,
    build_d0_dataset_manifest,
)

D0_SOURCE_SCHEMA = "strategy_factory_v2_d0_source_v1"
D0_SOURCE_KIND = "INSPECTED_M5_DEVELOPMENT_CORPUS"


@dataclass(frozen=True, slots=True)
class D0SourceDeclaration:
    source_kind: str
    source_materialization_id: str
    source_policy_id: str
    source_corpus_id: str
    source_window_feature_sha256: tuple[str, ...]
    manifest: D0DatasetManifest
    declaration_sha256: str
    authority: str = D0_AUTHORITY
    provenance_class: str = D0_PROVENANCE_CLASS
    schema: str = D0_SOURCE_SCHEMA

    def __post_init__(self) -> None:
        if self.schema != D0_SOURCE_SCHEMA or self.authority != D0_AUTHORITY:
            raise ValueError("D0 source declaration authority changed")
        if self.provenance_class != D0_PROVENANCE_CLASS:
            raise ValueError("D0 source must remain inspected/reusable discovery data")
        if self.source_kind != D0_SOURCE_KIND:
            raise ValueError("D0 source kind changed")
        if not self.declaration_sha256.strip():
            raise ValueError("D0 source declaration hash is required")

    def as_dict(self) -> dict[str, Any]:
        return {
            "schema": self.schema,
            "authority": self.authority,
            "provenance_class": self.provenance_class,
            "source_kind": self.source_kind,
            "source_materialization_id": self.source_materialization_id,
            "source_policy_id": self.source_policy_id,
            "source_corpus_id": self.source_corpus_id,
            "source_window_feature_sha256": list(self.source_window_feature_sha256),
            "d0_manifest": self.manifest.as_dict(),
            "declaration_sha256": self.declaration_sha256,
            "frozen_oos_opened": False,
            "live_execution_allowed": False,
        }


def declare_d0_from_inspected_m5_development(
    *,
    materialization: M5DevelopmentCorpusMaterialization,
    dataset_root: str | Path,
) -> tuple[D0SourceDeclaration, tuple[OrderFlowFeatureRow, ...]]:
    """Build D0 only from the already-inspected sealed M5 development corpus.

    This adapter deliberately rejects alternate corpora. It validates every immutable feature CSV
    hash before loading, keeps the 12 historical four-hour windows as 12 separate temporal strata,
    and never touches M5 Frozen OOS or prospective SF4 data.
    """

    _validate_source_materialization(materialization)
    root = Path(dataset_root).resolve()
    rows_by_window: list[tuple[OrderFlowFeatureRow, ...]] = []
    feature_hashes: list[str] = []

    for receipt, window in zip(
        materialization.windows,
        DEFAULT_M5_DEVELOPMENT_CORPUS.windows,
        strict=True,
    ):
        if receipt.window_name != window.name:
            raise RuntimeError("D0 source window identity mismatch")
        if receipt.start_ms != window.start_ms or receipt.end_ms != window.end_ms:
            raise RuntimeError("D0 source window range mismatch")
        dataset_path = _resolve_dataset_ref(root, receipt.dataset_ref)
        if not dataset_path.is_file():
            raise RuntimeError("D0 source feature CSV is missing")
        actual_sha = sha256_file(dataset_path)
        if actual_sha != receipt.feature_csv_sha256:
            raise RuntimeError("D0 source feature CSV integrity mismatch")
        rows = load_orderflow_feature_csv(dataset_path)
        if not rows:
            raise RuntimeError("D0 source feature CSV is empty")
        if rows[0].candle.open_time_ms != window.start_ms:
            raise RuntimeError("D0 source feature rows start outside declared window")
        if rows[-1].candle.close_time_ms + 1 != window.end_ms:
            raise RuntimeError("D0 source feature rows end outside declared window")
        rows_by_window.append(rows)
        feature_hashes.append(actual_sha)

    row_counts = {len(rows) for rows in rows_by_window}
    if len(row_counts) != 1:
        raise RuntimeError("D0 source windows must have equal row counts for one-window strata")
    combined_rows = tuple(row for rows in rows_by_window for row in rows)
    candles = tuple(row.candle for row in combined_rows)
    manifest = build_d0_dataset_manifest(
        symbol=materialization.symbol,
        venue=materialization.venue,
        interval=materialization.interval,
        candles=candles,
        orderflow_rows=combined_rows,
        temporal_strata=len(DEFAULT_M5_DEVELOPMENT_CORPUS.windows),
    )
    _assert_strata_match_source_windows(manifest)

    identity = {
        "schema": D0_SOURCE_SCHEMA,
        "authority": D0_AUTHORITY,
        "provenance_class": D0_PROVENANCE_CLASS,
        "source_kind": D0_SOURCE_KIND,
        "source_materialization_id": materialization.materialization_id,
        "source_policy_id": materialization.policy_id,
        "source_corpus_id": materialization.corpus_id,
        "source_window_feature_sha256": feature_hashes,
        "d0_manifest": manifest.as_dict(),
        "frozen_oos_opened": False,
        "live_execution_allowed": False,
    }
    declaration_sha = sha256_text(canonical_json(identity))
    declaration = D0SourceDeclaration(
        source_kind=D0_SOURCE_KIND,
        source_materialization_id=materialization.materialization_id,
        source_policy_id=materialization.policy_id,
        source_corpus_id=materialization.corpus_id,
        source_window_feature_sha256=tuple(feature_hashes),
        manifest=manifest,
        declaration_sha256=declaration_sha,
    )
    return declaration, combined_rows


def _validate_source_materialization(materialization: M5DevelopmentCorpusMaterialization) -> None:
    policy = DEFAULT_M5_STUDY_POLICY
    corpus = DEFAULT_M5_DEVELOPMENT_CORPUS
    if materialization.policy_id != policy.policy_id:
        raise ValueError("D0 source must use the sealed M5 study policy")
    if materialization.corpus_id != corpus.corpus_id:
        raise ValueError("D0 source must use the already-inspected default M5 development corpus")
    if (materialization.symbol, materialization.venue, materialization.interval) != (
        policy.symbol,
        policy.venue,
        policy.interval,
    ):
        raise ValueError("D0 source market identity mismatch")
    if len(materialization.windows) != len(corpus.windows):
        raise ValueError("D0 source materialization is incomplete")


def _resolve_dataset_ref(root: Path, dataset_ref: str) -> Path:
    relative = Path(dataset_ref)
    if relative.is_absolute() or ".." in relative.parts:
        raise ValueError("D0 source dataset_ref must remain inside dataset root")
    candidate = (root / relative).resolve()
    try:
        candidate.relative_to(root)
    except ValueError as exc:
        raise ValueError("D0 source dataset_ref escapes dataset root") from exc
    return candidate


def _assert_strata_match_source_windows(manifest: D0DatasetManifest) -> None:
    windows = DEFAULT_M5_DEVELOPMENT_CORPUS.windows
    if len(manifest.temporal_strata) != len(windows):
        raise RuntimeError("D0 temporal strata do not match source window count")
    for stratum, window in zip(manifest.temporal_strata, windows, strict=True):
        if stratum.start_ms != window.start_ms:
            raise RuntimeError("D0 stratum start does not align to source development window")
        if stratum.end_ms + 1 != window.end_ms:
            raise RuntimeError("D0 stratum end does not align to source development window")
