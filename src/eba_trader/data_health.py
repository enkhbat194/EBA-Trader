from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class DataHealthStatus(StrEnum):
    STARTING = "starting"
    HEALTHY = "healthy"
    STALE = "stale"
    STOPPED = "stopped"


@dataclass(frozen=True, slots=True)
class DataHealthSnapshot:
    status: DataHealthStatus
    last_event_ns: int | None
    age_ms: float | None
    events_seen: int


class MarketDataHealth:
    """Deterministic market-data freshness tracker.

    The trading/risk layer can use this object without depending on an exchange
    adapter or an AI model. A stale data feed must never be treated as healthy.
    """

    def __init__(self, max_age_ms: int = 15_000) -> None:
        if max_age_ms <= 0:
            raise ValueError("max_age_ms must be positive")
        self.max_age_ms = max_age_ms
        self._last_event_ns: int | None = None
        self._events_seen = 0
        self._stopped = False

    def mark_event(self, received_ns: int) -> None:
        if received_ns <= 0:
            raise ValueError("received_ns must be positive")
        if self._stopped:
            raise RuntimeError("cannot mark an event after data health is stopped")
        if self._last_event_ns is not None and received_ns < self._last_event_ns:
            raise ValueError("received_ns cannot move backwards")
        self._last_event_ns = received_ns
        self._events_seen += 1

    def stop(self) -> None:
        self._stopped = True

    def snapshot(self, now_ns: int) -> DataHealthSnapshot:
        if now_ns <= 0:
            raise ValueError("now_ns must be positive")

        if self._stopped:
            return DataHealthSnapshot(
                status=DataHealthStatus.STOPPED,
                last_event_ns=self._last_event_ns,
                age_ms=self._age_ms(now_ns),
                events_seen=self._events_seen,
            )

        if self._last_event_ns is None:
            return DataHealthSnapshot(
                status=DataHealthStatus.STARTING,
                last_event_ns=None,
                age_ms=None,
                events_seen=0,
            )

        age_ms = self._age_ms(now_ns)
        assert age_ms is not None
        status = (
            DataHealthStatus.STALE
            if age_ms > self.max_age_ms
            else DataHealthStatus.HEALTHY
        )
        return DataHealthSnapshot(
            status=status,
            last_event_ns=self._last_event_ns,
            age_ms=age_ms,
            events_seen=self._events_seen,
        )

    def _age_ms(self, now_ns: int) -> float | None:
        if self._last_event_ns is None:
            return None
        return max(0, now_ns - self._last_event_ns) / 1_000_000
