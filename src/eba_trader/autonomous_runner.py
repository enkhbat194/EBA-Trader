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
PUBLIC_PAPER_CREDENTIALS = CredentialEnvelope(api_key="", api_secret="")


class AutonomousDemoRunner:
    """Server-side paper scanners that do not depend on an open PWA.

    Carry and Fast Momentum run in independent threads so a slower carry snapshot
    cannot delay the fast scanner. Fast Momentum may use public Binance Demo market
    data with a conservative fallback taker fee when account credentials are absent.
    Both engines remain paper-only and never send exchange orders.
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
        self._carry_thread: threading.Thread | None = None
        self._fast_thread: threading.Thread | None = None
        self._stop_event = threading.Event()
        self._carry_wake_event = threading.Event()
        self._fast_wake_event = threading.Event()
        self._lock = threading.Lock()
        self._started_at_ms: int | None = None
        self._last_carry_scan_at_ms: int | None = None
        self._last_fast_scan_at_ms: int | None = None
        self._carry_error: str | None = None
        self._fast_error: str | None = None
        self._last_snapshot: dict[str, Any] | None = None

    def ensure_started(self) -> None:
        with self._lock:
            carry_alive = self._carry_thread is not None and self._carry_thread.is_alive()
            fast_alive = self._fast_thread is not None and self._fast_thread.is_alive()
            if carry_alive and fast_alive:
                return
            self._stop_event.clear()
            if self._started_at_ms is None:
                self._started_at_ms = int(time.time() * 1000)
            if not carry_alive:
                self._carry_thread = threading.Thread(
                    target=self._carry_loop,
                    name="eba-demo-carry-runner",
                    daemon=True,
                )
                self._carry_thread.start()
            if not fast_alive:
                self._fast_thread = threading.Thread(
                    target=self._fast_loop,
                    name="eba-demo-fast-runner",
                    daemon=True,
                )
                self._fast_thread.start()

    def shutdown(self) -> None:
        self._stop_event.set()
        self._carry_wake_event.set()
        self._fast_wake_event.set()
        timeout = max(1.0, self._interval_seconds + 1.0)
        for thread in (self._carry_thread, self._fast_thread):
            if thread is not None and thread.is_alive():
                thread.join(timeout=timeout)

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
        if carry is not None:
            self._carry_wake_event.set()
        if fast is not None:
            self._fast_wake_event.set()
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
        credentials = self._fast_credentials()
        state = self._momentum_engine.close(
            AUTONOMOUS_SESSION_KEY,
            credentials,
            reason=reason,
        )
        with self._lock:
            self._last_fast_scan_at_ms = int(time.time() * 1000)
        return state

    def status(self) -> dict[str, Any]:
        credentials_configured = self._credentials_loader() is not None
        with self._lock:
            carry_alive = self._carry_thread is not None and self._carry_thread.is_alive()
            fast_alive = self._fast_thread is not None and self._fast_thread.is_alive()
            carry_enabled = self._carry_enabled
            fast_enabled = self._fast_enabled
            snapshot = dict(self._last_snapshot) if self._last_snapshot is not None else None
            started_at_ms = self._started_at_ms
            last_carry_scan_at_ms = self._last_carry_scan_at_ms
            last_fast_scan_at_ms = self._last_fast_scan_at_ms
            errors = [item for item in (self._carry_error, self._fast_error) if item]
        last_loop_values = [
            value for value in (last_carry_scan_at_ms, last_fast_scan_at_ms) if value is not None
        ]
        return {
            "ok": True,
            "serverSide": True,
            "pwaRequired": False,
            "threadAlive": carry_alive and fast_alive,
            "carryThreadAlive": carry_alive,
            "fastThreadAlive": fast_alive,
            "carryRunning": carry_enabled,
            "fastRunning": fast_enabled,
            "fastPaperAvailable": True,
            "demoCredentialsConfigured": credentials_configured,
            "fastMarketDataMode": (
                "authenticated_demo" if credentials_configured else "public_demo"
            ),
            "fastFeeMode": (
                "account_commission_with_fallback"
                if credentials_configured
                else "conservative_fallback"
            ),
            "intervalSeconds": self._interval_seconds,
            "startedAtMs": started_at_ms,
            "lastLoopAtMs": max(last_loop_values) if last_loop_values else None,
            "lastCarryScanAtMs": last_carry_scan_at_ms,
            "lastFastScanAtMs": last_fast_scan_at_ms,
            "lastError": " · ".join(errors) if errors else None,
            "snapshot": snapshot,
            "carryState": self._paper_engine.state(AUTONOMOUS_SESSION_KEY),
            "fastState": self._momentum_engine.state(AUTONOMOUS_SESSION_KEY),
            "liveExecutionAllowed": False,
        }

    def _fast_credentials(self) -> CredentialEnvelope:
        credentials = self._credentials_loader()
        return credentials if credentials is not None else PUBLIC_PAPER_CREDENTIALS

    def _carry_loop(self) -> None:
        while not self._stop_event.is_set():
            started = time.monotonic()
            self._carry_iteration()
            elapsed = time.monotonic() - started
            delay = max(0.2, self._interval_seconds - elapsed)
            self._carry_wake_event.wait(delay)
            self._carry_wake_event.clear()

    def _fast_loop(self) -> None:
        while not self._stop_event.is_set():
            started = time.monotonic()
            self._fast_iteration()
            elapsed = time.monotonic() - started
            delay = max(0.2, self._interval_seconds - elapsed)
            self._fast_wake_event.wait(delay)
            self._fast_wake_event.clear()

    def _carry_iteration(self) -> None:
        with self._lock:
            enabled = self._carry_enabled
        if not enabled:
            return
        credentials = self._credentials_loader()
        if credentials is None:
            with self._lock:
                self._carry_error = "carry: Binance Demo server secret is not configured"
            return
        now_ms = int(time.time() * 1000)
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
                self._carry_error = None
        except Exception as exc:  # pragma: no cover - network failure path
            with self._lock:
                self._carry_error = f"carry: {exc}"

    def _fast_iteration(self) -> None:
        with self._lock:
            enabled = self._fast_enabled
        current = self._momentum_engine.state(AUTONOMOUS_SESSION_KEY)
        has_position = current.get("openPosition") is not None
        if not enabled and not has_position:
            return
        credentials = self._fast_credentials()
        now_ms = int(time.time() * 1000)
        try:
            self._momentum_engine.step(
                AUTONOMOUS_SESSION_KEY,
                credentials,
                allow_entry=enabled,
                now_ms=now_ms,
            )
            with self._lock:
                self._last_fast_scan_at_ms = now_ms
                self._fast_error = None
        except Exception as exc:  # pragma: no cover - network failure path
            with self._lock:
                self._fast_error = f"fast: {exc}"
