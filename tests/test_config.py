import pytest

from eba_trader.config import AppConfig
from eba_trader.domain import ExecutionMode


def test_default_config_is_paper_btcusdt_binance() -> None:
    config = AppConfig()
    config.validate()
    assert config.execution_mode is ExecutionMode.PAPER
    assert config.symbol == "BTCUSDT"
    assert config.primary_venue == "BINANCE"


def test_live_mode_is_locked() -> None:
    config = AppConfig(execution_mode=ExecutionMode.LIVE)
    with pytest.raises(RuntimeError, match="Live execution is locked"):
        config.validate()
