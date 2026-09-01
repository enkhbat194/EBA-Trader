#!/usr/bin/env bash
set -euo pipefail

REPO_DIR="/opt/Eba-Trader"
STATE_DIR="/var/lib/eba-trader/deploy-state"
UPDATE_SCRIPT="$REPO_DIR/scripts/update_linode_runtime.sh"
RUNTIME_LOCK="/run/lock/eba-trader-runtime-mutation.lock"

mkdir -p "$STATE_DIR"
chmod 750 "$STATE_DIR"
date -u +%FT%TZ > "$STATE_DIR/last_attempt_at"
rm -f "$STATE_DIR/last_error"

# Discovery campaigns execute code directly from the production checkout. Never let the
# five-minute automatic updater reset that checkout while a campaign invocation is active.
exec 9>"$RUNTIME_LOCK"
if ! flock -n 9; then
  echo "EBA auto-update skipped: production research holds $RUNTIME_LOCK"
  date -u +%FT%TZ > "$STATE_DIR/skipped_for_runtime_lock_at"
  exit 0
fi
rm -f "$STATE_DIR/skipped_for_runtime_lock_at"

TMP_LOG="$(mktemp /tmp/eba-auto-update.XXXXXX)"
trap 'rm -f "$TMP_LOG"' EXIT

set +e
bash "$UPDATE_SCRIPT" --auto >"$TMP_LOG" 2>&1
CODE=$?
set -e

cat "$TMP_LOG"
cp "$TMP_LOG" "$STATE_DIR/last_output.log"
chmod 640 "$STATE_DIR/last_output.log"

if [[ $CODE -ne 0 ]]; then
  date -u +%FT%TZ > "$STATE_DIR/failed_at"
  tail -n 20 "$TMP_LOG" > "$STATE_DIR/last_error"
  chmod 640 "$STATE_DIR/last_error"
  exit "$CODE"
fi

rm -f "$STATE_DIR/failed_at" "$STATE_DIR/last_error"
exit 0
