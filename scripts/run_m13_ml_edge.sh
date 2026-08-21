#!/usr/bin/env bash
set -euo pipefail

branch="$(git rev-parse --abbrev-ref HEAD)"
[[ "$branch" == "m13-ml-edge-engine" ]] || { echo "Run M13 only on m13-ml-edge-engine"; exit 1; }
[[ -z "$(git status --porcelain --untracked-files=no)" ]] || { echo "Tracked worktree must be clean"; exit 1; }
[[ ! -e artifacts/m13_ml_edge_engine.json ]] || { echo "M13 evidence already exists"; exit 1; }

python -m pytest -q
python -m ruff check .
python -c "from eba_trader.m13_ml_policy import verify_m13_freeze; verify_m13_freeze(); print('M13 freeze PASS')"
python -m eba_trader.m13_ml_edge
