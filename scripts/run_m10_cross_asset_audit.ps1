$ErrorActionPreference = "Stop"

python -m pytest -q
python -m ruff check .
python -c "from eba_trader.m10_cross_asset_policy import verify_m10_freeze; m=verify_m10_freeze(); assert m['status']=='FROZEN_PRE_AUDIT'; assert m['forward_returns']=='forbidden'; assert m['oos_2025']=='LOCKED_NOT_ACCESSED'; print('M10 frozen audit contract verified')"
python -m eba_trader.m10_cross_asset_audit --workers 8
