$ErrorActionPreference = 'Stop'

$repoRoot = (git rev-parse --show-toplevel).Trim()
Set-Location $repoRoot

$dirty = git status --porcelain --untracked-files=no
if ($dirty) {
    throw 'Tracked working tree is dirty. Commit or discard code changes before V3 evidence.'
}

$python = Join-Path $repoRoot '.venv\Scripts\python.exe'
if (-not (Test-Path $python)) {
    throw 'Supported .venv Python is missing. Create the Python 3.12 environment before running V3.'
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

Write-Output '[5/5] Frozen V3 development evidence'
& $python -m eba_trader.v3_pullback_evidence
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Output ''
Write-Output 'V3 development workflow completed.'
Write-Output '2025 OOS remains LOCKED_NOT_ACCESSED.'
Write-Output 'Evidence: artifacts/m4_v3_pullback_development_evidence.json'
