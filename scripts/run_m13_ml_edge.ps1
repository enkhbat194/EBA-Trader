$ErrorActionPreference = "Stop"

$branch = git rev-parse --abbrev-ref HEAD
if ($branch -ne "m13-ml-edge-engine") { throw "Run M13 only on m13-ml-edge-engine" }
if (git status --porcelain --untracked-files=no) { throw "Tracked worktree must be clean" }
if (Test-Path "artifacts/m13_ml_edge_engine.json") { throw "M13 evidence already exists" }

python -m pytest -q
python -m ruff check .
python -c "from eba_trader.m13_ml_policy import verify_m13_freeze; verify_m13_freeze(); print('M13 freeze PASS')"
python -m eba_trader.m13_ml_edge
