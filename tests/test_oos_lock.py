from __future__ import annotations

import inspect

from eba_trader import research


def test_frozen_oos_function_has_no_market_or_capital_overrides() -> None:
    parameters = inspect.signature(research.run_frozen_oos_study).parameters
    for forbidden in ("symbol", "interval", "initial_cash", "data_dir"):
        assert forbidden not in parameters


def test_frozen_oos_cli_has_no_market_or_capital_arguments() -> None:
    source = inspect.getsource(research.frozen_oos_cli)
    for forbidden in ('"--symbol"', '"--interval"', '"--cash"', '"--data-dir"'):
        assert forbidden not in source
