#!/usr/bin/env bash
set -euo pipefail

branch="$(git rev-parse --abbrev-ref HEAD)"
[[ "$branch" == "m14-market-neutral-funding-carry" ]] || { echo "Run M14 only on m14-market-neutral-funding-carry"; exit 1; }
[[ -z "$(git status --porcelain --untracked-files=no)" ]] || { echo "Tracked worktree must be clean"; exit 1; }
[[ ! -e artifacts/m14_market_neutral_funding_carry.json ]] || { echo "M14 evidence already exists"; exit 1; }

python -m pytest -q
python -m ruff check .
python -c "from eba_trader.m14_carry_policy import verify_m14_freeze; verify_m14_freeze(); print('M14 freeze PASS')"
python -m eba_trader.m14_carry
