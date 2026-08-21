#!/usr/bin/env bash
set -euo pipefail

branch="$(git rev-parse --abbrev-ref HEAD)"
if [[ "$branch" != "m12-cross-asset-eth-btc-edge" ]]; then
  echo "M12 runner requires branch m12-cross-asset-eth-btc-edge" >&2
  exit 1
fi
if [[ -n "$(git status --porcelain --untracked-files=no)" ]]; then
  echo "Tracked worktree must be clean before M12 evidence" >&2
  exit 1
fi
if [[ -e artifacts/m12_cross_asset_eth_btc_edge.json ]]; then
  echo "M12 evidence already exists; preserve the first result" >&2
  exit 1
fi

python -m pytest -q
python -m ruff check .
python - <<'PY'
from eba_trader.m12_cross_asset_policy import verify_m12_freeze
manifest = verify_m12_freeze()
assert manifest["status"] == "FROZEN_PREDECLARED_NOT_RUN"
assert manifest["candidate_count"] == 8
assert manifest["hypothesis_test_count"] == 24
assert manifest["oos_2025"] == "LOCKED_NOT_ACCESSED"
print("M12 frozen research contract verified")
PY

python - <<'PY'
from pathlib import Path
from eba_trader.m7_seed import _seed_spot
from eba_trader.m11_eth_perpetual_audit import run_m11_eth_perpetual_audit
from eba_trader.m12_cross_asset_policy import ETH_SHA256, sha256_file

cache = Path("data/cache/m2")
cache.mkdir(parents=True, exist_ok=True)
_seed_spot(cache)
eth = Path("data/cache/m12/m11_ethusdt_usdm_15m_normalized.csv")
report = run_m11_eth_perpetual_audit(
    workers=8,
    report_path="artifacts/m12_m11_seed_audit.json",
    normalized_path=eth,
)
assert report["decision"] == "M11_ETH_PERPETUAL_DATA_AUDIT_PASS"
assert sha256_file(eth) == ETH_SHA256
print("M12 frozen inputs seeded and hash verified")
PY

python -m eba_trader.m12_cross_asset
