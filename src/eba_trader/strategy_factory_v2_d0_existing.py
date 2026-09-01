from __future__ import annotations

from pathlib import Path

from .m5_corpus_materializer import (
    DEFAULT_NAMESPACE,
    M5DevelopmentCorpusMaterialization,
    materialize_m5_development_corpus,
)
from .strategy_factory_v2_d0_source import D0SourceDeclaration, declare_d0_from_inspected_m5_development
from .orderflow_feature_dataset import OrderFlowFeatureRow


def load_existing_d0_from_inspected_m5(
    *,
    dataset_root: str | Path,
    price_bucket: float = 1.0,
    namespace: str = DEFAULT_NAMESPACE,
    orderflow_source: str = "archive",
) -> tuple[D0SourceDeclaration, tuple[OrderFlowFeatureRow, ...], M5DevelopmentCorpusMaterialization]:
    """Load D0 from already-materialized inspected M5 development evidence only.

    The injected builder always fails before acquisition. Therefore this path can validate and
    reuse a complete existing materialization, but it cannot fetch, rebuild, or extend research
    data. Missing/incomplete evidence fails closed.
    """

    def reject_build(**_: object):
        raise RuntimeError(
            "existing-only D0 load requires a complete pre-existing M5 development materialization"
        )

    materialization, _ = materialize_m5_development_corpus(
        dataset_root=dataset_root,
        price_bucket=price_bucket,
        namespace=namespace,
        orderflow_source=orderflow_source,
        build_window=reject_build,
    )
    declaration, rows = declare_d0_from_inspected_m5_development(
        materialization=materialization,
        dataset_root=dataset_root,
    )
    return declaration, rows, materialization
