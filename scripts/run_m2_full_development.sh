#!/usr/bin/env bash
set -euo pipefail

cd "$(git rev-parse --show-toplevel)"

echo "[1/8] Python runtime"
python --version

if [ ! -d .venv ]; then
  echo "[2/8] Creating virtual environment"
  python -m venv .venv
else
  echo "[2/8] Reusing .venv"
fi

export PIP_USER=0
# shellcheck disable=SC1091
source .venv/bin/activate

echo "[3/8] Installing current project"
python -m pip install -e '.[trading,dev]'

echo "[4/8] Running complete deterministic test suite"
pytest -q

echo "[5/8] Running locked signal development evidence"
eba-development-study

echo "[6/8] Applying signal screening"
eba-development-verdict

echo "[7/8] Running predeclared risk-sized execution evidence"
eba-risk-execution-study

echo "[8/8] Applying risk execution screening"
eba-risk-execution-verdict

echo
echo "M2 development stages passed."
echo "2025 OOS remains LOCKED_NOT_ACCESSED."
echo "Signal evidence: artifacts/m2_development_evidence.json"
echo "Signal verdict:  artifacts/m2_development_verdict.json"
echo "Risk evidence:   artifacts/m2_risk_execution_evidence.json"
echo "Risk verdict:    artifacts/m2_risk_execution_verdict.json"
echo "Do not open 2025 until these reports are reviewed and final freeze is created."
