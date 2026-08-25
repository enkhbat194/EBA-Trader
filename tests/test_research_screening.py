from pathlib import Path

import pytest

from eba_trader.history import INTERVAL_MS, Candle, save_csv
from eba_trader.lifecycle import StrategyLifecycle
from eba_trader.research_evidence import ResearchEvidenceStore
from eba_trader.research_gates import GateOperator, GateRule, GateSet
from eba_trader.research_queue import ExperimentQueue
from eba_trader.research_screening import DevelopmentScreeningOrchestrator
from eba_trader.research_store import ResearchStore
from eba_trader.research_worker import ResearchBacktestWorker, WorkerOutcome


def _dataset(tmp_path: Path) -> tuple[Path, int, int]:
    start_ms = 1_704_067_200_000
    step = INTERVAL_MS["15m"]
    count = 80
    previous_close = 100.0
    candles: list[Candle] = []
    for index in range(count):
        open_price = previous_close
        close_price = open_price + (1.2 if index % 20 < 10 else -0.9)
        open_time = start_ms + index * step
        candles.append(
            Candle(
                open_time_ms=open_time,
                open=open_price,
                high=max(open_price, close_price) + 0.5,
                low=min(open_price, close_price) - 0.5,
                close=close_price,
                volume=100.0 + index,
                close_time_ms=open_time + step - 1,
                quote_volume=(100.0 + index) * close_price,
                trade_count=100 + index,
            )
        )
        previous_close = close_price
    return save_csv(candles, tmp_path / "btc.csv"), start_ms, start_ms + count * step


def _provenance() -> dict[str, object]:
    return {
        "git_commit": "screening-test-commit",
        "git_branch": "test",
        "tracked_working_tree_clean": True,
        "python_version": "test",
    }


def _prepared(tmp_path: Path) -> tuple[ResearchStore, str, ResearchEvidenceStore]:
    _, start_ms, end_ms = _dataset(tmp_path)
    store = ResearchStore(tmp_path / "research.db")
    store.register_strategy_version(
        strategy_id="STR-S",
        name="Screening Test",
        version=1,
        spec={
            "adapter": "ema_trend_v1",
            "fixed": {"initial_cash": 1_000.0},
            "dataset": {
                "symbol": "BTCUSDT",
                "interval": "15m",
                "start_ms": start_ms,
                "end_ms": end_ms,
            },
        },
    )
    queue = ExperimentQueue(store)
    experiment_id = queue.enqueue(
        strategy_id="STR-S",
        strategy_version=1,
        stage="development_backtest",
        parameters={
            "fast_ema": 3,
            "slow_ema": 8,
            "fee_bps": 1.0,
            "slippage_bps": 1.0,
        },
        dataset_ref="btc.csv",
    )
    evidence_store = ResearchEvidenceStore(store, tmp_path / "evidence")
    worker = ResearchBacktestWorker(
        store=store,
        queue=queue,
        evidence_store=evidence_store,
        dataset_resolver=lambda ref: tmp_path / ref,
        source_provenance_provider=_provenance,
    )
    result = worker.run_once(worker_id="worker-a", now_ms=1_000)
    assert result.outcome is WorkerOutcome.PASSED
    return store, experiment_id, evidence_store


def _passing_gates() -> GateSet:
    return GateSet(
        name="development-screen",
        version=1,
        rules=(
            GateRule("minimum-trades", "trade_count", GateOperator.GTE, 1),
            GateRule("equity-positive", "final_equity", GateOperator.GT, 0.0),
            GateRule("drawdown-bounded", "max_drawdown", GateOperator.GTE, -1.0),
        ),
    )


