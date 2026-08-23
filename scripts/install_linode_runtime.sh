#!/usr/bin/env bash
set -euo pipefail

REPO_DIR="/opt/Eba-Trader"
ENV_DIR="/etc/eba-trader"
STATE_DIR="/var/lib/eba-trader"
DATA_SERVICE="eba-binance-data.service"
API_SERVICE="eba-runtime-api.service"

if [[ $EUID -ne 0 ]]; then
  echo "Run as root." >&2
  exit 1
fi

cd "$REPO_DIR"

python3 -m venv .venv
. .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e '.[trading]'

mkdir -p "$ENV_DIR" "$STATE_DIR"
chmod 700 "$ENV_DIR"
chmod 750 "$STATE_DIR"

if [[ ! -f "$ENV_DIR/eba-trader.env" ]]; then
  cat > "$ENV_DIR/eba-trader.env" <<'EOF'
# Public market data requires no API credentials.
EBA_BINANCE_DATA_ENV=live_public

# Persistent runtime state.
EBA_LEDGER_DB=/var/lib/eba-trader/eba_trader.db
EBA_RUNTIME_API_HOST=127.0.0.1
EBA_RUNTIME_API_PORT=8765

# For Binance Demo data instead, set EBA_BINANCE_DATA_ENV=demo and add:
# BINANCE_DEMO_API_KEY=...
# BINANCE_DEMO_API_SECRET=...
EOF
  chmod 600 "$ENV_DIR/eba-trader.env"
fi

install -m 0644 deploy/systemd/eba-binance-data.service "/etc/systemd/system/$DATA_SERVICE"
install -m 0644 deploy/systemd/eba-runtime-api.service "/etc/systemd/system/$API_SERVICE"
systemctl daemon-reload
systemctl enable "$DATA_SERVICE" "$API_SERVICE"
systemctl restart "$DATA_SERVICE" "$API_SERVICE"

sleep 2
systemctl --no-pager --full status "$DATA_SERVICE" || true
systemctl --no-pager --full status "$API_SERVICE" || true

echo
echo "EBA Trader Linode runtime installed."
echo "Market-data logs: journalctl -u $DATA_SERVICE -f"
echo "Runtime API logs: journalctl -u $API_SERVICE -f"
echo "Runtime health: curl http://127.0.0.1:8765/health"
