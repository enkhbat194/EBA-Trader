import pytest

from eba_trader.demo_sessions import DemoSessionStore
from eba_trader.providers import (
    ConnectionState,
    ConnectionTestResult,
    CredentialEnvelope,
    ProviderEnvironment,
    ProviderKind,
)
from eba_trader.web_server import (
    parse_connection_request,
    run_connection_test,
    run_demo_disconnect_request,
    run_demo_snapshot_request,
)


def test_parse_demo_binance_connection_request() -> None:
    profile, credentials = parse_connection_request(
        {
            "provider": "binance",
            "environment": "demo",
            "credentials": {
                "apiKey": "demo-key",
                "apiSecret": "demo-secret",
            },
        }
    )
    assert profile.provider is ProviderKind.BINANCE
    assert profile.environment is ProviderEnvironment.DEMO
    assert credentials.api_key == "demo-key"
    assert credentials.api_secret == "demo-secret"


def test_live_connection_request_is_hard_locked() -> None:
    with pytest.raises(ValueError, match="live connections are locked"):
        parse_connection_request(
            {
                "provider": "binance",
                "environment": "live",
                "credentials": {"apiKey": "key", "apiSecret": "secret"},
            }
        )


def test_unknown_provider_is_rejected() -> None:
    with pytest.raises(ValueError, match="unsupported provider"):
        parse_connection_request(
            {"provider": "unknown", "environment": "demo", "credentials": {}}
        )


def test_mt5_scaffold_response_does_not_claim_success() -> None:
    result = run_connection_test(
        {
            "provider": "metatrader5",
            "environment": "demo",
            "credentials": {
                "server": "Broker-Demo",
                "login": "123456",
                "password": "secret",
            },
        }
    )
    assert result["ok"] is False
    assert result["provider"] == "metatrader5"
    assert result["environment"] == "demo"
    assert result["balances"] == {}
    assert result["liveExecutionAllowed"] is False
    assert "not activated" in result["message"].lower()


def test_successful_binance_demo_connection_can_issue_ram_only_session(monkeypatch) -> None:
    class FakeManager:
        def upsert_profile(self, profile) -> None:
            self.profile = profile

        def test_connection(self, connection_id, credentials):
            assert connection_id == "binance-demo"
            assert credentials.api_key == "demo-key"
            assert credentials.api_secret == "demo-secret"
            return ConnectionTestResult(
                ok=True,
                state=ConnectionState.CONNECTED,
                message="DEMO Spot + USD-M connection successful",
                account_label="SPOT",
                balances={"spot": {"USDT": 1000.0}, "usdm": {"USDT": 2000.0}},
            )

    monkeypatch.setattr("eba_trader.web_server.build_default_manager", lambda: FakeManager())
    store = DemoSessionStore(ttl_seconds=60)
    result = run_connection_test(
        {
            "provider": "binance",
            "environment": "demo",
            "credentials": {
                "apiKey": "demo-key",
                "apiSecret": "demo-secret",
            },
        },
        session_store=store,
    )
    token = result["sessionToken"]
    assert token
    assert "demo-key" not in token
    assert "demo-secret" not in token
    stored = store.get(token)
    assert stored is not None
    assert stored.api_key == "demo-key"
    assert result["liveExecutionAllowed"] is False


def test_demo_snapshot_request_uses_session_without_returning_credentials(monkeypatch) -> None:
    store = DemoSessionStore(ttl_seconds=60)
    _, credentials = parse_connection_request(
        {
            "provider": "binance",
            "environment": "demo",
            "credentials": {
                "apiKey": "demo-key",
                "apiSecret": "demo-secret",
            },
        }
    )
    token = store.create(credentials)

    def fake_snapshot(received_credentials):
        assert received_credentials == credentials
        return {
            "decision": "NO_TRADE",
            "reasonCodes": ["TEST"],
            "liveExecutionAllowed": False,
        }

    monkeypatch.setattr("eba_trader.web_server.run_demo_fee_snapshot", fake_snapshot)
    result = run_demo_snapshot_request({"sessionToken": token}, session_store=store)
    assert result["decision"] == "NO_TRADE"
    assert result["liveExecutionAllowed"] is False
    assert "apiSecret" not in result
    assert "credentials" not in result


def test_demo_snapshot_request_rejects_missing_session() -> None:
    store = DemoSessionStore(ttl_seconds=60)
    with pytest.raises(PermissionError, match="missing or expired"):
        run_demo_snapshot_request({"sessionToken": "bad-token"}, session_store=store)


def test_demo_disconnect_revokes_ram_session() -> None:
    store = DemoSessionStore(ttl_seconds=60)
    token = store.create(CredentialEnvelope(api_key="demo-key", api_secret="demo-secret"))
    assert store.get(token) is not None
    result = run_demo_disconnect_request({"sessionToken": token}, session_store=store)
    assert result == {
        "ok": True,
        "state": "disconnected",
        "liveExecutionAllowed": False,
    }
    assert store.get(token) is None
