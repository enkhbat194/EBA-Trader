import pytest

from eba_trader.providers import ProviderEnvironment, ProviderKind
from eba_trader.web_server import parse_connection_request, run_connection_test


def test_parse_demo_binance_connection_request() -> None:
    profile, credentials = parse_connection_request(
        {
            "provider": "binance",
            "environment": "demo",
            "credentials": {
                "apiKey": "spot-key",
                "apiSecret": "spot-secret",
                "futuresApiKey": "futures-key",
                "futuresApiSecret": "futures-secret",
            },
        }
    )
    assert profile.provider is ProviderKind.BINANCE
    assert profile.environment is ProviderEnvironment.DEMO
    assert credentials.api_key == "spot-key"
    assert credentials.api_secret == "spot-secret"
    assert credentials.futures_api_key == "futures-key"
    assert credentials.futures_api_secret == "futures-secret"


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
