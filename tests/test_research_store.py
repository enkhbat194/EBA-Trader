from pathlib import Path

import pytest

from eba_trader.lifecycle import StrategyLifecycle
from eba_trader.research_store import ResearchStore, make_experiment_id


def test_register_strategy_version_is_immutable(tmp_path: Path) -> None:
    store = ResearchStore(tmp_path / "research.db")
    first = store.register_strategy_version(
        strategy_id="STR-0001",
        name="Momentum",
        family="momentum",
        version=1,
        spec={"fast": 8, "slow": 21},
    )
    assert first["lifecycle_state"] is StrategyLifecycle.GENERATED

    same = store.register_strategy_version(
        strategy_id="STR-0001",
        name="Momentum",
        family="momentum",
        version=1,
        spec={"slow": 21, "fast": 8},
    )
    assert same["spec_sha256"] == first["spec_sha256"]

    with pytest.raises(ValueError, match="immutable"):
        store.register_strategy_version(
            strategy_id="STR-0001",
            name="Momentum",
            family="momentum",
            version=1,
            spec={"fast": 13, "slow": 34},
        )


def test_lifecycle_transition_is_persisted(tmp_path: Path) -> None:
    store = ResearchStore(tmp_path / "research.db")
    store.register_strategy_version(
        strategy_id="STR-0002",
        name="Breakout",
        version=1,
        spec={"lookback": 20},
    )
    store.record_transition(
        strategy_id="STR-0002",
        strategy_version=1,
        current=StrategyLifecycle.BACKTESTED,
        reason="Development experiment passed minimum gates",
        evidence_ref="experiment:abc",
    )
    record = store.get_strategy_version("STR-0002", 1)
    assert record is not None
    assert record["lifecycle_state"] is StrategyLifecycle.BACKTESTED


def test_experiment_id_is_deterministic_across_parameter_order() -> None:
    left = make_experiment_id(
        strategy_id="STR-0003",
        strategy_version=2,
        stage="backtest",
        parameters={"fast": 8, "slow": 21},
        dataset_ref="btc-1m-2024",
    )
    right = make_experiment_id(
        strategy_id="STR-0003",
        strategy_version=2,
        stage="backtest",
        parameters={"slow": 21, "fast": 8},
        dataset_ref="btc-1m-2024",
    )
    assert left == right


def test_experiment_result_round_trip(tmp_path: Path) -> None:
    store = ResearchStore(tmp_path / "research.db")
    store.register_strategy_version(
        strategy_id="STR-0004",
        name="Mean Reversion",
        version=1,
        spec={"zscore": 2.0},
    )
    experiment_id = store.create_experiment(
        strategy_id="STR-0004",
        strategy_version=1,
        stage="development_backtest",
        parameters={"zscore": 2.0},
        dataset_ref="btc-5m-research",
    )
    assert (
        store.create_experiment(
            strategy_id="STR-0004",
            strategy_version=1,
            stage="development_backtest",
            parameters={"zscore": 2.0},
            dataset_ref="btc-5m-research",
        )
        == experiment_id
    )

    store.record_experiment_result(
        experiment_id,
        status="passed",
        metrics={"expectancy": 0.42, "profit_factor": 1.3},
        evidence_ref="artifact:result-1",
    )
    experiments = store.list_experiments(strategy_id="STR-0004", strategy_version=1)
    assert len(experiments) == 1
    assert experiments[0]["status"] == "passed"
    assert experiments[0]["metrics"]["profit_factor"] == 1.3
