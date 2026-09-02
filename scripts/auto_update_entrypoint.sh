#!/usr/bin/env bash
set -euo pipefail

REPO_DIR="/opt/Eba-Trader"
STATE_DIR="/var/lib/eba-trader/deploy-state"
UPDATE_SCRIPT="$REPO_DIR/scripts/update_linode_runtime.sh"
RUNTIME_LOCK="/run/lock/eba-trader-runtime-mutation.lock"
SFV2_SERVICE="eba-sfv2-d0-authorized.service"
SFV2_SERVICE_SOURCE="$REPO_DIR/deploy/systemd/$SFV2_SERVICE"
SFV2_SERVICE_TARGET="/etc/systemd/system/$SFV2_SERVICE"
SFV2_AUTHORIZATION="$REPO_DIR/config/sfv2_d0_production_authorization_v1.json"
SFV2_RUNNER="$REPO_DIR/scripts/run_sfv2_d0_authorized_production.sh"
SFV2_STATUS="/var/lib/eba-trader/research/sfv2-d0-pilot-status.json"

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

# The updater is the production component we already know executes every five minutes. The prior
# SFv2 package depended indirectly on a legacy research-maintenance timer and therefore never
# reached the authorized campaign. Bootstrap one dedicated local-only systemd service from this
# known-good root path. Release the checkout lock BEFORE starting it; the campaign wrapper then
# reacquires the same lock for its full invocation. No HTTP/GitHub/PWA mutation path is added.
#
# The service invokes the runner through /bin/bash, so the tracked shell file only needs to exist;
# requiring an executable bit here would silently skip the campaign in repositories that track
# scripts as regular 100644 files.
#
# Once the immutable single-use request is COMPLETE, avoid spawning even the no-op service.
SFV2_COMPLETE=0
if [[ -f "$SFV2_STATUS" && -x "$REPO_DIR/.venv/bin/python" ]]; then
  SFV2_COMPLETE="$($REPO_DIR/.venv/bin/python - "$SFV2_STATUS" <<'PY'
import json
import sys
from pathlib import Path

path = Path(sys.argv[1])
try:
    payload = json.loads(path.read_text(encoding="utf-8"))
except (OSError, json.JSONDecodeError):
    print(0)
else:
    complete = (
        payload.get("schema") == "sfv2_d0_production_status_v1"
        and payload.get("requestId") == "sfv2-d0-prod-20260901-v1"
        and payload.get("phase") == "COMPLETE"
        and payload.get("selectionFrozen") is True
    )
    print(1 if complete else 0)
PY
)"
fi

if [[ "$SFV2_COMPLETE" != "1" && -f "$SFV2_AUTHORIZATION" && -f "$SFV2_RUNNER" && -f "$SFV2_SERVICE_SOURCE" ]]; then
  install -m 0644 "$SFV2_SERVICE_SOURCE" "$SFV2_SERVICE_TARGET"
  systemctl daemon-reload
  systemctl reset-failed "$SFV2_SERVICE" >/dev/null 2>&1 || true
  flock -u 9
  systemctl start --no-block "$SFV2_SERVICE" || \
    echo "SFv2 dedicated D0 service start deferred; the next auto-update cycle will retry." >&2
fi

exit 0
