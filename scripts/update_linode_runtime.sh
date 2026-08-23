#!/usr/bin/env bash
set -euo pipefail

REPO_DIR="/opt/Eba-Trader"
SERVICE_NAME="eba-binance-data.service"

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

install -m 0644 deploy/systemd/eba-binance-data.service "/etc/systemd/system/$SERVICE_NAME"
systemctl daemon-reload
systemctl restart "$SERVICE_NAME"

sleep 2
systemctl --no-pager --full status "$SERVICE_NAME" || true
