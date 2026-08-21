$ErrorActionPreference = "Stop"

python -m pytest -q
python -m ruff check .
python -c "from eba_trader.m11_eth_perpetual_policy import verify_m11_freeze; m=verify_m11_freeze(); assert m['status']=='FROZEN_PRE_AUDIT'; assert m['forward_returns']=='forbidden'; assert m['oos_2025']=='LOCKED_NOT_ACCESSED'; print('M11 frozen audit contract verified')"
python -m eba_trader.m11_eth_perpetual_audit --workers 8
