from eba_trader.providers import (
    BinanceProviderAdapter,
    ConnectionManager,
    ConnectionProfile,
    ConnectionState,
    CredentialEnvelope,
    MetaTrader4ProviderAdapter,
    MetaTrader5ProviderAdapter,
    ProviderCapability,
    ProviderEnvironment,
    ProviderKind,
)
from eba_trader.providers.binance import BINANCE_ENDPOINTS


def _manager() -> ConnectionManager:
    manager = ConnectionManager()
    manager.register(ProviderKind.BINANCE, BinanceProviderAdapter)
    manager.register(ProviderKind.METATRADER5, MetaTrader5ProviderAdapter)
    manager.register(ProviderKind.METATRADER4, MetaTrader4ProviderAdapter)
    return manager


def test_demo_is_first_class_binance_environment() -> None:
    endpoints = BINANCE_ENDPOINTS[ProviderEnvironment.DEMO]
    assert endpoints.spot_rest == "https://testnet.binance.vision"
    assert endpoints.futures_rest == "https://testnet.binancefuture.com"


def test_connection_manager_is_provider_neutral() -> None:
    manager = _manager()
    manager.upsert_profile(
        ConnectionProfile(
            connection_id="binance-demo",
            provider=ProviderKind.BINANCE,
            environment=ProviderEnvironment.DEMO,
            label="Binance Demo",
        )
    )
    manager.upsert_profile(
        ConnectionProfile(
            connection_id="mt5-demo",
            provider=ProviderKind.METATRADER5,
            environment=ProviderEnvironment.DEMO,
            label="MT5 Demo",
        )
    )

    assert [profile.connection_id for profile in manager.list_profiles()] == [
        "binance-demo",
        "mt5-demo",
    ]
    adapter = manager.build_adapter("binance-demo", CredentialEnvelope())
    assert isinstance(adapter, BinanceProviderAdapter)
    assert ProviderCapability.LIVE_EXECUTION not in adapter.capabilities


def test_binance_missing_credentials_fails_closed_without_network() -> None:
    profile = ConnectionProfile(
        connection_id="binance-demo",
        provider=ProviderKind.BINANCE,
        environment=ProviderEnvironment.DEMO,
        label="Binance Demo",
    )
    result = BinanceProviderAdapter(profile, CredentialEnvelope()).test_connection()
    assert result.ok is False
    assert result.state is ConnectionState.ERROR
    assert "required" in result.message.lower()


def test_binance_demo_connection_returns_read_only_balances(monkeypatch) -> None:
    profile = ConnectionProfile(
        connection_id="binance-demo",
        provider=ProviderKind.BINANCE,
        environment=ProviderEnvironment.DEMO,
        label="Binance Demo",
    )
    adapter = BinanceProviderAdapter(
        profile,
        CredentialEnvelope(api_key="key", api_secret="secret"),
    )

    def fake_signed_get(base_url, path, *, params=None):
        assert base_url == "https://testnet.binance.vision"
        assert path == "/api/v3/account"
        assert params == {"omitZeroBalances": "true"}
        return {
            "accountType": "SPOT",
            "balances": [
                {"asset": "USDT", "free": "1234.50", "locked": "5.50"},
                {"asset": "BTC", "free": "0.01", "locked": "0"},
            ],
        }

    monkeypatch.setattr(adapter, "_signed_get", fake_signed_get)
    result = adapter.test_connection()
    assert result.ok is True
    assert result.state is ConnectionState.CONNECTED
    assert result.balances["USDT"] == 1240.0
    assert result.balances["BTC"] == 0.01


def test_metatrader_scaffolds_do_not_claim_connection() -> None:
    credentials = CredentialEnvelope(login="123", password="secret", server="Demo-Server")
    for provider, adapter_type in (
        (ProviderKind.METATRADER5, MetaTrader5ProviderAdapter),
        (ProviderKind.METATRADER4, MetaTrader4ProviderAdapter),
    ):
        profile = ConnectionProfile(
            connection_id=provider.value,
            provider=provider,
            environment=ProviderEnvironment.DEMO,
            label=provider.value,
        )
        result = adapter_type(profile, credentials).test_connection()
        assert result.ok is False
        assert result.state is ConnectionState.DISCONNECTED
        assert "not activated" in result.message.lower()


def test_credentials_redact_secrets() -> None:
    credentials = CredentialEnvelope(
        api_key="abc",
        api_secret="def",
        login="123",
        password="pw",
        server="Demo",
    )
    redacted = credentials.redacted()
    assert redacted["api_key"] != "abc"
    assert redacted["api_secret"] != "def"
    assert redacted["password"] != "pw"
    assert redacted["login"] == "123"
