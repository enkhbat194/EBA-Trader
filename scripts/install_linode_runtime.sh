#!/usr/bin/env bash
set -euo pipefail

REPO_DIR="/opt/Eba-Trader"
ENV_DIR="/etc/eba-trader"
STATE_DIR="/var/lib/eba-trader"
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

if [[ $EUID -ne 0 ]]; then
  echo "Run as root." >&2
  exit 1
fi

cd "$REPO_DIR"

python3 -m venv .venv
. .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e '.[trading]'

mkdir -p \
  "$ENV_DIR" \
  "$STATE_DIR" \
  "$STATE_DIR/deploy-state" \
  "$CREDENTIAL_DIR" \
  "$RESEARCH_DATASET_DIR" \
  "$RESEARCH_EVIDENCE_DIR" \
  "$JOURNALD_DROPIN_DIR"
chmod 700 "$ENV_DIR" "$CREDENTIAL_DIR"
chmod 750 \
  "$STATE_DIR" \
  "$STATE_DIR/deploy-state" \
  "$RESEARCH_DIR" \
  "$RESEARCH_DATASET_DIR" \
  "$RESEARCH_EVIDENCE_DIR"

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

if [[ ! -f "$ENV_DIR/eba-trader.env" ]]; then
  cat > "$ENV_DIR/eba-trader.env" <<'EOF'
# Binance public market data service.
EBA_BINANCE_DATA_ENV=live_public

# Persistent runtime state.
EBA_LEDGER_DB=/var/lib/eba-trader/eba_trader.db
EBA_RUNTIME_API_HOST=127.0.0.1
EBA_RUNTIME_API_PORT=8765

# Persistent M4/M5 research state. Keep this outside the Git checkout.
EBA_RESEARCH_DB=/var/lib/eba-trader/research/eba_research.db
EBA_RESEARCH_DATASET_ROOT=/var/lib/eba-trader/research/datasets
EBA_RESEARCH_EVIDENCE_ROOT=/var/lib/eba-trader/research/evidence

# Linode PWA/web service. Keep this loopback-only; HTTPS proxy is public.
EBA_WEB_HOST=127.0.0.1
EBA_WEB_PORT=8000

# Browser-entered Binance Demo credentials are encrypted at rest using
# /etc/eba-trader/demo-credential.key and stored under /var/lib/eba-trader/credentials.
# Legacy environment credentials remain optional fallback only.
# BINANCE_DEMO_API_KEY=...
# BINANCE_DEMO_API_SECRET=...
EOF
  chmod 600 "$ENV_DIR/eba-trader.env"
fi

install -m 0644 deploy/journald/eba-trader.conf "$JOURNALD_DROPIN"
install -m 0644 deploy/systemd/eba-binance-data.service "/etc/systemd/system/$DATA_SERVICE"
install -m 0644 deploy/systemd/eba-runtime-api.service "/etc/systemd/system/$API_SERVICE"
install -m 0644 deploy/systemd/eba-web.service "/etc/systemd/system/$WEB_SERVICE"
install -m 0644 deploy/systemd/eba-research-worker.service "/etc/systemd/system/$RESEARCH_SERVICE"
install -m 0644 deploy/systemd/eba-research-worker.timer "/etc/systemd/system/$RESEARCH_TIMER"
install -m 0644 deploy/systemd/eba-auto-update.service "/etc/systemd/system/$UPDATE_SERVICE"
install -m 0644 deploy/systemd/eba-auto-update.timer "/etc/systemd/system/$UPDATE_TIMER"
systemctl restart systemd-journald
systemctl daemon-reload
systemctl reset-failed "$UPDATE_SERVICE" "$RESEARCH_SERVICE" || true
systemctl enable "$DATA_SERVICE" "$API_SERVICE" "$WEB_SERVICE" >/dev/null
systemctl enable --now "$UPDATE_TIMER" "$RESEARCH_TIMER" >/dev/null
systemctl restart "$DATA_SERVICE" "$API_SERVICE" "$WEB_SERVICE"
systemctl restart "$UPDATE_TIMER" "$RESEARCH_TIMER"

sleep 2
systemctl --no-pager --full status "$DATA_SERVICE" || true
systemctl --no-pager --full status "$API_SERVICE" || true
systemctl --no-pager --full status "$WEB_SERVICE" || true
systemctl --no-pager --full status "$RESEARCH_TIMER" || true
systemctl --no-pager --full status "$UPDATE_TIMER" || true

# Public PWA bootstrap is intentionally non-fatal: trading/runtime services must stay up
# even if a DNS/TLS provider is temporarily unavailable. The auto-update timer retries it.
if [[ -f scripts/bootstrap_linode_public_https.sh ]]; then
  bash scripts/bootstrap_linode_public_https.sh || \
    echo "Public HTTPS bootstrap deferred; auto-update will retry." >&2
fi

echo
echo "EBA Trader Linode runtime installed."
echo "Market-data logs: journalctl -u $DATA_SERVICE -f"
echo "Runtime API logs: journalctl -u $API_SERVICE -f"
echo "PWA/server logs: journalctl -u $WEB_SERVICE -f"
echo "Research worker logs: journalctl -u $RESEARCH_SERVICE"
echo "Auto-update logs: journalctl -u $UPDATE_SERVICE"
echo "Auto-update state: /var/lib/eba-trader/deploy-state/last_output.log"
echo "Research DB: $RESEARCH_DIR/eba_research.db"
echo "Research datasets: $RESEARCH_DATASET_DIR"
echo "Research evidence: $RESEARCH_EVIDENCE_DIR"
echo "Runtime health: curl http://127.0.0.1:8765/health"
echo "PWA health: curl http://127.0.0.1:8000/api/health"
if [[ -s "$ENV_DIR/public-url" ]]; then
  echo "Public PWA: $(cat "$ENV_DIR/public-url")"
else
  echo "Public PWA: pending automatic HTTPS bootstrap"
fi
echo "GitHub main is checked automatically every 5 minutes."
