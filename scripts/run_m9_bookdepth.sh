#!/usr/bin/env bash
set -euo pipefail

echo '[M9] Verify frozen policy'
python -c "from eba_trader.m9_bookdepth_policy import verify_m9_freeze; verify_m9_freeze(); print('M9 freeze verified')"

echo '[M9] Run full deterministic tests'
python -m pytest -q

echo '[M9] Run Ruff'
python -m ruff check .

echo '[M9] Run frozen 2023 discovery / 2024 challenge evidence once'
python -m eba_trader.m9_bookdepth --workers 12
