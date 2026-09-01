#!/usr/bin/env bash
set -euo pipefail

REPO_DIR="/opt/Eba-Trader"
DATASET_ROOT="/var/lib/eba-trader/research/datasets"
RESEARCH_DB="/var/lib/eba-trader/research/eba_research.db"
STATUS_PATH="/var/lib/eba-trader/research/sfv2-d0-pilot-status.json"
AUTHORIZATION_PATH="$REPO_DIR/config/sfv2_d0_production_authorization_v1.json"
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
  echo "SFv2 D0 authorization is absent; nothing to run."
  exit 0
fi
if [[ -n "$(git status --porcelain --untracked-files=no)" ]]; then
  echo "SFv2 D0 campaign not started: tracked production checkout is dirty." >&2
  exit 4
fi

# A completed single-use request is a permanent no-op on subsequent maintenance cycles.
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
    if (
        payload.get("schema") == "sfv2_d0_production_status_v1"
        and payload.get("requestId") == "sfv2-d0-prod-20260901-v1"
    ):
        print(str(payload.get("phase") or "UNKNOWN"))
    else:
        print("UNKNOWN")
PY
  } 2>/dev/null)"
  if [[ "$phase" == "COMPLETE" ]]; then
    echo "SFv2 D0 authorized campaign is already complete."
    exit 0
  fi
fi

# This is local-only. There is no HTTP/PWA/GitHub workflow mutation endpoint. The shared lock
# prevents the five-minute updater from changing the exact checkout while discovery code executes.
exec 9>"$RUNTIME_LOCK"
if ! flock -n 9; then
  echo "SFv2 D0 authorized campaign deferred: production checkout lock is busy."
  exit 75
fi

SOURCE_SHA="$(git rev-parse HEAD)"
echo "Starting/resuming authorized DISCOVERY_ONLY SFv2 D0 campaign on $SOURCE_SHA"
exec .venv/bin/python scripts/run_sfv2_d0_authorized_until_frozen.py \
  --authorization "$AUTHORIZATION_PATH" \
  --dataset-root "$DATASET_ROOT" \
  --research-db "$RESEARCH_DB" \
  --repo-root "$REPO_DIR" \
  --status-path "$STATUS_PATH"