def test_all_declared_gates_pass_promotes_generated_to_backtested(tmp_path: Path) -> None:
    store, experiment_id, _ = _prepared(tmp_path)
    orchestrator = DevelopmentScreeningOrchestrator(store)

    verdict = orchestrator.screen(
        strategy_id="STR-S",
        strategy_version=1,
        experiment_id=experiment_id,
        gate_set=_passing_gates(),
    )

    assert verdict.passed is True
    assert verdict.promoted is True
    strategy = store.get_strategy_version("STR-S", 1)
    assert strategy is not None
    assert strategy["lifecycle_state"] is StrategyLifecycle.BACKTESTED

    stored = orchestrator.list_verdicts("STR-S", 1)
    assert len(stored) == 1
    assert stored[0]["passed"] is True
    assert stored[0]["verdict_id"] == verdict.verdict_id


def test_failed_gate_persists_verdict_without_promotion(tmp_path: Path) -> None:
    store, experiment_id, _ = _prepared(tmp_path)
    orchestrator = DevelopmentScreeningOrchestrator(store)
    failing = GateSet(
        name="development-screen",
        version=1,
        rules=(GateRule("impossible-return", "total_return", GateOperator.GTE, 100.0),),
    )

    verdict = orchestrator.screen(
        strategy_id="STR-S",
        strategy_version=1,
        experiment_id=experiment_id,
        gate_set=failing,
    )

    assert verdict.passed is False
    assert verdict.promoted is False
    strategy = store.get_strategy_version("STR-S", 1)
    assert strategy is not None
    assert strategy["lifecycle_state"] is StrategyLifecycle.GENERATED
    assert orchestrator.list_verdicts("STR-S", 1)[0]["passed"] is False


def test_successful_screening_replay_is_idempotent(tmp_path: Path) -> None:
    store, experiment_id, _ = _prepared(tmp_path)
    orchestrator = DevelopmentScreeningOrchestrator(store)

    first = orchestrator.screen(
        strategy_id="STR-S",
        strategy_version=1,
        experiment_id=experiment_id,
        gate_set=_passing_gates(),
    )
    second = orchestrator.screen(
        strategy_id="STR-S",
        strategy_version=1,
        experiment_id=experiment_id,
        gate_set=_passing_gates(),
    )

    assert first.verdict_id == second.verdict_id
    assert first.promoted is True
    assert second.promoted is False
    assert len(orchestrator.list_verdicts("STR-S", 1)) == 1


def test_tampered_evidence_artifact_is_rejected(tmp_path: Path) -> None:
    store, experiment_id, evidence_store = _prepared(tmp_path)
    evidence = evidence_store.list_for_experiment(experiment_id)
    assert len(evidence) == 1
    artifact = Path(evidence[0]["artifact_path"])
    artifact.write_text(artifact.read_text(encoding="utf-8") + "\n", encoding="utf-8")

    orchestrator = DevelopmentScreeningOrchestrator(store)
    with pytest.raises(RuntimeError, match="SHA-256 mismatch"):
        orchestrator.screen(
            strategy_id="STR-S",
            strategy_version=1,
            experiment_id=experiment_id,
            gate_set=_passing_gates(),
        )

    strategy = store.get_strategy_version("STR-S", 1)
    assert strategy is not None
    assert strategy["lifecycle_state"] is StrategyLifecycle.GENERATED


def test_gate_policy_name_version_is_immutable(tmp_path: Path) -> None:
    store, experiment_id, _ = _prepared(tmp_path)
    orchestrator = DevelopmentScreeningOrchestrator(store)
    original = GateSet(
        name="development-screen",
        version=1,
        rules=(GateRule("return", "total_return", GateOperator.GTE, 100.0),),
    )
    changed = GateSet(
        name="development-screen",
        version=1,
        rules=(GateRule("return", "total_return", GateOperator.GTE, 200.0),),
    )

    first = orchestrator.screen(
        strategy_id="STR-S",
        strategy_version=1,
        experiment_id=experiment_id,
        gate_set=original,
    )
    assert first.passed is False

    with pytest.raises(ValueError, match="gate set name/version is immutable"):
        orchestrator.screen(
            strategy_id="STR-S",
            strategy_version=1,
            experiment_id=experiment_id,
            gate_set=changed,
        )
