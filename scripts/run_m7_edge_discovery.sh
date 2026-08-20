#!/usr/bin/env bash
set -euo pipefail

repo_root="$(git rev-parse --show-toplevel)"
cd "$repo_root"

if [[ -n "$(git status --porcelain --untracked-files=no)" ]]; then
  echo 'Tracked working tree is dirty. Commit or discard code changes before M7.' >&2
  exit 1
fi

branch="$(git branch --show-current)"
if [[ "$branch" != "m7-funding-futures-edge-discovery" ]]; then
  echo "M7 must run on m7-funding-futures-edge-discovery, current branch: $branch" >&2
  exit 1
fi

python_bin="$repo_root/.venv/bin/python"
if [[ ! -x "$python_bin" ]]; then
  echo 'Supported .venv Python is missing. Create the Python 3.12 environment first.' >&2
  exit 1
fi

report="$repo_root/artifacts/m7_funding_futures_edge_discovery.json"
if [[ -f "$report" ]]; then
  echo 'M7 evidence already exists. Preserve the first frozen-search result; do not overwrite it.' >&2
  exit 1
fi

echo '[1/6] Repository provenance'
git log -1 --oneline
git status --short

echo '[2/6] Python runtime'
"$python_bin" --version

echo '[3/6] Complete deterministic test suite'
"$python_bin" -m pytest -q

echo '[4/6] Ruff'
"$python_bin" -m ruff check .

echo '[5/6] Seed/verify only frozen M7 inputs'
"$python_bin" -m eba_trader.m7_seed

echo '[6/6] Frozen M7 funding + futures edge discovery'
"$python_bin" -m eba_trader.m7_funding_flow

echo
echo 'M7 workflow completed.'
echo '2025 OOS remains LOCKED_NOT_ACCESSED.'
echo 'Evidence: artifacts/m7_funding_futures_edge_discovery.json'
