from __future__ import annotations

from typing import Any

from eba_trader.autonomous_runner import AUTONOMOUS_SESSION_KEY, AutonomousDemoRunner
from eba_trader.providers import CredentialEnvelope


class FakePaperEngine:
    def state(self, session_key: str) -> dict[str, Any]:
        assert session_key == AUTONOMOUS_SESSION_KEY
        return {"openPosition": None}

    def step(self, *args: Any, **kwargs: Any) -> dict[str, Any]:
        return {"ok": True}

    def close(self, *args: Any, **kwargs: Any) -> dict[str, Any]:
        return {"ok": True}


class FakeMomentumEngine:
    def __init__(self) -> None:
        self.steps: list[tuple[str, CredentialEnvelope, bool]] = []
        self.closes: list[tuple[str, CredentialEnvelope, str]] = []

    def state(self, session_key: str) -> dict[str, Any]:
        assert session_key == AUTONOMOUS_SESSION_KEY
        return {"openPosition": None}

    def step(
        self,
        session_key: str,
        credentials: CredentialEnvelope,
        *,
        allow_entry: bool,
        now_ms: int,
    ) -> dict[str, Any]:
        assert now_ms > 0
        self.steps.append((session_key, credentials, allow_entry))
        return {"openPosition": None}

    def close(
        self,
        session_key: str,
        credentials: CredentialEnvelope,
        *,
        reason: str,
    ) -> dict[str, Any]:
        self.closes.append((session_key, credentials, reason))
        return {"openPosition": None}


def _runner(momentum: FakeMomentumEngine) -> AutonomousDemoRunner:
    return AutonomousDemoRunner(
        credentials_loader=lambda: None,
        snapshot_loader=lambda credentials: {},
        paper_engine=FakePaperEngine(),
        momentum_engine=momentum,
        auto_start_carry=False,
        auto_start_fast=True,
    )


def test_fast_iteration_uses_public_paper_mode_without_account_secret() -> None:
    momentum = FakeMomentumEngine()
    runner = _runner(momentum)

    runner._fast_iteration()

    assert len(momentum.steps) == 1
    session_key, credentials, allow_entry = momentum.steps[0]
    assert session_key == AUTONOMOUS_SESSION_KEY
    assert credentials.api_key == ""
    assert credentials.api_secret == ""
    assert allow_entry is True
    status = runner.status()
    assert status["fastPaperAvailable"] is True
    assert status["demoCredentialsConfigured"] is False
    assert status["fastMarketDataMode"] == "public_demo"
    assert status["fastFeeMode"] == "conservative_fallback"
    assert status["lastError"] is None


def test_fast_manual_close_does_not_require_account_secret() -> None:
    momentum = FakeMomentumEngine()
    runner = _runner(momentum)

    state = runner.close_fast(reason="TEST_CLOSE")

    assert state == {"openPosition": None}
    assert len(momentum.closes) == 1
    session_key, credentials, reason = momentum.closes[0]
    assert session_key == AUTONOMOUS_SESSION_KEY
    assert credentials.api_key == ""
    assert credentials.api_secret == ""
    assert reason == "TEST_CLOSE"
