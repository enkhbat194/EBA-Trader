from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_binance_probe_does_not_log_every_market_tick() -> None:
    source = (ROOT / "src/eba_trader/binance_probe.py").read_text(encoding="utf-8")

    assert "log_data=False" in source
    assert "log_data=True" not in source


def test_binance_data_service_rate_limits_log_bursts() -> None:
    service = (ROOT / "deploy/systemd/eba-binance-data.service").read_text(encoding="utf-8")

    assert "StandardOutput=journal" in service
    assert "StandardError=journal" in service
    assert "LogRateLimitIntervalSec=30s" in service
    assert "LogRateLimitBurst=200" in service
