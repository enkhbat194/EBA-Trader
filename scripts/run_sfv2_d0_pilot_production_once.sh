#!/usr/bin/env bash
set -euo pipefail

REPO_DIR="/opt/Eba-Trader"
DATASET_ROOT="/var/lib/eba-trader/research/datasets"
RESEARCH_DB="/var/lib/eba-trader/research/eba_research.db"
RUNTIME_LOCK="/run/lock/eba-trader-runtime-mutation.lock"
MAX_COMPUTE_MS_PER_STRATUM="${EBA_SFV2_D0_MAX_COMPUTE_MS_PER_STRATUM:-30000}"

if [[ $EUID -ne 0 ]]; then
  echo "Run as root so production research state remains under the canonical ownership." >&2
  exit 1
fi

case "$MAX_COMPUTE_MS_PER_STRATUM" in
  ''|*[!0-9]*)
    echo "EBA_SFV2_D0_MAX_COMPUTE_MS_PER_STRATUM must be a positive integer." >&2
    exit 2
    ;;
esac
if [[ "$MAX_COMPUTE_MS_PER_STRATUM" -le 0 ]]; then
  echo "EBA_SFV2_D0_MAX_COMPUTE_MS_PER_STRATUM must be positive." >&2
  exit 2
fi

cd "$REPO_DIR"
if [[ ! -x .venv/bin/python ]]; then
  echo "Production virtualenv is missing: $REPO_DIR/.venv/bin/python" >&2
  exit 3
fi

# Hold the same lock used by the five-minute auto-updater for the entire campaign invocation.
# A busy updater/campaign is a safe retry condition; never run against a checkout being mutated.
exec 9>"$RUNTIME_LOCK"
if ! flock -n 9; then
  echo "D0 pilot not started: production checkout lock is busy; retry later." >&2
  exit 75
fi

SOURCE_SHA="$(git rev-parse HEAD)"
if [[ -n "$(git status --porcelain --untracked-files=no)" ]]; then
  echo "D0 pilot not started: tracked production checkout is dirty." >&2
  exit 4
fi

echo "Starting DISCOVERY_ONLY D0 pilot on exact production build $SOURCE_SHA"
exec .venv/bin/python scripts/run_sfv2_d0_pilot_once.py \
  --dataset-root "$DATASET_ROOT" \
  --research-db "$RESEARCH_DB" \
  --repo-root "$REPO_DIR" \
  --expected-source-code-sha "$SOURCE_SHA" \
  --max-compute-ms-per-stratum "$MAX_COMPUTE_MS_PER_STRATUM"
