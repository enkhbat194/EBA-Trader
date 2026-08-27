#!/usr/bin/env bash
set -euo pipefail

REPO_DIR="/opt/Eba-Trader"
ENV_DIR="/etc/eba-trader"
STATE_DIR="/var/lib/eba-trader"
DEPLOY_STATE="$STATE_DIR/deploy-state"
PROOF_DIR="$STATE_DIR/proofs"
PROOF_FILE="$PROOF_DIR/latest.json"
RESEARCH_DIR="$STATE_DIR/research"
RESEARCH_DATASET_DIR="$RESEARCH_DIR/datasets"
RESEARCH_EVIDENCE_DIR="$RESEARCH_DIR/evidence"
CREDENTIAL_DIR="$STATE_DIR/credentials"
CREDENTIAL_KEY="$ENV_DIR/demo-credential.key"
JOURNALD_DROPIN_DIR="/etc/systemd/journald.conf.d"
JOURNALD_DROPIN="$JOURNALD_DROPIN_DIR/eba-trader.conf"
DATA_SERVICE="eba-binance-data.service"
API_SERVICE="eba-runtime-api.service"
WEB_SERVICE="eba-web.service"
RESEARCH_SERVICE="eba-research-worker.service"
RESEARCH_TIMER="eba-research-worker.timer"
UPDATE_SERVICE="eba-auto-update.service"
UPDATE_TIMER="eba-auto-update.timer"
AUTO_MODE=0

if [[ "${1:-}" == "--auto" ]]; then
  AUTO_MODE=1
fi

if [[ $EUID -ne 0 ]]; then
  echo "Run as root." >&2
  exit 1
fi

cd "$REPO_DIR"
mkdir -p \
  "$ENV_DIR" \
  "$STATE_DIR" \
  "$DEPLOY_STATE" \
  "$PROOF_DIR" \
  "$CREDENTIAL_DIR" \
  "$RESEARCH_DATASET_DIR" \
  "$RESEARCH_EVIDENCE_DIR" \
  "$JOURNALD_DROPIN_DIR"
chmod 700 "$ENV_DIR" "$CREDENTIAL_DIR"
chmod 750 \
  "$STATE_DIR" \
  "$DEPLOY_STATE" \
  "$PROOF_DIR" \
  "$RESEARCH_DIR" \
  "$RESEARCH_DATASET_DIR" \
  "$RESEARCH_EVIDENCE_DIR"

collect_proof() {
  local expected_build="$1"
  if [[ -x .venv/bin/python && -f scripts/collect_linode_proof.py ]]; then
    .venv/bin/python scripts/collect_linode_proof.py \
      --output "$PROOF_FILE" \
      --expected-build "$expected_build" >/dev/null 2>&1 || true
  fi
}

# Never deploy over local edits: a dirty runtime checkout is unsafe to auto-reset.
if [[ -n "$(git status --porcelain)" ]]; then
  echo "EBA deploy skipped: runtime checkout has local changes." >&2
  exit 2
fi

git fetch --quiet origin main
CURRENT_SHA="$(git rev-parse HEAD)"
TARGET_SHA="$(git rev-parse origin/main)"

if [[ "$CURRENT_SHA" == "$TARGET_SHA" ]]; then
  # In automatic mode, use the 5-minute timer as a lightweight HTTPS self-heal loop too.
  if [[ $AUTO_MODE -eq 1 && -f scripts/bootstrap_linode_public_https.sh ]]; then
    bash scripts/bootstrap_linode_public_https.sh >/dev/null 2>&1 || true
  elif [[ $AUTO_MODE -eq 0 ]]; then
    echo "EBA Trader already up to date: $CURRENT_SHA"
  fi
  # Refresh sanitized proof even when no deployment is needed. This lets Demo reconnect,
  # Chart/Positions/Research smoke and host-contract state converge without operator action.
  collect_proof "$CURRENT_SHA"
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

# Provision the encryption key once. Never rotate it implicitly during deploys because
# existing encrypted Demo credentials must remain decryptable across updates/restarts.
if [[ ! -f "$CREDENTIAL_KEY" ]]; then
  CREDENTIAL_KEY="$CREDENTIAL_KEY" python - <<'PY'
