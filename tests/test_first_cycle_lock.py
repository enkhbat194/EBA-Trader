from __future__ import annotations

import inspect

from eba_trader import evidence, locked_cli
from eba_trader.study_policy import (
    FIRST_CYCLE_FAST_EMA,
    FIRST_CYCLE_INITIAL_CASH,
    FIRST_CYCLE_INTERVAL,
    FIRST_CYCLE_SLOW_EMA,
    FIRST_CYCLE_SYMBOL,
)


def test_first_cycle_policy_is_explicit() -> None:
    assert FIRST_CYCLE_SYMBOL == "BTCUSDT"
    assert FIRST_CYCLE_INTERVAL == "15m"
    assert FIRST_CYCLE_FAST_EMA == 20
    assert FIRST_CYCLE_SLOW_EMA == 50
    assert FIRST_CYCLE_INITIAL_CASH == 1000.0


def test_development_function_has_no_market_parameter_or_capital_overrides() -> None:
    parameters = inspect.signature(evidence.run_development_evidence).parameters
    for forbidden in ("symbol", "interval", "fast_ema", "slow_ema", "initial_cash"):
        assert forbidden not in parameters


def test_development_cli_has_no_configuration_override_flags() -> None:
    source = inspect.getsource(evidence.development_evidence_cli)
    for forbidden in ('"--symbol"', '"--interval"', '"--fast"', '"--slow"', '"--cash"'):
        assert forbidden not in source


def test_public_baseline_cli_has_no_configuration_override_flags() -> None:
    source = inspect.getsource(locked_cli.baseline_study_cli)
    for forbidden in ('"--symbol"', '"--interval"', '"--fast"', '"--slow"', '"--cash"'):
        assert forbidden not in source
