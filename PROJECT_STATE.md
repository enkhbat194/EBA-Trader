# EBA Trader — Project State

_Last updated: 2026-08-24 (Asia/Ulaanbaatar)_

This is the authoritative cross-chat continuation record. If older chat text, old deployment notes, or screenshots conflict with this file, this file wins.

## Current goal

Build EBA Trader as a restart-safe, 24/7 trading system on one Linux server. Validate short-horizon strategies with paper trading first, record every trade durably, expose clear position/history/chart data to the PWA, and keep real-money execution locked until the execution path is separately proven.

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
- Runtime API: `127.0.0.1:8765` until authenticated HTTPS proxy is added

## Deprecated infrastructure

- Replit is not part of the active EBA Trader architecture.
- Render.com is not the target backend/runtime anymore.
- Do not add new EBA Trader work to Replit or Render.
- The old Render-backed dashboard/PWA may remain reachable only as a temporary client during migration. It is not authoritative and should be retired after the PWA is connected to Linode.
- BestCode integration remains separate from EBA Trader.

## What is already working

### Research/evidence core

- Deterministic risk engine and `NO_TRADE` behavior exist.
- Binance public historical downloader and integrity gates exist.
- Backtest, cost, walk-forward, regime and OOS guard tooling exists.
- Trend V1 historical development cycle was rejected; its evidence remains preserved under `docs/`.
- Historical research files are retained as evidence and are not active deployment instructions.

### Linode runtime

- Binance public market data has been observed running on Linode through NautilusTrader.
- `eba-binance-data.service` starts at boot and restarts after failure.
- SQLite-backed `TradeLedger` exists.
- `eba-runtime-api.service` exists.
- Runtime API currently exposes health, positions and events.
- `scripts/install_linode_runtime.sh` is the canonical first-install script.
- `scripts/update_linode_runtime.sh` is the canonical update script.

## Important current limitations

1. The paper execution engine is not yet fully wired to `TradeLedger`; OPEN / UPDATE / CLOSE must all be persisted.
2. Restart recovery of an active paper position is not complete until the execution engine reads OPEN positions from SQLite on startup.
3. Runtime API is local-only and is not yet exposed to the PWA through authenticated HTTPS.
4. The PWA/dashboard source is not present as a confirmed active frontend inside this repository, so the old Render client cannot simply be switched off before the frontend source/endpoint is migrated.
5. Binance real order submission is not enabled or validated.

## Active trading direction

The old Spot-only Trend research path is historical evidence, not the only runtime strategy direction.

The next paper strategy target is a separate **Fast Momentum / Micro Profit** mode for Binance perpetual futures simulation:

- BTCUSDT
- 1m + 5m inputs
- both LONG and SHORT eligibility
- small margin test sizes, starting from $10
- leverage tiers tested in paper mode first (5x / 10x / 20x; higher leverage remains aggressive-demo only until evidence supports it)
- explicit entry, TP, SL, fees, slippage, liquidation distance and net P&L
- each trade gets its own detail/chart record
- strategy/indicator values must be visible in the trade detail UI

This does not authorize real leveraged orders. Paper evidence comes first.

## Next tasks — strict order

1. Integrate the paper execution engine with `TradeLedger` for every OPEN / UPDATE / CLOSE event.
2. Add startup recovery from SQLite for OPEN paper positions.
3. Expand runtime API for completed trade history and trade detail data.
4. Add authenticated HTTPS reverse proxy on Linode.
5. Locate/migrate the actual PWA/dashboard frontend and point it only at Linode; then retire Render.
6. Add GitHub-main -> Linode automatic deployment with health-check/rollback behavior so routine updates do not require Weblish commands.
7. Implement and validate Fast Momentum LONG/SHORT paper execution with clear TP/SL/indicator/chart visibility.
8. Run forward paper evidence and compare leverage tiers after fees/slippage.
9. Only after the full paper path is restart-safe and statistically acceptable, design a separately gated Binance order-execution layer.

## Safety invariants

- No API secret is committed to GitHub.
- Withdrawal permission is never required.
- Real orders remain disabled until explicitly implemented and validated.
- The deterministic risk layer has veto authority.
- Server/PWA restart must not erase trade history or active paper state.
- UI state is not the source of truth; the Linode ledger/runtime is.

## Canonical runtime docs

See `docs/LINODE_RUNTIME.md` for deployment/runtime details. Historical M1/M2/M3 documents remain evidence records only.
