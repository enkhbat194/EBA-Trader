$ErrorActionPreference = "Stop"

$branch = git rev-parse --abbrev-ref HEAD
if ($branch -ne "m14-market-neutral-funding-carry") { throw "Run M14 only on m14-market-neutral-funding-carry" }
if (git status --porcelain --untracked-files=no) { throw "Tracked worktree must be clean" }
if (Test-Path "artifacts/m14_market_neutral_funding_carry.json") { throw "M14 evidence already exists" }

python -m pytest -q
python -m ruff check .
python -c "from eba_trader.m14_carry_policy import verify_m14_freeze; verify_m14_freeze(); print('M14 freeze PASS')"
python -m eba_trader.m14_carry
