# EBA Trader — Project State

_Last updated: 2026-08-24 (Asia/Ulaanbaatar)_

This is the authoritative cross-chat continuation record. If older chat text, old deployment notes, screenshots, old PRs, or old branches conflict with this file, this file wins.

## Current goal

Run EBA Trader as a restart-safe 24/7 system on one Linode server, validate short-horizon strategies with paper trading first, persist every trade, expose clear position/history/chart data to the PWA, and keep real-money execution locked until the execution path is separately proven.

## Source of truth and infrastructure

- Repository: `enkhbat194/EBA-Trader`
- Source of truth: GitHub `main`
- Sole active runtime target: Akamai/Linode Nanode 1 GB
- Region: Singapore 2
- OS: Ubuntu 24.04 LTS
- Server repo path: `/opt/Eba-Trader`
- Persistent state: `/var/lib/eba-trader/eba_trader.db`
- Market-data service: `eba-binance-data.service`
- Runtime API service: `eba-runtime-api.service`
- PWA/web/scanner service: `eba-web.service`
- Runtime API: `127.0.0.1:8765` until authenticated HTTPS proxy is added
- PWA/web service: `127.0.0.1:8000` until authenticated HTTPS proxy is added

## Deprecated infrastructure

- Replit is not part of the active EBA Trader architecture.
- Render.com is not an active backend/runtime target.
- Do not add new EBA Trader work to Replit or Render.
- Old Render-era branch/PR material is historical only and must not be treated as deployment authority.
- PR #14 is closed and superseded.
- BestCode integration remains separate from EBA Trader.

## What is already working

### Research/evidence core

- Deterministic risk engine and `NO_TRADE` behavior exist.
- Binance public historical downloader and integrity gates exist.
- Backtest, cost, walk-forward, regime and OOS guard tooling exists.
- Trend V1 historical development cycle was rejected; its evidence remains preserved under `docs/`.
- Historical research files are evidence, not deployment instructions.

### Linode/runtime core

- Binance public market data has been observed running on Linode through NautilusTrader.
- `eba-binance-data.service` starts at boot and restarts after failure.
- SQLite-backed `TradeLedger` exists.
- `eba-runtime-api.service` exists.
- Runtime API exposes health, positions and events.
- `scripts/install_linode_runtime.sh` is the canonical first-install script.
- `scripts/update_linode_runtime.sh` is the canonical update script.

### PWA and Fast Momentum migration

- The useful PWA/dashboard source is now in GitHub `main` under `web/`.
- Trade-detail UI, charts, PWA assets, Binance Demo connection UI and MT5 read-only bridge source are now in `main`.
- `eba-web.service` is included for the Linode-hosted PWA/server-side scanner.
- Fast Momentum supports LONG and SHORT paper decisions for BTCUSDT perpetual simulation.
- Fast Momentum stores OPEN / MARK / CLOSE state in SQLite through `PersistentMomentumPaperEngine`.
- Fast Momentum open position/history can be restored from SQLite after process restart.
- PWA update/status text now describes Linode rather than Render.
- `render.yaml` is not present in `main`.
- PR #17 was merged into `main` as the migration checkpoint.
- Main runtime CI now runs on pushes/PRs to `main`.

## Important current limitations

1. Linode PWA is still private on `127.0.0.1:8000`; authenticated HTTPS/reverse-proxy exposure is not complete.
2. Final phone smoke test against the Linode-served PWA is still pending.
3. The older carry paper engine is not yet persisted/recovered to the same standard as Fast Momentum.
4. GitHub `main` -> Linode automatic deployment with health check/rollback is not complete.
5. Binance real order submission is not enabled or validated.

## Active trading direction

Fast Momentum / Micro Profit paper mode is the current short-horizon runtime strategy direction:

- BTCUSDT perpetual simulation
- 1m + 5m inputs
- both LONG and SHORT eligibility
- paper margin starts from $10
- risk-selected leverage caps 5x / 10x / 20x
- explicit entry, TP, SL, fees and net P&L
- dedicated trade detail/chart record
- indicator values visible in the trade detail UI
- live execution remains locked

The older Spot-only Trend path remains historical evidence, not the active deployment direction.

## Next tasks — strict order

1. Add authenticated HTTPS reverse proxy for the Linode PWA/web service without exposing port 8000 directly.
2. Deploy/update `main` on Linode and verify `eba-binance-data`, `eba-runtime-api`, and `eba-web` are all healthy.
3. Open the Linode-served PWA from the phone and smoke-test Dashboard / Opportunities / Positions / History / Settings / trade detail.
4. Verify Fast Momentum OPEN -> MARK -> CLOSE persistence and restart recovery on the real Linode database.
5. Retire/delete the old Render service only after the Linode PWA passes the phone test.
6. Add GitHub `main` -> Linode automatic deployment with health-check and rollback behavior.
7. Persist/recover the older carry paper engine or remove it if Fast Momentum becomes the only supported paper strategy.
8. Run forward paper evidence and compare leverage tiers after fees/slippage.
9. Only after the full paper path is restart-safe and statistically acceptable, design a separately gated Binance order-execution layer.

## Safety invariants

- No API secret is committed to GitHub.
- Withdrawal permission is never required.
- Real orders remain disabled until explicitly implemented and validated.
- The deterministic risk layer has veto authority.
- Server/PWA restart must not erase trade history or active Fast Momentum paper state.
- UI state is not the source of truth; Linode/SQLite is.
- Port 8000 must not be exposed directly to the public internet without an authenticated HTTPS boundary.

## Canonical runtime docs

See `docs/LINODE_RUNTIME.md` for deployment/runtime details. Historical M1/M2/M3 documents remain evidence records only.
