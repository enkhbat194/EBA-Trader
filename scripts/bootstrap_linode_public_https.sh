#!/usr/bin/env bash
set -euo pipefail

REPO_DIR="/opt/Eba-Trader"
ENV_DIR="/etc/eba-trader"
HOST_FILE="$ENV_DIR/public-host"
URL_FILE="$ENV_DIR/public-url"

if [[ $EUID -ne 0 ]]; then
  echo "Run as root." >&2
  exit 1
fi

cd "$REPO_DIR"
mkdir -p "$ENV_DIR"
chmod 700 "$ENV_DIR"

if [[ -s "$HOST_FILE" ]]; then
  SAVED_HOST="$(tr -d '[:space:]' < "$HOST_FILE")"
  if [[ -n "$SAVED_HOST" ]]; then
    echo "EBA public host already configured: $SAVED_HOST"
    if curl --fail --silent --show-error --max-time 10 "https://${SAVED_HOST}/api/health" >/dev/null 2>&1; then
      printf 'https://%s/\n' "$SAVED_HOST" > "$URL_FILE"
      chmod 600 "$URL_FILE"
      echo "HTTPS health is already good."
      exit 0
    fi
    echo "Saved host exists but HTTPS health is not ready; repairing configuration."
    exec bash scripts/configure_linode_https.sh "$SAVED_HOST"
  fi
fi

is_public_ipv4() {
  local ip="$1"
  [[ "$ip" =~ ^[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+$ ]] || return 1
  case "$ip" in
    10.*|127.*|169.254.*|192.168.*) return 1 ;;
  esac

  local first second
  IFS=. read -r first second _ _ <<< "$ip"
  if [[ "$first" == "172" && "$second" -ge 16 && "$second" -le 31 ]]; then
    return 1
  fi
  if [[ "$first" == "100" && "$second" -ge 64 && "$second" -le 127 ]]; then
    return 1
  fi
  return 0
}

PUBLIC_IPV4=""
while read -r candidate; do
  if is_public_ipv4 "$candidate"; then
    PUBLIC_IPV4="$candidate"
    break
  fi
done < <(ip -4 -o addr show scope global | awk '{split($4,a,"/"); print a[1]}')

if [[ -z "$PUBLIC_IPV4" ]]; then
  echo "Could not determine a public IPv4 address from this Linode." >&2
  exit 2
fi

DASHED_IP="${PUBLIC_IPV4//./-}"
CANDIDATES=(
  "eba-trader-${DASHED_IP}.sslip.io"
  "eba-trader-${DASHED_IP}.nip.io"
)

host_resolves_here() {
  local host="$1"
  local resolved
  resolved="$(getent ahostsv4 "$host" 2>/dev/null | awk 'NR==1 {print $1}')"
  [[ "$resolved" == "$PUBLIC_IPV4" ]]
}

for host in "${CANDIDATES[@]}"; do
  echo "Trying automatic EBA hostname: $host"
  for _ in $(seq 1 12); do
    if host_resolves_here "$host"; then
      break
    fi
    sleep 5
  done

  if ! host_resolves_here "$host"; then
    echo "DNS did not resolve $host to $PUBLIC_IPV4; trying the next provider." >&2
    continue
  fi

  if bash scripts/configure_linode_https.sh "$host"; then
    printf 'https://%s/\n' "$host" > "$URL_FILE"
    chmod 600 "$URL_FILE"
    echo "EBA Trader public PWA ready: https://${host}/"
    exit 0
  fi

  echo "TLS bootstrap failed for $host; trying the next provider." >&2
done

echo "Automatic HTTPS bootstrap did not complete. Runtime remains healthy on loopback." >&2
exit 3
