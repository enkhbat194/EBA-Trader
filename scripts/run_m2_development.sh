#!/usr/bin/env bash
set -euo pipefail

cd "$(git rev-parse --show-toplevel)"

echo "[1/5] Python runtime"
python --version

if [ ! -d .venv ]; then
  echo "[2/5] Creating virtual environment"
  python -m venv .venv
else
  echo "[2/5] Reusing .venv"
fi

# Replit/Nix may export PIP_USER, which conflicts with virtualenv installs.
# Override only for this process; do not mutate the system Python.
export PIP_USER=0
# shellcheck disable=SC1091
source .venv/bin/activate

echo "[3/5] Installing EBA Trader dependencies"
python -m pip install -e '.[trading,dev]'

echo "[4/5] Running full deterministic test suite"
pytest -q

echo "[5/5] Running locked M2 development study"
eba-development-study

echo
echo "M2 development run finished."
echo "2025 OOS remains LOCKED_NOT_ACCESSED."
echo "Primary evidence: artifacts/m2_development_evidence.json"
