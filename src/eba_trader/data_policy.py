from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from .study_policy import FIRST_CYCLE_INTERVAL, FIRST_CYCLE_SYMBOL


def _utc_ms(value: str) -> int:
    return int(datetime.fromisoformat(value).replace(tzinfo=UTC).timestamp() * 1000)


@dataclass(frozen=True, slots=True)
class AllowedSourceGap:
    start: str
    end_exclusive: str
    reason: str

    @property
    def range_ms(self) -> tuple[int, int]:
        return _utc_ms(self.start), _utc_ms(self.end_exclusive)


# Binance public klines contain no BTCUSDT bars during these source outages. These exact ranges
# were observed twice independently before first-cycle development evidence was accepted.
FIRST_CYCLE_ALLOWED_SOURCE_GAPS = (
    AllowedSourceGap("2021-02-11T03:45:00", "2021-02-11T05:00:00", "binance_source_outage"),
    AllowedSourceGap("2021-03-06T02:00:00", "2021-03-06T03:30:00", "binance_source_outage"),
    AllowedSourceGap("2021-04-20T02:00:00", "2021-04-20T04:30:00", "binance_source_outage"),
    AllowedSourceGap("2021-04-25T04:15:00", "2021-04-25T08:45:00", "binance_source_outage"),
    AllowedSourceGap("2021-08-13T02:00:00", "2021-08-13T06:30:00", "binance_source_outage"),
    AllowedSourceGap("2021-09-29T07:00:00", "2021-09-29T09:00:00", "binance_source_outage"),
    AllowedSourceGap("2023-03-24T12:45:00", "2023-03-24T14:00:00", "binance_source_outage"),
)


def allowed_source_gap_ranges(symbol: str, interval: str) -> tuple[tuple[int, int], ...]:
    if symbol.upper() != FIRST_CYCLE_SYMBOL or interval != FIRST_CYCLE_INTERVAL:
        return ()
    return tuple(gap.range_ms for gap in FIRST_CYCLE_ALLOWED_SOURCE_GAPS)
