#!/usr/bin/env bash
set -euo pipefail

REPO_DIR="/opt/Eba-Trader"
ENV_DIR="/etc/eba-trader"
STATE_DIR="/var/lib/eba-trader"
DATA_SERVICE="eba-binance-data.service"
API_SERVICE="eba-runtime-api.service"
WEB_SERVICE="eba-web.service"
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

mkdir -p "$ENV_DIR" "$STATE_DIR" "$STATE_DIR/deploy-state"
chmod 700 "$ENV_DIR"
chmod 750 "$STATE_DIR" "$STATE_DIR/deploy-state"

if [[ ! -f "$ENV_DIR/eba-trader.env" ]]; then
  cat > "$ENV_DIR/eba-trader.env" <<'EOF'
# Binance public market data service.
EBA_BINANCE_DATA_ENV=live_public

# Persistent runtime state.
EBA_LEDGER_DB=/var/lib/eba-trader/eba_trader.db
EBA_RUNTIME_API_HOST=127.0.0.1
EBA_RUNTIME_API_PORT=8765

# Linode PWA/web service. Keep this loopback-only; HTTPS proxy is public.
EBA_WEB_HOST=127.0.0.1
EBA_WEB_PORT=8000

# Optional Binance Demo credentials for Fast Momentum paper scanning.
# Enter these once on the server. The browser never receives the secret.
# BINANCE_DEMO_API_KEY=...
# BINANCE_DEMO_API_SECRET=...
EOF
  chmod 600 "$ENV_DIR/eba-trader.env"
fi

install -m 0644 deploy/systemd/eba-binance-data.service "/etc/systemd/system/$DATA_SERVICE"
install -m 0644 deploy/systemd/eba-runtime-api.service "/etc/systemd/system/$API_SERVICE"
install -m 0644 deploy/systemd/eba-web.service "/etc/systemd/system/$WEB_SERVICE"
install -m 0644 deploy/systemd/eba-auto-update.service "/etc/systemd/system/$UPDATE_SERVICE"
install -m 0644 deploy/systemd/eba-auto-update.timer "/etc/systemd/system/$UPDATE_TIMER"
systemctl daemon-reload
systemctl enable "$DATA_SERVICE" "$API_SERVICE" "$WEB_SERVICE" "$UPDATE_TIMER"
systemctl restart "$DATA_SERVICE" "$API_SERVICE" "$WEB_SERVICE"
systemctl restart "$UPDATE_TIMER"

sleep 2
systemctl --no-pager --full status "$DATA_SERVICE" || true
systemctl --no-pager --full status "$API_SERVICE" || true
systemctl --no-pager --full status "$WEB_SERVICE" || true
systemctl --no-pager --full status "$UPDATE_TIMER" || true

echo
echo "EBA Trader Linode runtime installed."
echo "Market-data logs: journalctl -u $DATA_SERVICE -f"
echo "Runtime API logs: journalctl -u $API_SERVICE -f"
echo "PWA/server logs: journalctl -u $WEB_SERVICE -f"
echo "Auto-update logs: journalctl -u $UPDATE_SERVICE"
echo "Runtime health: curl http://127.0.0.1:8765/health"
echo "PWA health: curl http://127.0.0.1:8000/api/health"
echo "GitHub main is checked automatically every 5 minutes."
