from __future__ import annotations

import secrets
import threading
import time
from dataclasses import dataclass
from typing import Any

PAIR_TTL_SECONDS = 15 * 60
BRIDGE_STALE_SECONDS = 45


@dataclass(slots=True)
class _BridgeRecord:
    created_at: float
    expires_at: float
    last_seen: float | None = None
    snapshot: dict[str, Any] | None = None


class MT5BridgeStore:
    """Process-memory-only pairing and read-only MT5 bridge state.

    Pair tokens are capability tokens shared only with the browser and the local
    Windows MT5 bridge. No broker password is stored in the cloud. The record is
    intentionally ephemeral and disappears on Render restart/spin-down.
    """

    def __init__(self, *, pair_ttl_seconds: int = PAIR_TTL_SECONDS) -> None:
        if pair_ttl_seconds <= 0:
            raise ValueError("pair_ttl_seconds must be positive")
        self._pair_ttl_seconds = pair_ttl_seconds
        self._records: dict[str, _BridgeRecord] = {}
        self._lock = threading.Lock()

    def create_pair(self) -> dict[str, Any]:
        now = time.monotonic()
        token = secrets.token_urlsafe(32)
        record = _BridgeRecord(
            created_at=now,
            expires_at=now + self._pair_ttl_seconds,
        )
        with self._lock:
            self._purge_locked(now)
            self._records[token] = record
        return {
            "pairToken": token,
            "expiresInSeconds": self._pair_ttl_seconds,
            "state": "waiting",
        }

    def ingest(self, token: str, snapshot: dict[str, Any]) -> dict[str, Any]:
        now = time.monotonic()
        with self._lock:
            self._purge_locked(now)
            record = self._records.get(token)
            if record is None:
                raise PermissionError("MT5 pair token is missing or expired")
            record.last_seen = now
            record.snapshot = snapshot
            # Once the local bridge is connected, keep the capability alive while
            # heartbeats continue. A stale bridge still fails closed in state().
            record.expires_at = now + self._pair_ttl_seconds
        return {"ok": True, "state": "connected"}

    def state(self, token: str) -> dict[str, Any]:
        now = time.monotonic()
        with self._lock:
            self._purge_locked(now)
            record = self._records.get(token)
            if record is None:
                raise PermissionError("MT5 pair token is missing or expired")
            last_seen = record.last_seen
            snapshot = dict(record.snapshot or {})

        if last_seen is None:
            return {
                "ok": True,
                "state": "waiting",
                "connected": False,
                "snapshot": None,
                "liveExecutionAllowed": False,
            }
        age = max(0.0, now - last_seen)
        connected = age <= BRIDGE_STALE_SECONDS
        return {
            "ok": True,
            "state": "connected" if connected else "stale",
            "connected": connected,
            "heartbeatAgeSeconds": round(age, 1),
            "snapshot": snapshot if connected else None,
            "liveExecutionAllowed": False,
        }

    def revoke(self, token: str) -> None:
        if not token:
            return
        with self._lock:
            self._records.pop(token, None)

    def _purge_locked(self, now: float) -> None:
        expired = [token for token, record in self._records.items() if record.expires_at <= now]
        for token in expired:
            self._records.pop(token, None)
