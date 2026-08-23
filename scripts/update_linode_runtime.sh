#!/usr/bin/env bash
set -euo pipefail

REPO_DIR="/opt/Eba-Trader"
DATA_SERVICE="eba-binance-data.service"
API_SERVICE="eba-runtime-api.service"
WEB_SERVICE="eba-web.service"

if [[ $EUID -ne 0 ]]; then
  echo "Run as root." >&2
  exit 1
fi

cd "$REPO_DIR"
git fetch origin main
git checkout main
git pull --ff-only origin main

if [[ ! -x .venv/bin/python ]]; then
  python3 -m venv .venv
fi

. .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e '.[trading]'

mkdir -p /var/lib/eba-trader
chmod 750 /var/lib/eba-trader

install -m 0644 deploy/systemd/eba-binance-data.service "/etc/systemd/system/$DATA_SERVICE"
install -m 0644 deploy/systemd/eba-runtime-api.service "/etc/systemd/system/$API_SERVICE"
install -m 0644 deploy/systemd/eba-web.service "/etc/systemd/system/$WEB_SERVICE"
systemctl daemon-reload
systemctl enable "$DATA_SERVICE" "$API_SERVICE" "$WEB_SERVICE"
systemctl restart "$DATA_SERVICE" "$API_SERVICE" "$WEB_SERVICE"

sleep 2
systemctl --no-pager --full status "$DATA_SERVICE" || true
systemctl --no-pager --full status "$API_SERVICE" || true
systemctl --no-pager --full status "$WEB_SERVICE" || true

curl --fail --silent http://127.0.0.1:8765/health && echo
curl --fail --silent http://127.0.0.1:8000/api/health && echo
