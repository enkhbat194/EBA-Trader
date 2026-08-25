from pathlib import Path

from eba_trader.m5_emitter import M5ExperimentEmitter
from eba_trader.m5_factory import ParameterFamily
from eba_trader.m5_hypothesis import (
    ComparisonOperator,
    Condition,
    StrategyHypothesis,
    TradeDirection,
)
from eba_trader.research_queue import ExperimentQueue
from eba_trader.research_store import ResearchStore


def _hypothesis() -> StrategyHypothesis:
    return StrategyHypothesis(
        family="orderflow_momentum",
        version=1,
        direction=TradeDirection.LONG,
        timeframe="1m",
        features=("ema_fast", "ema_slow", "of_delta_ratio"),
        entry_all=(
            Condition("of_delta_ratio", ComparisonOperator.GT, 0.2),
            Condition("ema_fast", ComparisonOperator.GT, 0.0),
        ),
    )


def test_emitter_registers_immutable_hypothesis_and_deduplicates_experiments(
    tmp_path: Path,
) -> None:
    store = ResearchStore(tmp_path / "research.db")
    emitter = M5ExperimentEmitter(store, ExperimentQueue(store))
    family = ParameterFamily({"ema_fast": (8, 13), "delta_threshold": (0.1, 0.2)})

    first = emitter.emit(
        hypothesis=_hypothesis(),
        parameter_family=family,
        dataset_ref="btc_1m_dev.csv",
    )
    second = emitter.emit(
        hypothesis=_hypothesis(),
        parameter_family=family,
        dataset_ref="btc_1m_dev.csv",
    )

    assert first == second
    assert len(first.experiment_ids) == 4
    assert len(set(first.experiment_ids)) == 4

    record = store.get_strategy_version(first.strategy_id, 1)
    assert record is not None
    assert record["spec"]["schema"] == "m5_hypothesis_v1"
    assert record["spec"]["hypothesis"]["features"] == [
        "ema_fast",
        "ema_slow",
        "of_delta_ratio",
    ]

    experiments = store.list_experiments(
        strategy_id=first.strategy_id,
        strategy_version=1,
    )
    assert len(experiments) == 4
    assert all(item["status"] == "queued" for item in experiments)
    assert all(item["stage"] == "m5_candidate" for item in experiments)


def test_dataset_changes_experiment_identity(tmp_path: Path) -> None:
    store = ResearchStore(tmp_path / "research.db")
    emitter = M5ExperimentEmitter(store, ExperimentQueue(store))
    family = ParameterFamily({"ema_fast": (8,)})

    first = emitter.emit(
        hypothesis=_hypothesis(),
        parameter_family=family,
        dataset_ref="btc_dev_a.csv",
    )
    second = emitter.emit(
        hypothesis=_hypothesis(),
        parameter_family=family,
        dataset_ref="btc_dev_b.csv",
    )

    assert first.strategy_id == second.strategy_id
    assert first.experiment_ids != second.experiment_ids
