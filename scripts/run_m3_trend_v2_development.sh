#!/usr/bin/env bash
set -euo pipefail

cd "$(git rev-parse --show-toplevel)"

echo "[1/3] Running complete deterministic test suite"
pytest -q

echo "[2/3] Running Ruff"
ruff check .

echo "[3/3] Running frozen Trend V2 development evidence"
eba-trend-v2-development

echo "2025 OOS remains LOCKED_NOT_ACCESSED."
