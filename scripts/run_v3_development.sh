#!/usr/bin/env bash
set -euo pipefail

cd "$(git rev-parse --show-toplevel)"

if [ -n "$(git status --porcelain --untracked-files=no)" ]; then
  echo "Tracked working tree is dirty. Commit or discard code changes before V3 evidence." >&2
  exit 1
fi

echo "[1/5] Repository provenance"
git log -1 --oneline
git status --short

echo "[2/5] Python runtime"
python --version

echo "[3/5] Complete deterministic test suite"
python -m pytest -q

echo "[4/5] Ruff"
python -m ruff check .

echo "[5/5] Frozen V3 development evidence"
python -m eba_trader.v3_pullback_evidence

echo
echo "V3 development workflow completed."
echo "2025 OOS remains LOCKED_NOT_ACCESSED."
echo "Evidence: artifacts/m4_v3_pullback_development_evidence.json"
