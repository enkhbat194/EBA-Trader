from pathlib import Path

import pytest

from eba_trader.lifecycle import StrategyLifecycle
from eba_trader.research_gates import GateOperator, GateRule, GateSet
from eba_trader.research_queue import ExperimentQueue
from eba_trader.research_store import ResearchStore
from eba_trader.robustness_fanout import (
    RobustnessFanoutPlanner,
    RobustnessPlan,
    RobustnessScenario,
)
from eba_trader.robustness_verdict import RobustnessVerdictEngine


def _batch(tmp_path: Path) -> tuple[ResearchStore, str, tuple[str, ...]]:
    store = ResearchStore(tmp_path / "research.db")
    store.register_strategy_version(
        strategy_id="STR-V",
        name="Verdict Test",
        version=1,
        spec={"adapter": "ema_trend_v1", "fixed": {}, "dataset": {}},
    )
    store.record_transition(
        strategy_id="STR-V",
        strategy_version=1,
        current=StrategyLifecycle.BACKTESTED,
        reason="test development pass",
        evidence_ref="verdict:dev",
    )
    planner = RobustnessFanoutPlanner(store, ExperimentQueue(store))
    batch = planner.create_batch(
        strategy_id="STR-V",
        strategy_version=1,
        dataset_ref="btc.csv",
        plan=RobustnessPlan(
            name="robust-v1",
            version=1,
            base_parameters={"fast_ema": 8, "slow_ema": 21},
            parameter_scenarios=(
                RobustnessScenario("neighbor", {"fast_ema": 9}),
            ),
            cost_scenarios=(
                RobustnessScenario("adverse", {"fee_bps": 12.0, "slippage_bps": 8.0}),
            ),
        ),
    )
    return store, batch.batch_id, batch.experiment_ids


def _gate_set() -> GateSet:
    return GateSet(
        name="robustness-minimums",
        version=1,
        rules=(
            GateRule("pf", "profit_factor", GateOperator.GTE, 1.1),
            GateRule("dd", "max_drawdown", GateOperator.GTE, -0.25),
            GateRule("trades", "trade_count", GateOperator.GTE, 5),
        ),
    )


def _pass(store: ResearchStore, experiment_id: str, *, pf: float = 1.3) -> None:
    store.record_experiment_result(
        experiment_id,
        status="passed",
        metrics={"profit_factor": pf, "max_drawdown": -0.12, "trade_count": 20},
        evidence_ref=f"evidence:{experiment_id}",
    )


def test_all_scenarios_must_pass_and_verdict_is_idempotent(tmp_path: Path) -> None:
    store, batch_id, experiment_ids = _batch(tmp_path)
    for experiment_id in experiment_ids:
        _pass(store, experiment_id)

    engine = RobustnessVerdictEngine(store)
    first = engine.evaluate(batch_id=batch_id, gate_set=_gate_set())
    second = engine.evaluate(batch_id=batch_id, gate_set=_gate_set())

    assert first == second
    assert first.passed is True
    assert first.experiment_count == 2
    assert first.failed_experiment_ids == ()
    assert len(engine.list_verdicts(batch_id)) == 1

    strategy = store.get_strategy_version("STR-V", 1)
    assert strategy is not None
    assert strategy["lifecycle_state"] is StrategyLifecycle.BACKTESTED


def test_one_failed_scenario_fails_batch_without_lifecycle_promotion(tmp_path: Path) -> None:
    store, batch_id, experiment_ids = _batch(tmp_path)
    _pass(store, experiment_ids[0], pf=1.3)
    _pass(store, experiment_ids[1], pf=0.8)

    verdict = RobustnessVerdictEngine(store).evaluate(
        batch_id=batch_id,
        gate_set=_gate_set(),
    )

    assert verdict.passed is False
    assert verdict.failed_experiment_ids == (experiment_ids[1],)
    strategy = store.get_strategy_version("STR-V", 1)
    assert strategy is not None
    assert strategy["lifecycle_state"] is StrategyLifecycle.BACKTESTED


def test_incomplete_batch_cannot_receive_verdict(tmp_path: Path) -> None:
    store, batch_id, experiment_ids = _batch(tmp_path)
    _pass(store, experiment_ids[0])

    with pytest.raises(RuntimeError, match="is not PASSED"):
        RobustnessVerdictEngine(store).evaluate(
            batch_id=batch_id,
            gate_set=_gate_set(),
        )
