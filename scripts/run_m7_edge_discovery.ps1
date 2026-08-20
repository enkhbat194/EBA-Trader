$ErrorActionPreference = 'Stop'

$repoRoot = (git rev-parse --show-toplevel).Trim()
Set-Location $repoRoot

$dirty = git status --porcelain --untracked-files=no
if ($dirty) {
    throw 'Tracked working tree is dirty. Commit or discard code changes before M7.'
}

$branch = (git branch --show-current).Trim()
if ($branch -ne 'm7-funding-futures-edge-discovery') {
    throw "M7 must run on m7-funding-futures-edge-discovery, current branch: $branch"
}

$python = Join-Path $repoRoot '.venv\Scripts\python.exe'
if (-not (Test-Path $python)) {
    throw 'Supported .venv Python is missing. Create the Python 3.12 environment first.'
}

$report = Join-Path $repoRoot 'artifacts\m7_funding_futures_edge_discovery.json'
if (Test-Path $report) {
    throw 'M7 evidence already exists. Preserve the first frozen-search result; do not overwrite it.'
}

Write-Output '[1/6] Repository provenance'
git log -1 --oneline
git status --short

Write-Output '[2/6] Python runtime'
& $python --version

Write-Output '[3/6] Complete deterministic test suite'
& $python -m pytest -q
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Output '[4/6] Ruff'
& $python -m ruff check .
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Output '[5/6] Seed/verify only frozen M7 inputs'
& $python -m eba_trader.m7_seed
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Output '[6/6] Frozen M7 funding + futures edge discovery'
& $python -m eba_trader.m7_funding_flow
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Output ''
Write-Output 'M7 workflow completed.'
Write-Output '2025 OOS remains LOCKED_NOT_ACCESSED.'
Write-Output 'Evidence: artifacts/m7_funding_futures_edge_discovery.json'