import os
from pathlib import Path

from cryptography.fernet import Fernet

path = Path(os.environ["CREDENTIAL_KEY"])
fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
with os.fdopen(fd, "wb") as handle:
    handle.write(Fernet.generate_key() + b"\n")
PY
fi
chmod 600 "$CREDENTIAL_KEY"

# Ensure upgrades of an existing Linode env file gain the canonical persistent research
# paths without overwriting any explicit operator choice already present.
bash scripts/ensure_linode_research_env.sh

# Keep research state outside the Git checkout so deployments cannot delete datasets,
# queue metadata or immutable evidence.
mkdir -p "$RESEARCH_DATASET_DIR" "$RESEARCH_EVIDENCE_DIR"
chmod 750 "$RESEARCH_DIR" "$RESEARCH_DATASET_DIR" "$RESEARCH_EVIDENCE_DIR"

# The journal cap is a host-safety invariant, not application state. It intentionally
# survives application rollback so a bad release cannot re-open the disk-fill failure.
install -m 0644 deploy/journald/eba-trader.conf "$JOURNALD_DROPIN"
systemctl restart systemd-journald

install -m 0644 deploy/systemd/eba-binance-data.service "/etc/systemd/system/$DATA_SERVICE"
install -m 0644 deploy/systemd/eba-runtime-api.service "/etc/systemd/system/$API_SERVICE"
install -m 0644 deploy/systemd/eba-web.service "/etc/systemd/system/$WEB_SERVICE"
install -m 0644 deploy/systemd/eba-research-worker.service "/etc/systemd/system/$RESEARCH_SERVICE"
install -m 0644 deploy/systemd/eba-research-worker.timer "/etc/systemd/system/$RESEARCH_TIMER"
install -m 0644 deploy/systemd/eba-auto-update.service "/etc/systemd/system/$UPDATE_SERVICE"
install -m 0644 deploy/systemd/eba-auto-update.timer "/etc/systemd/system/$UPDATE_TIMER"
systemctl daemon-reload
systemctl reset-failed "$RESEARCH_SERVICE" || true
systemctl enable "$DATA_SERVICE" "$API_SERVICE" "$WEB_SERVICE" >/dev/null
systemctl enable --now "$UPDATE_TIMER" "$RESEARCH_TIMER" >/dev/null
systemctl restart "$DATA_SERVICE" "$API_SERVICE" "$WEB_SERVICE"
systemctl restart "$RESEARCH_TIMER"

# Give the processes a short warm-up window, then require both APIs to answer.
sleep 3
systemctl is-active --quiet "$DATA_SERVICE"
systemctl is-active --quiet "$API_SERVICE"
systemctl is-active --quiet "$WEB_SERVICE"
systemctl is-active --quiet "$RESEARCH_TIMER"
curl --fail --silent --max-time 5 http://127.0.0.1:8765/health >/dev/null
curl --fail --silent --max-time 5 http://127.0.0.1:8000/api/health >/dev/null

# HTTPS is not part of the rollback boundary. A temporary DNS/CA outage must not roll
# back an otherwise healthy runtime deployment; the timer retries bootstrap later.
if [[ -f scripts/bootstrap_linode_public_https.sh ]]; then
  bash scripts/bootstrap_linode_public_https.sh || \
    echo "Public HTTPS bootstrap deferred; runtime deployment remains healthy." >&2
fi

# Collect a sanitized post-restart proof. External Binance/Demo availability does not
# participate in rollback; local host/runtime failures are already gated above.
collect_proof "$TARGET_SHA"

trap - ERR
printf '%s\n' "$TARGET_SHA" > "$DEPLOY_STATE/current_sha"
date -u +%FT%TZ > "$DEPLOY_STATE/succeeded_at"
rm -f "$DEPLOY_STATE/rolled_back_to" "$DEPLOY_STATE/failed_at"

echo "EBA Trader deployed successfully: $PREVIOUS_SHA -> $TARGET_SHA"
