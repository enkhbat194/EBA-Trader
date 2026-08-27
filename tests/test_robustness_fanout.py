from pathlib import Path

import pytest

from eba_trader.lifecycle import StrategyLifecycle
from eba_trader.research_queue import ExperimentQueue
from eba_trader.research_store import ResearchStore
from eba_trader.robustness_fanout import (
    MAX_ROBUSTNESS_JOBS,
    RobustnessFanoutPlanner,
    RobustnessPlan,
    RobustnessScenario,
)


def _backtested_store(tmp_path: Path) -> tuple[ResearchStore, ExperimentQueue]:
    store = ResearchStore(tmp_path / "research.db")
    store.register_strategy_version(
        strategy_id="STR-R",
        name="Robustness Test",
        version=1,
        spec={
            "adapter": "ema_trend_v1",
            "fixed": {"initial_cash": 1_000.0},
            "dataset": {
                "symbol": "BTCUSDT",
                "interval": "15m",
                "start_ms": 1_704_067_200_000,
                "end_ms": 1_704_067_200_000 + 80 * 900_000,
            },
        },
    )
    store.record_transition(
        strategy_id="STR-R",
        strategy_version=1,
        current=StrategyLifecycle.BACKTESTED,
        reason="test development gate passed",
        evidence_ref="verdict:test-development",
    )
    return store, ExperimentQueue(store)


def _plan() -> RobustnessPlan:
    return RobustnessPlan(
        name="ema-neighborhood",
        version=1,
        base_parameters={"fast_ema": 8, "slow_ema": 21},
        parameter_scenarios=(
            RobustnessScenario("fast-down", {"fast_ema": 7}),
            RobustnessScenario("fast-up", {"fast_ema": 9}),
        ),
        cost_scenarios=(
            RobustnessScenario("adverse-cost", {"fee_bps": 12.0, "slippage_bps": 8.0}),
        ),
    )


def test_fanout_is_bounded_deterministic_and_idempotent(tmp_path: Path) -> None:
    store, queue = _backtested_store(tmp_path)
    planner = RobustnessFanoutPlanner(store, queue)

    first = planner.create_batch(
        strategy_id="STR-R",
        strategy_version=1,
        dataset_ref="btc.csv",
        plan=_plan(),
    )
    second = planner.create_batch(
        strategy_id="STR-R",
        strategy_version=1,
        dataset_ref="btc.csv",
        plan=_plan(),
    )

    assert first.batch_id == second.batch_id
    assert first.experiment_ids == second.experiment_ids
    assert len(first.experiment_ids) == 3
    batch = planner.get_batch(first.batch_id)
    assert batch is not None
    assert [item["stage"] for item in batch["experiments"]] == [
        "robustness_parameter",
        "robustness_parameter",
        "robustness_cost",
    ]


def test_fanout_requires_v2_backtested_pre_oos_state(tmp_path: Path) -> None:
    store = ResearchStore(tmp_path / "research.db")
    store.register_strategy_version(
        strategy_id="STR-G",
        name="Generated Only",
        version=1,
        spec={"adapter": "ema_trend_v1", "fixed": {}, "dataset": {}},
    )
    planner = RobustnessFanoutPlanner(store, ExperimentQueue(store))

    with pytest.raises(RuntimeError, match="requires BACKTESTED"):
        planner.create_batch(
            strategy_id="STR-G",
            strategy_version=1,
            dataset_ref="btc.csv",
            plan=_plan(),
        )


def test_fanout_cannot_be_reopened_after_robustness_promotion(tmp_path: Path) -> None:
    store, queue = _backtested_store(tmp_path)
    store.record_transition(
        strategy_id="STR-R",
        strategy_version=1,
        current=StrategyLifecycle.ROBUSTNESS_VERIFIED,
        reason="test robustness pass",
        evidence_ref="robustness-verdict:test",
    )

    with pytest.raises(RuntimeError, match="requires BACKTESTED"):
        RobustnessFanoutPlanner(store, queue).create_batch(
            strategy_id="STR-R",
            strategy_version=1,
            dataset_ref="btc.csv",
            plan=_plan(),
        )


def test_cost_scenarios_are_restricted_to_cost_fields() -> None:
    with pytest.raises(ValueError, match="cost scenarios may override only"):
        RobustnessPlan(
            name="bad-cost",
            version=1,
            base_parameters={},
            cost_scenarios=(RobustnessScenario("bad", {"fast_ema": 8}),),
        )


def test_hard_job_cap_blocks_unbounded_fanout() -> None:
    scenarios = tuple(
        RobustnessScenario(f"p-{index}", {"fast_ema": index + 2})
        for index in range(MAX_ROBUSTNESS_JOBS + 1)
    )
    with pytest.raises(ValueError, match="hard job cap"):
        RobustnessPlan(
            name="too-many",
            version=1,
            base_parameters={},
            parameter_scenarios=scenarios,
        )


def test_fixed_strategy_fields_cannot_be_overridden(tmp_path: Path) -> None:
    store, queue = _backtested_store(tmp_path)
    planner = RobustnessFanoutPlanner(store, queue)
    plan = RobustnessPlan(
        name="bad-fixed",
        version=1,
        base_parameters={"initial_cash": 2_000.0},
        parameter_scenarios=(RobustnessScenario("p", {"fast_ema": 8}),),
    )

    with pytest.raises(ValueError, match="immutable strategy fixed fields"):
        planner.create_batch(
            strategy_id="STR-R",
            strategy_version=1,
            dataset_ref="btc.csv",
            plan=plan,
        )
