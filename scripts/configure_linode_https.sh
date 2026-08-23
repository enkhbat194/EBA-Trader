#!/usr/bin/env bash
set -euo pipefail

if [[ $EUID -ne 0 ]]; then
  echo "Run as root." >&2
  exit 1
fi

PUBLIC_HOST="${1:-}"
EMAIL="${2:-}"

if [[ -z "$PUBLIC_HOST" || -z "$EMAIL" ]]; then
  echo "Usage: $0 <public-hostname> <email>" >&2
  echo "Example: $0 trader.example.com owner@example.com" >&2
  exit 2
fi

if [[ "$PUBLIC_HOST" == http://* || "$PUBLIC_HOST" == https://* || "$PUBLIC_HOST" == */* ]]; then
  echo "Pass only the hostname, without https:// or a path." >&2
  exit 2
fi

export DEBIAN_FRONTEND=noninteractive
apt-get update
apt-get install -y nginx certbot python3-certbot-nginx

cat > /etc/nginx/sites-available/eba-trader <<EOF
server {
    listen 80;
    listen [::]:80;
    server_name ${PUBLIC_HOST};

    client_max_body_size 1m;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_read_timeout 60s;
    }
}
EOF

ln -sfn /etc/nginx/sites-available/eba-trader /etc/nginx/sites-enabled/eba-trader
rm -f /etc/nginx/sites-enabled/default
nginx -t
systemctl enable --now nginx
systemctl reload nginx

# Certbot verifies that PUBLIC_HOST resolves to this server and then installs HTTPS.
certbot --nginx \
  --non-interactive \
  --agree-tos \
  --redirect \
  --email "$EMAIL" \
  -d "$PUBLIC_HOST"

nginx -t
systemctl reload nginx

mkdir -p /etc/eba-trader
printf '%s\n' "$PUBLIC_HOST" > /etc/eba-trader/public-host
chmod 600 /etc/eba-trader/public-host

echo "HTTPS ready: https://${PUBLIC_HOST}/"
echo "Health: https://${PUBLIC_HOST}/api/health"
