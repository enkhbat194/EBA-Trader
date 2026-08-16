from __future__ import annotations

from dataclasses import replace

from .data_health import DataHealthSnapshot, DataHealthStatus
from .risk import RiskContext


def apply_market_data_health(
    context: RiskContext,
    snapshot: DataHealthSnapshot,
) -> RiskContext:
    """Return a risk context whose data-fresh flag is derived deterministically.

    Only HEALTHY market data is considered fresh. STARTING, STALE and STOPPED
    states all force the Risk Engine's existing `STALE_MARKET_DATA` hard halt.
    """

    return replace(
        context,
        data_fresh=snapshot.status is DataHealthStatus.HEALTHY,
    )
