from __future__ import annotations

import json
from pathlib import Path

from eba_trader.binance_demo_execution import BinanceDemoExecutionClient


def test_demo_position_risk_uses_v2_for_flat_symbol_precheck() -> None:
    source = Path("src/eba_trader/binance_demo_execution.py").read_text(encoding="utf-8")

    assert '"/fapi/v2/positionRisk"' in source
    assert '"/fapi/v3/positionRisk"' not in source
    assert BinanceDemoExecutionClient.position_risk.__name__ == "position_risk"


def test_corrected_probe_uses_new_one_shot_id() -> None:
    payload = json.loads(
        Path("config/binance_demo_execution_probe_v1.json").read_text(encoding="utf-8")
    )

    assert payload["probe_id"] == "usdm-btcusdt-roundtrip-20260829-v3"
    assert payload["enabled"] is True
