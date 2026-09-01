#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json

from eba_trader.strategy_factory_v2_campaign import run_existing_production_d0_pilot


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run/resume Strategy Factory v2 pilot on existing inspected D0 only."
    )
    parser.add_argument("--dataset-root", required=True)
    parser.add_argument("--research-db", required=True)
    parser.add_argument("--repo-root", default=None)
    parser.add_argument(
        "--expected-source-code-sha",
        default=None,
        help="Optional guard; actual clean checkout SHA is always authoritative.",
    )
    parser.add_argument("--max-compute-ms-per-stratum", type=int, required=True)
    args = parser.parse_args()

    result = run_existing_production_d0_pilot(
        dataset_root=args.dataset_root,
        research_db_path=args.research_db,
        repo_root=args.repo_root,
        expected_source_code_sha=args.expected_source_code_sha,
        max_compute_ms_per_stratum=args.max_compute_ms_per_stratum,
    )
    payload = {
        "campaignId": result.campaign_id,
        "authority": result.authority,
        "sourceCodeSha": result.source_code_sha,
        "d0DeclarationSha256": result.d0_declaration_sha256,
        "d0DatasetSha256": result.d0_dataset_sha256,
        "candidateCount": result.candidate_count,
        "stratumCount": result.stratum_count,
        "newlyEvaluatedTrialCount": result.newly_evaluated_trial_count,
        "reusedTerminalTrialCount": result.reused_terminal_trial_count,
        "completeCandidateCount": result.report.complete_candidate_count,
        "rejectedCandidateCount": result.report.rejected_candidate_count,
        "behavioralRepresentativeCount": len(result.report.representative_candidate_ids),
        "stoppedForComputeBudget": result.stopped_for_compute_budget,
        "d1Opened": result.d1_opened,
        "frozenOosOpened": result.frozen_oos_opened,
        "liveExecutionAllowed": result.live_execution_allowed,
    }
    print(json.dumps(payload, sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
