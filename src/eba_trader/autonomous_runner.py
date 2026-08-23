from __future__ import annotations

import threading
import time
from collections.abc import Callable
from typing import Any

from .momentum_engine import MomentumPaperEngine
from .paper_engine import PaperExecutionEngine
from .providers import CredentialEnvelope

AUTONOMOUS_SESSION_KEY = "server-autonomous-demo"
DEFAULT_INTERVAL_SECONDS = 15.0


class AutonomousDemoRunner:
    """Server-side paper scanner that does not depend on an open PWA.

    Both strategies remain paper-only. The runner reads Demo market/account data,
    advances the existing paper engines, and never submits an exchange order.
    """

    def __init__(
        self,
        *,
        credentials_loader: Callable[[], CredentialEnvelope | None],
        snapshot_loader: Callable[[CredentialEnvelope], dict[str, Any]],
        paper_engine: PaperExecutionEngine,
        momentum_engine: MomentumPaperEngine,
        interval_seconds: float = DEFAULT_INTERVAL_SECONDS,
        auto_start_carry: bool = True,
        auto_start_fast: bool = True,
    ) -> None:
        if interval_seconds <= 0:
            raise ValueError("interval_seconds must be positive")
        self._credentials_loader = credentials_loader
        self._snapshot_loader = snapshot_loader
        self._paper_engine = paper_engine
        self._momentum_engine = momentum_engine
        self._interval_seconds = float(interval_seconds)
        self._carry_enabled = bool(auto_start_carry)
        self._fast_enabled = bool(auto_start_fast)
        self._thread: threading.Thread | None = None
        self._stop_event = threading.Event()
        self._wake_event = threading.Event()
        self._lock = threading.Lock()
        self._started_at_ms: int | None = None
        self._last_loop_at_ms: int | None = None
        self._last_carry_scan_at_ms: int | None = None
        self._last_fast_scan_at_ms: int | None = None
        self._last_error: str | None = None
        self._last_snapshot: dict[str, Any] | None = None

    def ensure_started(self) -> None:
        with self._lock:
            if self._thread is not None and self._thread.is_alive():
                return
            self._stop_event.clear()
            self._thread = threading.Thread(
                target=self._run_loop,
                name="eba-demo-paper-runner",
                daemon=True,
            )
            self._started_at_ms = int(time.time() * 1000)
            self._thread.start()

    def shutdown(self) -> None:
        self._stop_event.set()
        self._wake_event.set()
        thread = self._thread
        if thread is not None and thread.is_alive():
            thread.join(timeout=max(1.0, self._interval_seconds + 1.0))

    def set_enabled(
        self,
        *,
        carry: bool | None = None,
        fast: bool | None = None,
    ) -> dict[str, Any]:
        with self._lock:
            if carry is not None:
                self._carry_enabled = bool(carry)
            if fast is not None:
                self._fast_enabled = bool(fast)
        self.ensure_started()
        self._wake_event.set()
        return self.status()

    def close_carry(self, *, reason: str = "SERVER_RUNNER_MANUAL_CLOSE") -> dict[str, Any]:
        credentials = self._credentials_loader()
        if credentials is None:
            raise RuntimeError("Binance Demo server secret is not configured")
        snapshot = self._snapshot_loader(credentials)
        state = self._paper_engine.close(
            AUTONOMOUS_SESSION_KEY,
            snapshot,
            reason=reason,
        )
        with self._lock:
            self._last_snapshot = snapshot
            self._last_carry_scan_at_ms = int(time.time() * 1000)
        return state

    def close_fast(self, *, reason: str = "SERVER_RUNNER_MANUAL_CLOSE") -> dict[str, Any]:
        credentials = self._credentials_loader()
        if credentials is None:
            raise RuntimeError("Binance Demo server secret is not configured")
        state = self._momentum_engine.close(
            AUTONOMOUS_SESSION_KEY,
            credentials,
            reason=reason,
        )
        with self._lock:
            self._last_fast_scan_at_ms = int(time.time() * 1000)
        return state

    def status(self) -> dict[str, Any]:
        with self._lock:
            thread_alive = self._thread is not None and self._thread.is_alive()
            carry_enabled = self._carry_enabled
            fast_enabled = self._fast_enabled
            snapshot = dict(self._last_snapshot) if self._last_snapshot is not None else None
            started_at_ms = self._started_at_ms
            last_loop_at_ms = self._last_loop_at_ms
            last_carry_scan_at_ms = self._last_carry_scan_at_ms
            last_fast_scan_at_ms = self._last_fast_scan_at_ms
            last_error = self._last_error
        return {
            "ok": True,
            "serverSide": True,
            "pwaRequired": False,
            "threadAlive": thread_alive,
            "carryRunning": carry_enabled,
            "fastRunning": fast_enabled,
            "intervalSeconds": self._interval_seconds,
            "startedAtMs": started_at_ms,
            "lastLoopAtMs": last_loop_at_ms,
            "lastCarryScanAtMs": last_carry_scan_at_ms,
            "lastFastScanAtMs": last_fast_scan_at_ms,
            "lastError": last_error,
            "snapshot": snapshot,
            "carryState": self._paper_engine.state(AUTONOMOUS_SESSION_KEY),
            "fastState": self._momentum_engine.state(AUTONOMOUS_SESSION_KEY),
            "liveExecutionAllowed": False,
        }

    def _run_loop(self) -> None:
        while not self._stop_event.is_set():
            started = time.monotonic()
            try:
                self._run_iteration()
            except Exception as exc:  # pragma: no cover - final process safety net
                with self._lock:
                    self._last_error = f"runner loop failed: {exc}"
            elapsed = time.monotonic() - started
            delay = max(0.2, self._interval_seconds - elapsed)
            self._wake_event.wait(delay)
            self._wake_event.clear()

    def _run_iteration(self) -> None:
        now_ms = int(time.time() * 1000)
        credentials = self._credentials_loader()
        with self._lock:
            carry_enabled = self._carry_enabled
            fast_enabled = self._fast_enabled
            self._last_loop_at_ms = now_ms

        if credentials is None:
            with self._lock:
                self._last_error = "Binance Demo server secret is not configured"
            return

        errors: list[str] = []
        if carry_enabled:
            try:
                snapshot = self._snapshot_loader(credentials)
                self._paper_engine.step(
                    AUTONOMOUS_SESSION_KEY,
                    snapshot,
                    allow_entry=True,
                    now_ms=now_ms,
                )
                with self._lock:
                    self._last_snapshot = snapshot
                    self._last_carry_scan_at_ms = now_ms
            except Exception as exc:
                errors.append(f"carry: {exc}")

        fast_state = self._momentum_engine.state(AUTONOMOUS_SESSION_KEY)
        fast_has_position = fast_state.get("openPosition") is not None
        if fast_enabled or fast_has_position:
            try:
                self._momentum_engine.step(
                    AUTONOMOUS_SESSION_KEY,
                    credentials,
                    allow_entry=fast_enabled,
                    now_ms=now_ms,
                )
                with self._lock:
                    self._last_fast_scan_at_ms = now_ms
            except Exception as exc:
                errors.append(f"fast: {exc}")

        with self._lock:
            self._last_error = " · ".join(errors) if errors else None
