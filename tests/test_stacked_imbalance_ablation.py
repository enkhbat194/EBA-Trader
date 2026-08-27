from __future__ import annotations

import json
from pathlib import Path

import pytest

from eba_trader.m5_ablation import AblationDefinition, OrderFlowGate
from eba_trader.m5_ablation_cli import GATE_SET_SCHEMA, LEGACY_GATE_SET_SCHEMA, _load_gates


def test_stacked_gate_parameters_are_deterministic_and_integer_bounded() -> None:
    gate = OrderFlowGate(stacked_imbalance_threshold=2)

    assert gate.parameters() == {"stacked_imbalance_threshold": 2}
    assert gate.gate_id == OrderFlowGate(stacked_imbalance_threshold=2).gate_id

    with pytest.raises(ValueError, match="integer >= 1"):
        OrderFlowGate(stacked_imbalance_threshold=0).parameters()
    with pytest.raises(ValueError, match="integer >= 1"):
        OrderFlowGate(stacked_imbalance_threshold=1.5).parameters()  # type: ignore[arg-type]


def test_ablation_definition_accepts_stacked_only_gate_without_changing_baseline_contract() -> None:
    definition = AblationDefinition(
        dataset_ref="m5_orderflow_dev/features/off_stacked.csv",
        symbol="BTCUSDT",
        interval="1m",
        start_ms=1_000,
        end_ms=61_000,
        fast_ema=12,
        slow_ema=26,
        initial_cash=10_000.0,
        fee_bps=4.0,
        slippage_bps=1.5,
        gates=(OrderFlowGate(stacked_imbalance_threshold=2),),
    )

    definition.validate()

    assert definition.fixed_config() == {
        "fast_ema": 12,
        "slow_ema": 26,
        "initial_cash": 10_000.0,
        "fee_bps": 4.0,
        "slippage_bps": 1.5,
    }
    assert definition.gates[0].parameters() == {"stacked_imbalance_threshold": 2}


def test_v2_gate_file_accepts_stacked_and_legacy_gate_file_rejects_it(tmp_path: Path) -> None:
    v2_path = tmp_path / "v2.json"
    v2_path.write_text(
        json.dumps(
            {
                "schema": GATE_SET_SCHEMA,
                "gates": [
                    {"stacked_imbalance_threshold": 1},
                    {"stacked_imbalance_threshold": 3, "delta_ratio_threshold": 0.1},
                ],
            }
        ),
        encoding="utf-8",
    )
    gates = _load_gates(v2_path)
    assert gates[0].parameters() == {"stacked_imbalance_threshold": 1}
    assert gates[1].parameters() == {
        "delta_ratio_threshold": 0.1,
        "stacked_imbalance_threshold": 3,
    }

    legacy_path = tmp_path / "v1.json"
    legacy_path.write_text(
        json.dumps(
            {
                "schema": LEGACY_GATE_SET_SCHEMA,
                "gates": [{"stacked_imbalance_threshold": 1}],
            }
        ),
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="unsupported fields"):
        _load_gates(legacy_path)


def test_stacked_gate_set_remains_development_only_by_contract() -> None:
    definition = AblationDefinition(
        dataset_ref="features.csv",
        symbol="BTCUSDT",
        interval="1m",
        start_ms=0,
        end_ms=60_000,
        fast_ema=12,
        slow_ema=26,
        initial_cash=10_000.0,
        fee_bps=4.0,
        slippage_bps=1.5,
        gates=(OrderFlowGate(stacked_imbalance_threshold=1),),
    )
    definition.validate()
    assert definition.gates[0].parameters()["stacked_imbalance_threshold"] == 1
