#!/usr/bin/env bash
set -euo pipefail

repo_root="$(git rev-parse --show-toplevel)"
cd "$repo_root"

if [[ -n "$(git status --porcelain --untracked-files=no)" ]]; then
  echo 'Tracked working tree is dirty. Commit or discard code changes before M6 audit.' >&2
  exit 1
fi

branch="$(git branch --show-current)"
if [[ "$branch" != "m6-derivatives-data-audit" ]]; then
  echo "M6 audit must run on m6-derivatives-data-audit, current branch: $branch" >&2
  exit 1
fi

python_bin="$repo_root/.venv/bin/python"
if [[ ! -x "$python_bin" ]]; then
  echo 'Supported .venv Python is missing. Create the Python 3.12 environment first.' >&2
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

echo '[5/6] Seed checksum-verified Binance Vision 2021-2024 archives'
"$python_bin" -m eba_trader.derivatives_archive_seed

echo '[6/6] M6 derivatives historical data audit'
"$python_bin" -m eba_trader.derivatives_audit --no-download

echo
echo 'M6 derivatives data-audit workflow completed.'
echo '2025 OOS remains LOCKED_NOT_ACCESSED.'
echo 'Archive manifest: data/cache/m6/binance_vision_manifest.json'
echo 'Evidence: artifacts/m6_derivatives_data_audit.json'
