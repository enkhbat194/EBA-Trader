from __future__ import annotations

import math

import pytest

from eba_trader.m5_ablation import (
    ABLATION_STAGE,
    MAX_ORDERFLOW_VARIANTS,
    AblationDefinition,
    M5OrderFlowAblationOrchestrator,
    OrderFlowGate,
)
from eba_trader.research_queue import ExperimentQueue
from eba_trader.research_store import ResearchStore


def _definition(**overrides: object) -> AblationDefinition:
    values: dict[str, object] = {
        "dataset_ref": "sha256:feature-dataset-001",
        "symbol": "BTCUSDT",
        "interval": "1m",
        "start_ms": 1_700_000_000_000,
        "end_ms": 1_700_086_400_000,
        "fast_ema": 12,
        "slow_ema": 26,
        "initial_cash": 10_000.0,
        "fee_bps": 4.0,
        "slippage_bps": 1.5,
        "trade_start_time_ms": 1_700_003_600_000,
        "gates": (
            OrderFlowGate(delta_ratio_threshold=0.05),
            OrderFlowGate(delta_ratio_threshold=0.10),
            OrderFlowGate(cvd_threshold=0.0),
            OrderFlowGate(delta_ratio_threshold=0.10, cvd_threshold=0.0),
        ),
        "max_attempts": 3,
    }
    values.update(overrides)
    return AblationDefinition(**values)  # type: ignore[arg-type]


def _orchestrator(tmp_path):
    store = ResearchStore(tmp_path / "research.db")
    queue = ExperimentQueue(store)
    return store, queue, M5OrderFlowAblationOrchestrator(store, queue)


def test_ablation_emission_is_deterministic_and_idempotent(tmp_path) -> None:
    store, _, orchestrator = _orchestrator(tmp_path)
    definition = _definition()

    first = orchestrator.emit(definition)
    second = orchestrator.emit(definition)

    assert first == second
    assert len(first.pairs) == 4
    assert len(first.experiment_ids) == 5
    assert len(set(first.experiment_ids)) == 5
    assert {pair.baseline_experiment_id for pair in first.pairs} == {
        first.baseline_experiment_id
    }

    baseline_runs = store.list_experiments(
        strategy_id=first.baseline_strategy_id,
        strategy_version=1,
    )
    treatment_runs = store.list_experiments(
        strategy_id=first.orderflow_strategy_id,
        strategy_version=1,
    )
    assert len(baseline_runs) == 1
    assert len(treatment_runs) == 4
    assert baseline_runs[0]["stage"] == ABLATION_STAGE
    assert baseline_runs[0]["parameters"] == {}
    assert {run["experiment_id"] for run in treatment_runs} == {
        pair.orderflow_experiment_id for pair in first.pairs
    }


def test_arms_share_dataset_and_execution_assumptions(tmp_path) -> None:
    store, _, orchestrator = _orchestrator(tmp_path)
    definition = _definition()
    batch = orchestrator.emit(definition)

    baseline = store.get_strategy_version(batch.baseline_strategy_id, 1)
    treatment = store.get_strategy_version(batch.orderflow_strategy_id, 1)
    assert baseline is not None
    assert treatment is not None

    baseline_spec = baseline["spec"]
    treatment_spec = treatment["spec"]
    assert baseline_spec["adapter"] == "ema_feature_baseline_v1"
    assert treatment_spec["adapter"] == "ema_orderflow_v1"
    assert baseline_spec["dataset"] == treatment_spec["dataset"]
    assert baseline_spec["fixed"] == treatment_spec["fixed"]
    assert baseline_spec["fixed"] == {
        "fast_ema": 12,
        "slow_ema": 26,
        "initial_cash": 10_000.0,
        "fee_bps": 4.0,
        "slippage_bps": 1.5,
        "trade_start_time_ms": 1_700_003_600_000,
    }

    for pair in batch.pairs:
        assert pair.orderflow_parameters
        assert set(pair.orderflow_parameters) <= {
            "delta_ratio_threshold",
            "cvd_threshold",
        }


def test_gate_order_does_not_change_batch_identity(tmp_path) -> None:
    _, _, orchestrator = _orchestrator(tmp_path)
    gates = _definition().gates

    forward = orchestrator.emit(_definition(gates=gates))
    reverse = orchestrator.emit(_definition(gates=tuple(reversed(gates))))

    assert forward == reverse


def test_dataset_or_cost_change_changes_experiment_identity(tmp_path) -> None:
    _, _, orchestrator = _orchestrator(tmp_path)

    original = orchestrator.emit(_definition())
    different_dataset = orchestrator.emit(_definition(dataset_ref="sha256:feature-dataset-002"))
    different_cost = orchestrator.emit(_definition(fee_bps=5.0))

    assert original.batch_id != different_dataset.batch_id
    assert original.baseline_experiment_id != different_dataset.baseline_experiment_id
    assert original.batch_id != different_cost.batch_id
    assert original.baseline_experiment_id != different_cost.baseline_experiment_id


def test_orchestrator_is_development_only_and_has_no_oos_switch(tmp_path) -> None:
    store, _, orchestrator = _orchestrator(tmp_path)
    batch = orchestrator.emit(_definition())

    for strategy_id in (batch.baseline_strategy_id, batch.orderflow_strategy_id):
        runs = store.list_experiments(strategy_id=strategy_id, strategy_version=1)
        assert runs
        assert {run["stage"] for run in runs} == {ABLATION_STAGE}


def test_invalid_gate_and_unbounded_fanout_fail_closed(tmp_path) -> None:
    _, _, orchestrator = _orchestrator(tmp_path)

    with pytest.raises(ValueError, match="at least one order-flow gate"):
        orchestrator.emit(_definition(gates=()))
    with pytest.raises(ValueError, match="requires delta_ratio_threshold or cvd_threshold"):
        orchestrator.emit(_definition(gates=(OrderFlowGate(),)))
    with pytest.raises(ValueError, match="duplicate order-flow gate"):
        orchestrator.emit(
            _definition(
                gates=(
                    OrderFlowGate(delta_ratio_threshold=0.1),
                    OrderFlowGate(delta_ratio_threshold=0.1),
                )
            )
        )
    with pytest.raises(ValueError, match=f"capped at {MAX_ORDERFLOW_VARIANTS}"):
        orchestrator.emit(
            _definition(
                gates=tuple(
                    OrderFlowGate(delta_ratio_threshold=index / 1000)
                    for index in range(MAX_ORDERFLOW_VARIANTS + 1)
                )
            )
        )
    with pytest.raises(ValueError, match="must be finite"):
        orchestrator.emit(
            _definition(gates=(OrderFlowGate(delta_ratio_threshold=math.inf),))
        )


def test_invalid_common_assumptions_fail_closed(tmp_path) -> None:
    _, _, orchestrator = _orchestrator(tmp_path)

    with pytest.raises(ValueError, match="fast_ema < slow_ema"):
        orchestrator.emit(_definition(fast_ema=26, slow_ema=26))
    with pytest.raises(ValueError, match="initial_cash must be positive"):
        orchestrator.emit(_definition(initial_cash=0.0))
    with pytest.raises(ValueError, match="fee_bps must be non-negative"):
        orchestrator.emit(_definition(fee_bps=-0.1))
    with pytest.raises(ValueError, match="slippage_bps must be non-negative"):
        orchestrator.emit(_definition(slippage_bps=-0.1))
    with pytest.raises(ValueError, match="trade_start_time_ms must be inside"):
        orchestrator.emit(_definition(trade_start_time_ms=1_800_000_000_000))
