#!/usr/bin/env bash
set -euo pipefail

REPO_DIR="/opt/Eba-Trader"
STATE_DIR="/var/lib/eba-trader/deploy-state"
UPDATE_SERVICE="eba-auto-update.service"
UPDATE_TIMER="eba-auto-update.timer"
REMOTE_SCRIPT_URL="https://raw.githubusercontent.com/enkhbat194/EBA-Trader/main/scripts/update_linode_runtime.sh"

if [[ $EUID -ne 0 ]]; then
  echo "Run as root." >&2
  exit 1
fi

mkdir -p "$STATE_DIR"
chmod 750 "$STATE_DIR"
exec > >(tee -a "$STATE_DIR/repair.log") 2>&1

echo "=== EBA Trader auto-update repair $(date -u +%FT%TZ) ==="
cd "$REPO_DIR"

echo "Current HEAD: $(git rev-parse HEAD)"
echo "Origin: $(git remote get-url origin)"

DIRTY="$(git status --porcelain)"
if [[ -n "$DIRTY" ]]; then
  printf '%s\n' "$DIRTY" > "$STATE_DIR/dirty-checkout.txt"
  echo "Refusing destructive repair because the runtime checkout has local changes:"
  printf '%s\n' "$DIRTY"
  echo "Saved report: $STATE_DIR/dirty-checkout.txt"
  exit 2
fi
rm -f "$STATE_DIR/dirty-checkout.txt"

systemctl daemon-reload || true
systemctl enable "$UPDATE_TIMER" >/dev/null 2>&1 || true
systemctl restart "$UPDATE_TIMER" || true
systemctl reset-failed "$UPDATE_SERVICE" || true

TMP_SCRIPT="$(mktemp /tmp/eba-update-repair.XXXXXX)"
trap 'rm -f "$TMP_SCRIPT"' EXIT
curl --fail --silent --show-error --location --max-time 30 "$REMOTE_SCRIPT_URL" -o "$TMP_SCRIPT"
chmod 700 "$TMP_SCRIPT"

echo "Running the latest main deployment script..."
bash "$TMP_SCRIPT"

echo "Restarting and validating the auto-update timer..."
systemctl daemon-reload
systemctl enable --now "$UPDATE_TIMER"
systemctl reset-failed "$UPDATE_SERVICE" || true
systemctl --no-pager --full status "$UPDATE_TIMER" || true
systemctl list-timers --all "$UPDATE_TIMER" --no-pager || true

echo "Server app info:"
curl --fail --silent --show-error --max-time 10 http://127.0.0.1:8000/api/app-info || true
echo
echo "=== repair complete ==="
