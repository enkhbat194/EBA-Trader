$ErrorActionPreference = 'Stop'

$repoRoot = (git rev-parse --show-toplevel).Trim()
Set-Location $repoRoot

$dirty = git status --porcelain --untracked-files=no
if ($dirty) {
    throw 'Tracked working tree is dirty. Commit or discard code changes before M6 audit.'
}

$branch = (git branch --show-current).Trim()
if ($branch -ne 'm6-derivatives-data-audit') {
    throw "M6 audit must run on m6-derivatives-data-audit, current branch: $branch"
}

$python = Join-Path $repoRoot '.venv\Scripts\python.exe'
if (-not (Test-Path $python)) {
    throw 'Supported .venv Python is missing. Create the Python 3.12 environment first.'
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

Write-Output '[5/5] M6 derivatives historical data audit'
& $python -m eba_trader.derivatives_audit
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Output ''
Write-Output 'M6 derivatives data-audit workflow completed.'
Write-Output '2025 OOS remains LOCKED_NOT_ACCESSED.'
Write-Output 'Evidence: artifacts/m6_derivatives_data_audit.json'
