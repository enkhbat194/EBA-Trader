#!/usr/bin/env bash
set -euo pipefail

REPO_DIR="/opt/Eba-Trader"
DATASET_ROOT="/var/lib/eba-trader/research/datasets"
STATUS_PATH="/var/lib/eba-trader/research/sfv2-next-d0-materialization-status.json"
AUTHORIZATION_PATH="$REPO_DIR/config/sfv2_next_d0_materialization_authorization_v1.json"
PLAN_PATH="$REPO_DIR/config/sfv2_next_d0_dataset_plan_v1.json"
INVENTORY_PATH="$REPO_DIR/config/sfv2_historical_window_inventory_v1.json"
RUNTIME_LOCK="/run/lock/eba-trader-runtime-mutation.lock"

if [[ $EUID -ne 0 ]]; then
  echo "Run as root so production research state remains under canonical ownership." >&2
  exit 1
fi

cd "$REPO_DIR"
if [[ ! -x .venv/bin/python ]]; then
  echo "Production virtualenv is missing: $REPO_DIR/.venv/bin/python" >&2
  exit 3
fi
if [[ ! -f "$AUTHORIZATION_PATH" ]]; then
  echo "Next D0 materialization authorization is absent; nothing to run."
  exit 0
fi
if [[ -n "$(git status --porcelain --untracked-files=no)" ]]; then
  echo "Next D0 materialization not started: tracked production checkout is dirty." >&2
  exit 4
fi

if [[ -f "$STATUS_PATH" ]]; then
  phase="$({ .venv/bin/python - "$STATUS_PATH" <<'PY'
import json
import sys
from pathlib import Path

path = Path(sys.argv[1])
try:
    payload = json.loads(path.read_text(encoding="utf-8"))
except (OSError, json.JSONDecodeError):
    print("UNKNOWN")
else:
    valid = (
        payload.get("schema") == "sfv2_next_d0_materialization_status_v1"
        and payload.get("requestId") == "sfv2-next-d0-materialize-20260904-v1"
    )
    print(str(payload.get("phase") or "UNKNOWN") if valid else "UNKNOWN")
PY
  } 2>/dev/null)"
  if [[ "$phase" == "COMPLETE" ]]; then
    echo "Next D0 production materialization is already complete."
    exit 0
  fi
fi

exec 9>"$RUNTIME_LOCK"
if ! flock -n 9; then
  echo "Next D0 materialization deferred: production checkout lock is busy."
  exit 75
fi

# Pin the feature-builder contract rather than the whole git commit. This lets unrelated UI/docs
# changes deploy between windows while still failing closed if any data-plan, boundary, acquisition,
# footprint or materialization logic changes before the ten-window receipt is frozen.
SOURCE_SHA="$(.venv/bin/python - <<'PY'
from pathlib import Path

from eba_trader.research_evidence import canonical_json, sha256_file, sha256_text

paths = (
    "config/sfv2_next_d0_dataset_plan_v1.json",
    "config/sfv2_historical_window_inventory_v1.json",
    "src/eba_trader/strategy_factory_v2_next_dataset_plan.py",
    "src/eba_trader/strategy_factory_v2_next_dataset_workflow.py",
    "src/eba_trader/strategy_factory_v2_next_materialization.py",
    "src/eba_trader/strategy_factory_v2_window_inventory.py",
    "src/eba_trader/candle_acquisition.py",
    "src/eba_trader/orderflow_archive.py",
    "src/eba_trader/orderflow_acquisition.py",
    "src/eba_trader/orderflow_dataset.py",
    "src/eba_trader/orderflow_feature_dataset.py",
    "src/eba_trader/footprint.py",
    "src/eba_trader/history.py",
    "src/eba_trader/holdout_guard.py",
    "src/eba_trader/research_evidence.py",
)
identity = [[path, sha256_file(Path(path))] for path in paths]
print(sha256_text(canonical_json(identity)))
PY
)"
echo "Materializing one frozen next-D0 window on builder contract $SOURCE_SHA"
exec .venv/bin/python scripts/run_sfv2_next_d0_materialization.py \
  --authorization "$AUTHORIZATION_PATH" \
  --plan "$PLAN_PATH" \
  --inventory "$INVENTORY_PATH" \
  --dataset-root "$DATASET_ROOT" \
  --status-path "$STATUS_PATH" \
  --source-code-sha "$SOURCE_SHA"
