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

echo '[1/5] Repository provenance'
git log -1 --oneline
git status --short

echo '[2/5] Python runtime'
"$python_bin" --version

echo '[3/5] Complete deterministic test suite'
"$python_bin" -m pytest -q

echo '[4/5] Ruff'
"$python_bin" -m ruff check .

echo '[5/5] M6 derivatives historical data audit'
"$python_bin" -m eba_trader.derivatives_audit

echo
echo 'M6 derivatives data-audit workflow completed.'
echo '2025 OOS remains LOCKED_NOT_ACCESSED.'
echo 'Evidence: artifacts/m6_derivatives_data_audit.json'
