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
- Automatic deploy timer: `eba-auto-update.timer`
- Runtime API: `127.0.0.1:8765`
- PWA/web service: `127.0.0.1:8000`

## Deprecated infrastructure

- Replit is not part of the active EBA Trader architecture.
- Render.com is not an active backend/runtime target.
- Do not add new EBA Trader work to Replit or Render.
- Old Render-era branch/PR material is historical only and must not be treated as deployment authority.
- PR #14 is closed and superseded.
- BestCode integration remains separate from EBA Trader.

## What is already working in main

### Research/evidence core

- Deterministic risk engine and `NO_TRADE` behavior exist.
- Binance public historical downloader and integrity gates exist.
- Backtest, cost, walk-forward, regime and OOS guard tooling exists.
- Historical research files remain evidence, not deployment instructions.

### Linode/runtime core

- Binance public market data has been observed running on Linode through NautilusTrader.
- `eba-binance-data.service`, `eba-runtime-api.service`, and `eba-web.service` are the canonical runtime services.
- SQLite-backed `TradeLedger` exists outside the Git checkout.
- Runtime API exposes health, positions and events.
- `scripts/install_linode_runtime.sh` is the canonical first-install script.
- `scripts/update_linode_runtime.sh` supports automatic exact-main deployment with service/health verification and rollback.
- `eba-auto-update.timer` checks GitHub `main` every five minutes after one-time activation on the server.
- Deployment state is recorded under `/var/lib/eba-trader/deploy-state` and does not overwrite the trade database.
- `scripts/configure_linode_https.sh` provides the one-time Nginx + Certbot reverse-proxy/TLS setup for a public hostname.
- PR #18 was merged into `main` as the Linode production deployment bundle.

### PWA and Fast Momentum

- PWA/dashboard source is in GitHub `main` under `web/`.
- Trade-detail UI, charts, PWA assets, Binance Demo connection UI and MT5 read-only bridge source are in `main`.
- Fast Momentum supports LONG and SHORT paper decisions for BTCUSDT perpetual simulation.
- Fast Momentum stores OPEN / MARK / CLOSE state in SQLite through `PersistentMomentumPaperEngine`.
- Fast Momentum open position/history can be restored from SQLite after process restart.
- `render.yaml` is not present in `main`.
- PR #17 was the PWA/Fast Momentum migration checkpoint.

## Important current limitations

1. The production bundle is merged, but the Linode server still needs the one-time activation pull/install so the auto-update timer and HTTPS setup script exist on that machine.
2. A public hostname must resolve to the Linode before Certbot HTTPS can be completed.
3. Final phone smoke test against the Linode-served HTTPS PWA is still pending.
4. Fast Momentum persistence/restart recovery still needs a real Linode restart smoke test against the production SQLite database.
5. The older carry paper engine is not persisted/recovered to the same standard as Fast Momentum.
6. Binance real order submission is not enabled or validated.

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

## Next tasks — strict order

1. Perform the one-time Linode activation of the merged production bundle.
2. Point a public hostname to Linode and run the one-time HTTPS setup.
3. Open the Linode HTTPS PWA from the phone and smoke-test Dashboard / Opportunities / Positions / History / Settings / trade detail.
4. Verify Fast Momentum OPEN -> MARK -> CLOSE persistence and restart recovery on the real Linode database.
5. Retire/delete the old Render service only after the Linode PWA passes the phone test.
6. Run forward paper evidence and compare leverage tiers after fees/slippage.
7. Persist/recover the older carry paper engine or remove it if Fast Momentum becomes the only supported paper strategy.
8. Only after the full paper path is restart-safe and statistically acceptable, design a separately gated Binance order-execution layer.

## Safety invariants

- No API secret is committed to GitHub.
- Withdrawal permission is never required.
- Real orders remain disabled until explicitly implemented and validated.
- The deterministic risk layer has veto authority.
- Server/PWA restart must not erase trade history or active Fast Momentum paper state.
- UI state is not the source of truth; Linode/SQLite is.
- Ports 8000 and 8765 remain loopback-only; public access goes through HTTPS reverse proxy.

## Canonical runtime docs

See `docs/LINODE_RUNTIME.md` and `docs/DEPLOYMENT_CHECKLIST.md`. Historical M1/M2/M3 documents remain evidence records only.
