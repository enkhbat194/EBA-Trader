# Scanner status incident — 2026-08-28

## User-visible symptom

Production Settings showed `Server scanner: UNREACHABLE` while Runtime/HTTPS/build indicators remained healthy. `Last server scans` displayed `Can't find variable: mt5PositionMarkup`.

## Root cause

This was a real browser JavaScript defect plus an observability-classification defect:

1. `trade_detail.js` invoked `mt5PositionMarkup(...)` without a definition. The same combined-position path also depended on an undefined legacy `paperPositionMarkup(...)` helper.
2. Settings runner sync grouped `/api/runner/status` transport and optional UI renderer execution under one catch block. Any successful API response followed by a renderer exception was therefore mislabeled as a server/network outage.
3. Settings used aggregate legacy `threadAlive`; Fast Momentum is the sole active production paper scanner and must use its own heartbeat fields.
4. Static PWA assets needed explicit network revalidation to reduce mixed-version JS after deployments.

## Accepted observability contract

- `UNREACHABLE` means `/api/runner/status` itself could not be fetched/validated.
- A browser renderer exception must **not** change a successfully fetched server/scanner health result to `UNREACHABLE`.
- Fast Momentum scanner status is derived from `fastPaperAvailable`, `fastRunning`, `fastThreadAlive`, `lastFastScanAtMs`, and the configured scan interval.
- UI-only faults may be surfaced as `UI sync warning` while preserving backend health truth.
- Required shared renderer functions must be defined before dependent scripts load.
- Service-worker/static asset refresh should prefer current network content and use cached assets only as fallback.

## Implementation

PR #65 changed:

- `web/paper_ui.js` — defines `paperPositionMarkup` and `mt5PositionMarkup`.
- `web/scanner_heartbeat.js` — Fast scanner health truth and UI/API error separation.
- `web/sw.js` — fresh static asset revalidation/cache update behavior.
- `tests/test_scanner_status_ui_hotfix.py` — regression contracts.

PR #65 merged as:

`b1afa22fcfa459d2a8a3789291b74a0566041545`

## Validation

Exact PR head `7d6e67ffed44228bec6df093c2041f43cb66b5cf` passed full regression, Ruff, shell/deployment, Linode runtime and continuity checks.

Exact merged main `b1afa22fcfa459d2a8a3789291b74a0566041545` passed hardened external exact-build production proof run `33111336161`.

Public production smoke run `33111336195` first observed a transient nginx `/api/chart` 502 while deploy convergence was still occurring. Rerun attempt 2 passed on the same exact main SHA.

The hotfix did not change strategy logic, risk logic, lifecycle authority, Frozen OOS access or real execution. Frozen OOS and real-money execution remain locked.
