$ErrorActionPreference = "Stop"

python -m eba_trader.m7_seed --workers 8
python -m eba_trader.m15_basis
