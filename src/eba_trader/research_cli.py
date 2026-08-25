from __future__ import annotations

import argparse
import json
import os
import socket
from pathlib import Path

from .research_evidence import ResearchEvidenceStore
from .research_queue import ExperimentQueue
from .research_store import DEFAULT_RESEARCH_DB_PATH, ResearchStore
from .research_worker import ResearchBacktestWorker, WorkerOutcome


def _dataset_resolver(root: Path):
    resolved_root = root.resolve()

    def resolve(dataset_ref: str) -> Path:
        candidate = (resolved_root / dataset_ref).resolve()
        try:
            candidate.relative_to(resolved_root)
        except ValueError as exc:
            raise ValueError("dataset_ref escapes the configured dataset root") from exc
        return candidate

    return resolve


def research_worker_cli() -> None:
    parser = argparse.ArgumentParser(
        description="Run queued EBA Trader research backtests with immutable evidence"
    )
    parser.add_argument("--db", default=str(DEFAULT_RESEARCH_DB_PATH))
    parser.add_argument("--dataset-root", default="data/cache")
    parser.add_argument("--evidence-dir", default="artifacts/research/evidence")
    parser.add_argument(
        "--worker-id",
        default=f"{socket.gethostname()}-{os.getpid()}",
    )
    parser.add_argument("--stage", action="append", dest="stages")
    parser.add_argument("--max-jobs", type=int, default=1)
    parser.add_argument("--lease-seconds", type=int, default=900)
    parser.add_argument("--retry-delay-seconds", type=int, default=30)
    args = parser.parse_args()

    if args.max_jobs < 1:
        raise SystemExit("--max-jobs must be >= 1")

    store = ResearchStore(args.db)
    queue = ExperimentQueue(store)
    evidence_store = ResearchEvidenceStore(store, args.evidence_dir)
    worker = ResearchBacktestWorker(
        store=store,
        queue=queue,
        evidence_store=evidence_store,
        dataset_resolver=_dataset_resolver(Path(args.dataset_root)),
    )

    completed = 0
    for _ in range(args.max_jobs):
        result = worker.run_once(
            worker_id=args.worker_id,
            stages=args.stages,
            lease_seconds=args.lease_seconds,
            retry_delay_seconds=args.retry_delay_seconds,
        )
        print(
            json.dumps(
                {
                    "outcome": result.outcome.value,
                    "experiment_id": result.experiment_id,
                    "evidence_id": result.evidence_id,
                    "error": result.error,
                },
                sort_keys=True,
            )
        )
        if result.outcome is WorkerOutcome.IDLE:
            break
        completed += 1

    print(f"completed_jobs={completed}")
