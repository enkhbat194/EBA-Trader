$ErrorActionPreference = 'Stop'

$repoRoot = (git rev-parse --show-toplevel).Trim()
Set-Location $repoRoot

$branch = (git branch --show-current).Trim()
if ($branch -ne 'edge-discovery-engine') {
    throw "Run M5 only from edge-discovery-engine; current branch is $branch"
}

$dirty = git status --porcelain --untracked-files=no
if ($dirty) {
    throw 'Tracked working tree is dirty. Commit or discard code changes before M5 evidence.'
}

$report = Join-Path $repoRoot 'artifacts\m5_edge_discovery_price_volume_v1.json'
if (Test-Path $report) {
    throw 'M5 report already exists. Preserve the first complete frozen-search result.'
}

$python = Join-Path $repoRoot '.venv\Scripts\python.exe'
if (-not (Test-Path $python)) {
    throw 'Supported .venv Python is missing. Create the Python 3.12 environment before running M5.'
}

Write-Output '[1/5] Repository provenance'
git log -1 --oneline
git status --short

Write-Output '[2/5] Python runtime'
& $python --version

Write-Output '[3/5] Complete deterministic test suite'
& $python -m pytest -q
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Output '[4/5] Ruff'
& $python -m ruff check .
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Output '[5/5] Frozen M5 price-volume edge discovery'
& $python -m eba_trader.edge_discovery
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Output ''
Write-Output 'M5 edge discovery workflow completed.'
Write-Output 'No strategy was generated or traded.'
Write-Output '2025 OOS remains LOCKED_NOT_ACCESSED.'
Write-Output 'Evidence: artifacts/m5_edge_discovery_price_volume_v1.json'
