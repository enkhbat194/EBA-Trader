#!/usr/bin/env bash
set -euo pipefail

ENV_FILE="/etc/eba-trader/eba-trader.env"

if [[ $EUID -ne 0 ]]; then
  echo "Run as root." >&2
  exit 1
fi

mkdir -p "$(dirname "$ENV_FILE")"
touch "$ENV_FILE"
chmod 600 "$ENV_FILE"

ensure_default() {
  local key="$1"
  local value="$2"
  if ! grep -q "^${key}=" "$ENV_FILE"; then
    printf '%s=%s\n' "$key" "$value" >> "$ENV_FILE"
  fi
}

ensure_default EBA_RESEARCH_DB /var/lib/eba-trader/research/eba_research.db
ensure_default EBA_RESEARCH_DATASET_ROOT /var/lib/eba-trader/research/datasets
ensure_default EBA_RESEARCH_EVIDENCE_ROOT /var/lib/eba-trader/research/evidence
