from __future__ import annotations

import argparse
import json

from eba_trader.strategy_factory_v2_next_materialization import (
    run_next_d0_materialization_cycle,
)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Materialize one authorized frozen Strategy Factory v2 next-D0 window"
    )
    parser.add_argument("--authorization", required=True)
    parser.add_argument("--plan", required=True)
    parser.add_argument("--inventory", required=True)
    parser.add_argument("--dataset-root", required=True)
    parser.add_argument("--status-path", required=True)
    parser.add_argument("--source-code-sha", required=True)
    args = parser.parse_args()

    payload = run_next_d0_materialization_cycle(
        authorization_path=args.authorization,
        plan_path=args.plan,
        inventory_path=args.inventory,
        dataset_root=args.dataset_root,
        status_path=args.status_path,
        source_code_sha=args.source_code_sha,
    )
    print(
        json.dumps(
            {
                "phase": payload["phase"],
                "completedWindowCount": payload["completedWindowCount"],
                "expectedWindowCount": payload["expectedWindowCount"],
                "nextWindowName": payload["nextWindowName"],
                "datasetBundleSha256": payload["datasetBundleSha256"],
                "performanceEvaluationAllowed": False,
                "d1Opened": False,
                "frozenOosOpened": False,
                "sf4DataAccessAllowed": False,
                "liveExecutionAllowed": False,
                "realExecutionAllowed": False,
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
