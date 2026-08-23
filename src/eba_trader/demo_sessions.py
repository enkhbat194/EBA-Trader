from __future__ import annotations

import secrets
import threading
import time
from dataclasses import dataclass

from .providers import CredentialEnvelope

DEFAULT_DEMO_SESSION_TTL_SECONDS = 30 * 60


@dataclass(frozen=True, slots=True)
class _DemoSession:
    credentials: CredentialEnvelope
    expires_at_monotonic: float


class DemoSessionStore:
    """Process-memory-only credential session store.

    Tokens may be returned to the browser, but credentials never leave this
    process after the connection-test request. Sessions are never written to
    disk and disappear on process restart or TTL expiry.
    """

    def __init__(self, *, ttl_seconds: int = DEFAULT_DEMO_SESSION_TTL_SECONDS) -> None:
        if ttl_seconds <= 0:
            raise ValueError("ttl_seconds must be positive")
        self._ttl_seconds = ttl_seconds
        self._sessions: dict[str, _DemoSession] = {}
        self._lock = threading.Lock()

    def create(self, credentials: CredentialEnvelope) -> str:
        token = secrets.token_urlsafe(32)
        record = _DemoSession(
            credentials=credentials,
            expires_at_monotonic=time.monotonic() + self._ttl_seconds,
        )
        with self._lock:
            self._purge_expired_locked()
            self._sessions[token] = record
        return token

    def get(self, token: str) -> CredentialEnvelope | None:
        if not token:
            return None
        with self._lock:
            self._purge_expired_locked()
            record = self._sessions.get(token)
            return record.credentials if record is not None else None

    def revoke(self, token: str) -> None:
        if not token:
            return
        with self._lock:
            self._sessions.pop(token, None)

    def _purge_expired_locked(self) -> None:
        now = time.monotonic()
        expired = [
            token
            for token, record in self._sessions.items()
            if record.expires_at_monotonic <= now
        ]
        for token in expired:
            self._sessions.pop(token, None)
