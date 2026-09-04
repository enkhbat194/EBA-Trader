from __future__ import annotations

from collections.abc import Sequence

from .history import Candle
from .orderflow_feature_dataset import OrderFlowFeatureRow
from .strategy_discovery_v2 import DiscoveryCandidate
from .strategy_factory_v2_next_design import EXPECTED_FAMILY_IDS
from .strategy_factory_v2_next_families import NextFamilyExecution, execute_next_family

ADAPTER_AUTHORITY = "DESIGN_ONLY"


def execute_design_candidate(
    *,
    candidate: DiscoveryCandidate,
    candles: Sequence[Candle],
    orderflow_rows: Sequence[OrderFlowFeatureRow] = (),
    trade_start_time_ms: int | None = None,
) -> NextFamilyExecution:
    """Bind a declared specification to next-family semantics without campaign authority.

    This adapter exists so engine semantics can be unit-tested before the exact catalog and D0
    dataset are frozen. It does not register a campaign/trial, rank a candidate, write research
    evidence, authorize performance evaluation, open D1/OOS/SF4 or enable exchange execution.
    """

    if candidate.family_id not in EXPECTED_FAMILY_IDS:
        raise ValueError("candidate is not one of the frozen next-campaign design family slots")
    return execute_next_family(
        family_id=candidate.family_id,
        parameters=candidate.parameters,
        candles=candles,
        orderflow_rows=orderflow_rows,
        trade_start_time_ms=trade_start_time_ms,
    )
