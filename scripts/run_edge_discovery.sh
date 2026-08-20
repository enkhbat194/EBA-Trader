#!/usr/bin/env bash
set -euo pipefail

cd "$(git rev-parse --show-toplevel)"

branch="$(git branch --show-current)"
if [[ "$branch" != "edge-discovery-engine" ]]; then
  echo "Run M5 only from edge-discovery-engine; current branch is $branch" >&2
  exit 1
fi

if [[ -n "$(git status --porcelain --untracked-files=no)" ]]; then
  echo "Tracked working tree is dirty. Commit or discard code changes before M5 evidence." >&2
  exit 1
fi

report="artifacts/m5_edge_discovery_price_volume_v1.json"
if [[ -e "$report" ]]; then
  echo "M5 report already exists. Preserve the first complete frozen-search result." >&2
  exit 1
fi

python_bin=".venv/bin/python"
if [[ ! -x "$python_bin" ]]; then
  echo "Supported .venv Python is missing. Create the Python 3.12 environment before running M5." >&2
  exit 1
fi

echo "[1/5] Repository provenance"
git log -1 --oneline
git status --short

echo "[2/5] Python runtime"
"$python_bin" --version

echo "[3/5] Complete deterministic test suite"
"$python_bin" -m pytest -q

echo "[4/5] Ruff"
"$python_bin" -m ruff check .

echo "[5/5] Frozen M5 price-volume edge discovery"
"$python_bin" -m eba_trader.edge_discovery

echo
echo "M5 edge discovery workflow completed."
echo "No strategy was generated or traded."
echo "2025 OOS remains LOCKED_NOT_ACCESSED."
echo "Evidence: artifacts/m5_edge_discovery_price_volume_v1.json"
