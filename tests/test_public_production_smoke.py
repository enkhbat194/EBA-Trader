from __future__ import annotations

from typing import Any

import pytest

from eba_trader import public_smoke


def _responses(build_sha: str) -> dict[str, dict[str, Any]]:
    return {
        "/api/app-info": {
            "ok": True,
            "runtime": "linode",
            "httpsReady": True,
            "buildSha": build_sha,
            "liveExecutionAllowed": False,
        },
        "/api/research/status": {
            "ok": True,
            "runtime": "linode",
            "buildSha": build_sha,
            "liveExecutionAllowed": False,
            "locks": {
                "frozenOos": True,
                "realExecution": True,
                "rankingHasLifecycleAuthority": False,
            },
            "researchStore": {"available": True},
        },
        "/api/demo/credential-status": {
            "ok": True,
            "configured": True,
            "credentialMode": "encrypted_server_vault",
            "maskedApiKey": "••••••••abcd",
            "liveExecutionAllowed": False,
        },
        "/api/demo/autoconnect": {
            "ok": True,
            "configured": True,
            "credentialMode": "encrypted_server_vault",
            "sessionToken": "must-not-be-printed",
            "liveExecutionAllowed": False,
        },
        "/api/runner/status": {
            "ok": True,
            "serverSide": True,
            "pwaRequired": False,
            "fastThreadAlive": True,
            "fastRunning": True,
            "demoCredentialsConfigured": True,
            "liveExecutionAllowed": False,
            "fastState": {
                "openPosition": None,
                "history": [],
                "liveExecutionAllowed": False,
            },
        },
        "/api/chart": {
            "provider": "binance",
            "symbol": "BTCUSDT",
            "timeframe": "15m",
            "environment": "demo",
            "liveExecutionAllowed": False,
            "candles": [{"time": 1_000 + index} for index in range(20)],
        },
    }


def test_public_smoke_checks_all_server_truth_surfaces(monkeypatch: pytest.MonkeyPatch) -> None:
    build_sha = "a" * 40
    responses = _responses(build_sha)
    calls: list[str] = []

    def fake_request(
        base_url: str,
        path: str,
        *,
        payload: dict[str, Any] | None = None,
        timeout: float = 15.0,
    ) -> dict[str, Any]:
        del base_url, payload, timeout
        calls.append(path)
        return responses[path]

    monkeypatch.setattr(public_smoke, "_request_json", fake_request)
    summary = public_smoke.run_public_production_smoke(
        base_url="https://example.invalid",
        expected_build=build_sha,
        timeout_seconds=1,
    )

    assert summary.build_sha == build_sha
    assert summary.research_ok is True
    assert summary.demo_vault_ok is True
    assert summary.demo_autoconnect_ok is True
    assert summary.fast_positions_ok is True
    assert summary.chart_ok is True
    assert calls == [
        "/api/app-info",
        "/api/research/status",
        "/api/demo/credential-status",
        "/api/demo/autoconnect",
        "/api/runner/status",
        "/api/chart",
    ]
    assert "sessionToken" not in summary.as_dict()


def test_research_smoke_fails_if_frozen_oos_lock_is_open(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    build_sha = "b" * 40
    response = _responses(build_sha)["/api/research/status"]
    response["locks"]["frozenOos"] = False
    monkeypatch.setattr(public_smoke, "_request_json", lambda *_args, **_kwargs: response)

    with pytest.raises(public_smoke.ProductionSmokeError, match="frozen OOS lock"):
        public_smoke.verify_research("https://example.invalid", expected_build=build_sha)


def test_demo_autoconnect_requires_encrypted_vault(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    response = _responses("c" * 40)["/api/demo/autoconnect"]
    response["credentialMode"] = "legacy_server_env"
    monkeypatch.setattr(public_smoke, "_request_json", lambda *_args, **_kwargs: response)

    with pytest.raises(public_smoke.ProductionSmokeError, match="encrypted Demo vault"):
        public_smoke.verify_demo_autoconnect("https://example.invalid", attempts=1)


def test_positions_smoke_accepts_empty_position_but_requires_persistent_state_shape(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    response = _responses("d" * 40)["/api/runner/status"]
    monkeypatch.setattr(public_smoke, "_request_json", lambda *_args, **_kwargs: response)

    public_smoke.verify_fast_positions("https://example.invalid")
    response["fastState"].pop("openPosition")
    with pytest.raises(public_smoke.ProductionSmokeError, match="openPosition"):
        public_smoke.verify_fast_positions("https://example.invalid")
