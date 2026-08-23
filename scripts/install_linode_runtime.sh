#!/usr/bin/env bash
set -euo pipefail

REPO_DIR="/opt/Eba-Trader"
ENV_DIR="/etc/eba-trader"
STATE_DIR="/var/lib/eba-trader"
SERVICE_NAME="eba-binance-data.service"

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

if [[ ! -f "$ENV_DIR/eba-trader.env" ]]; then
  cat > "$ENV_DIR/eba-trader.env" <<'EOF'
# Public market data requires no API credentials.
EBA_BINANCE_DATA_ENV=live_public

# For Binance Demo data instead, set EBA_BINANCE_DATA_ENV=demo and add:
# BINANCE_DEMO_API_KEY=...
# BINANCE_DEMO_API_SECRET=...
EOF
  chmod 600 "$ENV_DIR/eba-trader.env"
fi

install -m 0644 deploy/systemd/eba-binance-data.service "/etc/systemd/system/$SERVICE_NAME"
systemctl daemon-reload
systemctl enable "$SERVICE_NAME"
systemctl restart "$SERVICE_NAME"

sleep 2
systemctl --no-pager --full status "$SERVICE_NAME" || true

echo
echo "EBA Trader Linode runtime installed."
echo "Logs: journalctl -u $SERVICE_NAME -f"
