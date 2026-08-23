#!/usr/bin/env bash
set -euo pipefail

APP_DIR="/opt/Eba-Trader"
VENV="$APP_DIR/.venv"
ENV_FILE="/etc/eba-trader.env"
SERVICE="/etc/systemd/system/eba-trader.service"
UPDATE_SERVICE="/etc/systemd/system/eba-trader-update.service"
UPDATE_TIMER="/etc/systemd/system/eba-trader-update.timer"

if [ "$(id -u)" -ne 0 ]; then
  echo "Run as root"
  exit 1
fi

apt-get update
apt-get install -y python3 python3-venv python3-pip git nginx curl

cd "$APP_DIR"
python3 -m venv "$VENV"
"$VENV/bin/python" -m pip install -U pip
"$VENV/bin/python" -m pip install -e .

if [ ! -f "$ENV_FILE" ]; then
  cat > "$ENV_FILE" <<'EOF'
EBA_EXECUTION_MODE=paper
EBA_SYMBOL=BTCUSDT
EBA_PRIMARY_VENUE=BINANCE
EBA_BINANCE_DATA_ENV=live_public
PORT=8000
EOF
  chmod 600 "$ENV_FILE"
fi

cat > "$SERVICE" <<'EOF'
[Unit]
Description=EBA Trader
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
WorkingDirectory=/opt/Eba-Trader
Environment=PYTHONPATH=src
EnvironmentFile=-/etc/eba-trader.env
ExecStart=/opt/Eba-Trader/.venv/bin/python -m eba_trader.web_server_v2
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
EOF

cat > /etc/nginx/sites-available/eba-trader <<'EOF'
server {
    listen 80 default_server;
    listen [::]:80 default_server;
    server_name _;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 120s;
    }
}
EOF
rm -f /etc/nginx/sites-enabled/default
ln -sf /etc/nginx/sites-available/eba-trader /etc/nginx/sites-enabled/eba-trader
nginx -t

cat > "$APP_DIR/scripts/linode_update.sh" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
cd /opt/Eba-Trader
OLD="$(git rev-parse HEAD)"
git fetch origin main
git reset --hard origin/main
NEW="$(git rev-parse HEAD)"
if [ "$OLD" != "$NEW" ]; then
  /opt/Eba-Trader/.venv/bin/python -m pip install -e . >/tmp/eba-trader-pip.log 2>&1
  systemctl restart eba-trader
fi
EOF
chmod +x "$APP_DIR/scripts/linode_update.sh"

cat > "$UPDATE_SERVICE" <<'EOF'
[Unit]
Description=Update EBA Trader from GitHub main

[Service]
Type=oneshot
ExecStart=/opt/Eba-Trader/scripts/linode_update.sh
EOF

cat > "$UPDATE_TIMER" <<'EOF'
[Unit]
Description=Check EBA Trader updates every minute

[Timer]
OnBootSec=60
OnUnitActiveSec=60
Unit=eba-trader-update.service

[Install]
WantedBy=timers.target
EOF

systemctl daemon-reload
systemctl enable --now eba-trader
systemctl enable --now nginx
systemctl enable --now eba-trader-update.timer

sleep 2
systemctl --no-pager --full status eba-trader | head -n 20 || true
echo
echo "EBA Trader Linode setup complete."
echo "Local health check:"
curl -I --max-time 5 http://127.0.0.1:8000/ || true
