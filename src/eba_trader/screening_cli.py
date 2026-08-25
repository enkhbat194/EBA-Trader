from __future__ import annotations

import argparse
import json
from pathlib import Path

from .research_gates import GateSet
from .research_screening import DevelopmentScreeningOrchestrator
from .research_store import DEFAULT_RESEARCH_DB_PATH, ResearchStore


def development_screening_cli() -> None:
    parser = argparse.ArgumentParser(
        description="Evaluate persisted development evidence against a versioned gate policy"
    )
    parser.add_argument("--db", default=str(DEFAULT_RESEARCH_DB_PATH))
    parser.add_argument("--strategy-id", required=True)
    parser.add_argument("--strategy-version", required=True, type=int)
    parser.add_argument("--experiment-id", required=True)
    parser.add_argument("--gate-set", required=True, help="Path to a JSON GateSet definition")
    args = parser.parse_args()

    payload = json.loads(Path(args.gate_set).read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise SystemExit("gate-set JSON must be an object")
    gate_set = GateSet.from_mapping(payload)

    store = ResearchStore(args.db)
    orchestrator = DevelopmentScreeningOrchestrator(store)
    verdict = orchestrator.screen(
        strategy_id=args.strategy_id,
        strategy_version=args.strategy_version,
        experiment_id=args.experiment_id,
        gate_set=gate_set,
    )
    print(
        json.dumps(
            {
                "verdict_id": verdict.verdict_id,
                "gate_set_id": verdict.gate_set_id,
                "experiment_id": verdict.experiment_id,
                "evidence_id": verdict.evidence_id,
                "passed": verdict.passed,
                "promoted": verdict.promoted,
                "evaluation": verdict.evaluation.as_dict(),
            },
            sort_keys=True,
        )
    )
