$ErrorActionPreference = "Stop"

python -m pytest -q
python -m ruff check .
python - <<'PY'
from eba_trader.m10_cross_asset_policy import verify_m10_freeze
manifest = verify_m10_freeze()
assert manifest["status"] == "FROZEN_PRE_AUDIT"
assert manifest["forward_returns"] == "forbidden"
assert manifest["oos_2025"] == "LOCKED_NOT_ACCESSED"
print("M10 frozen audit contract verified")
PY
python -m eba_trader.m10_cross_asset_audit --workers 8
