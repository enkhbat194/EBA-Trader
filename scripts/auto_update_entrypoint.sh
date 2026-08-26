#!/usr/bin/env bash
set -euo pipefail

REPO_DIR="/opt/Eba-Trader"
STATE_DIR="/var/lib/eba-trader/deploy-state"
UPDATE_SCRIPT="$REPO_DIR/scripts/update_linode_runtime.sh"

mkdir -p "$STATE_DIR"
chmod 750 "$STATE_DIR"
date -u +%FT%TZ > "$STATE_DIR/last_attempt_at"
rm -f "$STATE_DIR/last_error"

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
