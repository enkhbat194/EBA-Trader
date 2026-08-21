#!/usr/bin/env bash
set -euo pipefail

python -m pytest -q
python -m ruff check .
python - <<'PY'
from eba_trader.m11_eth_perpetual_policy import verify_m11_freeze
manifest = verify_m11_freeze()
assert manifest["status"] == "FROZEN_PRE_AUDIT"
assert manifest["forward_returns"] == "forbidden"
assert manifest["oos_2025"] == "LOCKED_NOT_ACCESSED"
print("M11 frozen audit contract verified")
PY
python -m eba_trader.m11_eth_perpetual_audit --workers 8
