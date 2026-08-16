import pytest

from eba_trader.binance_probe import BinanceDataEnvironment, BinanceProbeSettings


def test_live_public_probe_needs_no_credentials(monkeypatch) -> None:
    monkeypatch.delenv("BINANCE_DEMO_API_KEY", raising=False)
    monkeypatch.delenv("BINANCE_DEMO_API_SECRET", raising=False)

    settings = BinanceProbeSettings(environment=BinanceDataEnvironment.LIVE_PUBLIC)

    assert settings.validate_demo_credentials() == (None, None)
    assert settings.instrument_id == "BTCUSDT.BINANCE"


def test_demo_probe_requires_environment_credentials(monkeypatch) -> None:
    monkeypatch.delenv("BINANCE_DEMO_API_KEY", raising=False)
    monkeypatch.delenv("BINANCE_DEMO_API_SECRET", raising=False)
    settings = BinanceProbeSettings(environment=BinanceDataEnvironment.DEMO)

    with pytest.raises(RuntimeError, match="BINANCE_DEMO_API_KEY"):
        settings.validate_demo_credentials()


def test_demo_probe_reads_environment_credentials(monkeypatch) -> None:
    monkeypatch.setenv("BINANCE_DEMO_API_KEY", "demo-key")
    monkeypatch.setenv("BINANCE_DEMO_API_SECRET", "demo-secret")
    settings = BinanceProbeSettings(environment=BinanceDataEnvironment.DEMO)

    assert settings.validate_demo_credentials() == ("demo-key", "demo-secret")


def test_data_environment_is_restricted(monkeypatch) -> None:
    monkeypatch.setenv("EBA_BINANCE_DATA_ENV", "live")

    with pytest.raises(RuntimeError, match="live_public"):
        BinanceProbeSettings.from_env()
