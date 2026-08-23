#!/usr/bin/env bash
set -euo pipefail

REPO_DIR="/opt/Eba-Trader"
STATE_DIR="/var/lib/eba-trader"
DEPLOY_STATE="$STATE_DIR/deploy-state"
DATA_SERVICE="eba-binance-data.service"
API_SERVICE="eba-runtime-api.service"
WEB_SERVICE="eba-web.service"
AUTO_MODE=0

if [[ "${1:-}" == "--auto" ]]; then
  AUTO_MODE=1
fi

if [[ $EUID -ne 0 ]]; then
  echo "Run as root." >&2
  exit 1
fi

cd "$REPO_DIR"
mkdir -p "$STATE_DIR" "$DEPLOY_STATE"
chmod 750 "$STATE_DIR" "$DEPLOY_STATE"

# Never deploy over local edits: a dirty runtime checkout is unsafe to auto-reset.
if [[ -n "$(git status --porcelain)" ]]; then
  echo "EBA deploy skipped: runtime checkout has local changes." >&2
  exit 2
fi

git fetch --quiet origin main
CURRENT_SHA="$(git rev-parse HEAD)"
TARGET_SHA="$(git rev-parse origin/main)"

if [[ "$CURRENT_SHA" == "$TARGET_SHA" ]]; then
  if [[ $AUTO_MODE -eq 0 ]]; then
    echo "EBA Trader already up to date: $CURRENT_SHA"
  fi
  exit 0
fi

PREVIOUS_SHA="$CURRENT_SHA"
printf '%s\n' "$PREVIOUS_SHA" > "$DEPLOY_STATE/previous_sha"
printf '%s\n' "$TARGET_SHA" > "$DEPLOY_STATE/target_sha"
date -u +%FT%TZ > "$DEPLOY_STATE/started_at"

rollback() {
  local code=$?
  trap - ERR
  echo "Deployment failed (exit $code). Rolling back to $PREVIOUS_SHA" >&2
  cd "$REPO_DIR"
  git reset --hard "$PREVIOUS_SHA"
  . .venv/bin/activate || true
  python -m pip install -e '.[trading]' || true
  install -m 0644 deploy/systemd/eba-binance-data.service "/etc/systemd/system/$DATA_SERVICE" || true
  install -m 0644 deploy/systemd/eba-runtime-api.service "/etc/systemd/system/$API_SERVICE" || true
  install -m 0644 deploy/systemd/eba-web.service "/etc/systemd/system/$WEB_SERVICE" || true
  install -m 0644 deploy/systemd/eba-auto-update.service /etc/systemd/system/eba-auto-update.service || true
  install -m 0644 deploy/systemd/eba-auto-update.timer /etc/systemd/system/eba-auto-update.timer || true
  systemctl daemon-reload || true
  systemctl restart "$DATA_SERVICE" "$API_SERVICE" "$WEB_SERVICE" || true
  printf '%s\n' "$PREVIOUS_SHA" > "$DEPLOY_STATE/rolled_back_to"
  date -u +%FT%TZ > "$DEPLOY_STATE/failed_at"
  exit "$code"
}
trap rollback ERR

git checkout --quiet main
git reset --hard "$TARGET_SHA"

if [[ ! -x .venv/bin/python ]]; then
  python3 -m venv .venv
fi

. .venv/bin/activate
python -m pip install --upgrade --quiet pip
python -m pip install --quiet -e '.[trading]'

install -m 0644 deploy/systemd/eba-binance-data.service "/etc/systemd/system/$DATA_SERVICE"
install -m 0644 deploy/systemd/eba-runtime-api.service "/etc/systemd/system/$API_SERVICE"
install -m 0644 deploy/systemd/eba-web.service "/etc/systemd/system/$WEB_SERVICE"
install -m 0644 deploy/systemd/eba-auto-update.service /etc/systemd/system/eba-auto-update.service
install -m 0644 deploy/systemd/eba-auto-update.timer /etc/systemd/system/eba-auto-update.timer
systemctl daemon-reload
systemctl enable "$DATA_SERVICE" "$API_SERVICE" "$WEB_SERVICE" eba-auto-update.timer >/dev/null
systemctl restart "$DATA_SERVICE" "$API_SERVICE" "$WEB_SERVICE"

# Give the processes a short warm-up window, then require both APIs to answer.
sleep 3
systemctl is-active --quiet "$DATA_SERVICE"
systemctl is-active --quiet "$API_SERVICE"
systemctl is-active --quiet "$WEB_SERVICE"
curl --fail --silent --max-time 5 http://127.0.0.1:8765/health >/dev/null
curl --fail --silent --max-time 5 http://127.0.0.1:8000/api/health >/dev/null

trap - ERR
printf '%s\n' "$TARGET_SHA" > "$DEPLOY_STATE/current_sha"
date -u +%FT%TZ > "$DEPLOY_STATE/succeeded_at"
rm -f "$DEPLOY_STATE/rolled_back_to" "$DEPLOY_STATE/failed_at"

echo "EBA Trader deployed successfully: $PREVIOUS_SHA -> $TARGET_SHA"
