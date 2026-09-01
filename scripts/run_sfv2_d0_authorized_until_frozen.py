#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
import traceback
from datetime import UTC, datetime
from pathlib import Path

from eba_trader.strategy_factory_v2_authorized import (
    STATUS_SCHEMA,
    load_sfv2_d0_authorization,
    run_authorized_d0_cycle,
    write_sfv2_d0_status,
)


def _failure_payload(*, request_id: str, message: str) -> dict[str, object]:
    return {
        "schema": STATUS_SCHEMA,
        "phase": "FAILED",
        "requestId": request_id,
        "authority": "DISCOVERY_ONLY",
        "error": message[:2000],
        "freshConfirmationEvidence": False,
        "verificationAuthority": False,
        "d1Opened": False,
        "frozenOosOpened": False,
        "demoPromotionAllowed": False,
        "liveExecutionAllowed": False,
        "realExecutionAllowed": False,
        "updatedAt": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Run/resume the explicitly authorized Strategy Factory v2 D0 campaign until the "
            "immutable D0 survivor outcome is frozen or the bounded per-invocation cycle budget ends."
        )
    )
    parser.add_argument("--authorization", required=True)
    parser.add_argument("--dataset-root", required=True)
    parser.add_argument("--research-db", required=True)
    parser.add_argument("--repo-root", required=True)
    parser.add_argument("--status-path", required=True)
    args = parser.parse_args()

    authorization = load_sfv2_d0_authorization(args.authorization)
    try:
        last_result = None
        for _ in range(authorization.max_cycles_per_invocation):
            last_result = run_authorized_d0_cycle(
                authorization_path=args.authorization,
                dataset_root=args.dataset_root,
                research_db_path=args.research_db,
                repo_root=args.repo_root,
                status_path=args.status_path,
            )
            print(
                json.dumps(
                    dict(last_result.status_payload),
                    sort_keys=True,
                    separators=(",", ":"),
                )
            )
            if last_result.phase == "COMPLETE":
                return 0
            if last_result.campaign_run.newly_evaluated_trial_count == 0:
                break
        if last_result is None:
            raise RuntimeError("authorized D0 runner executed no cycle")
        # Incomplete is a normal bounded-research state. The existing systemd timer will retry.
        return 0
    except Exception as exc:
        payload = _failure_payload(request_id=authorization.request_id, message=str(exc))
        write_sfv2_d0_status(payload, path=args.status_path)
        traceback.print_exc(file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
