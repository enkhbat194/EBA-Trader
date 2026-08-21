import pytest

from eba_trader.providers import ProviderEnvironment, ProviderKind
from eba_trader.web_server import parse_connection_request, test_connection_payload


def test_parse_demo_binance_connection_request() -> None:
    profile, credentials = parse_connection_request(
        {
            "provider": "binance",
            "environment": "demo",
            "credentials": {"apiKey": "key", "apiSecret": "secret"},
        }
    )
    assert profile.provider is ProviderKind.BINANCE
    assert profile.environment is ProviderEnvironment.DEMO
    assert credentials.api_key == "key"
    assert credentials.api_secret == "secret"


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
    result = test_connection_payload(
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
    assert result["liveExecutionAllowed"] is False
    assert "not activated" in result["message"].lower()
