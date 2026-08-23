#!/usr/bin/env bash
set -euo pipefail

if [[ $EUID -ne 0 ]]; then
  echo "Run as root." >&2
  exit 1
fi

PUBLIC_HOST="${1:-}"
EMAIL="${2:-}"
ENV_DIR="/etc/eba-trader"
HOST_FILE="$ENV_DIR/public-host"
URL_FILE="$ENV_DIR/public-url"

if [[ -z "$PUBLIC_HOST" ]]; then
  echo "Usage: $0 <public-hostname> [email]" >&2
  echo "Example: $0 trader.example.com owner@example.com" >&2
  exit 2
fi

if [[ "$PUBLIC_HOST" == http://* || "$PUBLIC_HOST" == https://* || "$PUBLIC_HOST" == */* ]]; then
  echo "Pass only the hostname, without https:// or a path." >&2
  exit 2
fi

export DEBIAN_FRONTEND=noninteractive
apt-get update
apt-get install -y nginx certbot python3-certbot-nginx curl

mkdir -p "$ENV_DIR"
chmod 700 "$ENV_DIR"

cat > /etc/nginx/sites-available/eba-trader <<EOF
server {
    listen 80;
    listen [::]:80;
    server_name ${PUBLIC_HOST};

    server_tokens off;
    client_max_body_size 1m;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_read_timeout 60s;
        add_header X-Content-Type-Options nosniff always;
        add_header Referrer-Policy no-referrer always;
        add_header X-Frame-Options DENY always;
    }
}
EOF

ln -sfn /etc/nginx/sites-available/eba-trader /etc/nginx/sites-enabled/eba-trader
rm -f /etc/nginx/sites-enabled/default
nginx -t
systemctl enable --now nginx
systemctl reload nginx

CERTBOT_ARGS=(
  --nginx
  --non-interactive
  --agree-tos
  --redirect
  --keep-until-expiring
  -d "$PUBLIC_HOST"
)
if [[ -n "$EMAIL" ]]; then
  CERTBOT_ARGS+=(--email "$EMAIL")
else
  CERTBOT_ARGS+=(--register-unsafely-without-email)
fi

certbot "${CERTBOT_ARGS[@]}"

nginx -t
systemctl reload nginx

printf '%s\n' "$PUBLIC_HOST" > "$HOST_FILE"
printf 'https://%s/\n' "$PUBLIC_HOST" > "$URL_FILE"
chmod 600 "$HOST_FILE" "$URL_FILE"

curl --fail --silent --show-error --max-time 15 "https://${PUBLIC_HOST}/api/health" >/dev/null

echo "HTTPS ready: https://${PUBLIC_HOST}/"
echo "Health: https://${PUBLIC_HOST}/api/health"
