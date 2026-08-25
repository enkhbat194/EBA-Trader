# EBA Trader — Project State

_Last updated: 2026-08-25 (Asia/Ulaanbaatar)_

This is the authoritative cross-chat continuation record. If older chat text, old deployment notes, screenshots, old PRs, or old branches conflict with this file, this file wins.

## Current goal

Run EBA Trader as a restart-safe 24/7 system on one Linode server, validate short-horizon strategies with paper trading first, persist every trade, expose clear position/history/chart data to the PWA, and keep real-money execution locked until the execution path is separately proven.

In parallel, build the M4 research control plane required before any mass AI strategy generator: immutable strategy versions, deterministic experiments, machine-enforced lifecycle gates, durable evidence and restart-safe experiment workers.

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
- M4 foundation PR #20 is merged as `d3a31ec0ee2556ec1e577fd9b16662a3bbe6614f`.
- Generic strategy decisions are now `LONG`, `SHORT`, `EXIT`, and `NO_TRADE`; historical `Decision.BUY` is only a temporary compatibility alias to `LONG`.
- Generic deterministic risk sizing now handles LONG and SHORT stop distance symmetrically.
- `StrategyLifecycle` enforces ordered promotion gates and requires an evidence reference for promotions.
- `ResearchStore` provides a separate SQLite control plane for immutable strategy versions, experiment metadata, and lifecycle history without coupling research state to runtime `TradeLedger` positions.
- Experiment IDs are deterministic from strategy/version/stage/parameters/dataset, establishing the base for duplicate detection and resumable experiment queues.
- Production CI now starts correctly and runs the full Python regression suite plus Ruff, shell syntax, and deployment-contract checks.

### Linode/runtime core

- Binance public market data has been observed running on Linode through NautilusTrader.
- `eba-binance-data.service`, `eba-runtime-api.service`, and `eba-web.service` are the canonical runtime services.
- SQLite-backed `TradeLedger` exists outside the Git checkout.
- Runtime API exposes health, positions and events.
- `scripts/install_linode_runtime.sh` is the canonical first-install script.
- `scripts/update_linode_runtime.sh` supports automatic exact-main deployment with service/health verification and rollback.
- `eba-auto-update.timer` is already activated on the Linode and checks GitHub `main` every five minutes.
- Deployment state is recorded under `/var/lib/eba-trader/deploy-state` and does not overwrite the trade database.
- `scripts/bootstrap_linode_public_https.sh` automatically derives an IP-backed hostname and attempts Nginx + Certbot HTTPS setup, with sslip.io and nip.io fallback.
- HTTPS failure is non-fatal to the trading runtime and is retried by the existing auto-update timer.
- PR #18 added the production deployment bundle.
- PR #19 added hands-free public HTTPS bootstrap and credential-independent Fast paper operation.

### PWA and Fast Momentum

- PWA/dashboard source is in GitHub `main` under `web/`.
- Settings reports app/server version, build, PWA cache, Linode runtime state, public-PWA HTTPS state and server scanner freshness.
- Live chart code supports touch pinch zoom, drag/pan, mouse-wheel zoom, EMA20 and EMA50 overlays, and paper markers.
- Fast trades have dedicated trade-detail UI with entry/current-or-exit, TP, SL, leverage, P&L, fees, indicators, EMA overlays, zoom/pan and history access.
- Fast Momentum supports LONG and SHORT paper decisions for BTCUSDT perpetual simulation.
- Fast Momentum stores OPEN / MARK / CLOSE state in SQLite through `PersistentMomentumPaperEngine`.
- Fast Momentum open position/history can be restored from SQLite after process restart.
- Fast Momentum server scanning no longer requires a Binance account secret: it can use public Binance Demo market data and a conservative fallback taker fee. A Demo API key is optional for authenticated balances/account commission/account-dependent features.
- Fast Momentum runs server-side and is not dependent on keeping the phone PWA open.
- `render.yaml` is not present in `main`.
- Real Binance order execution remains locked.

## Production state now

1. The Linode exists, is RUNNING, and the canonical services have been installed.
2. The one-time production activation has already been performed.
3. The GitHub-main auto-update timer has been observed active on Linode.
4. PR #19 and M4 foundation PR #20 are merged to `main`; Linode should consume main automatically through the existing timer.
5. The merged runtime attempts public HTTPS bootstrap automatically and records the resulting URL for Settings to display.
6. Final external phone/browser verification of that HTTPS URL is still required before declaring public-PWA deployment proven.
7. Fast Momentum persistence/recovery is repository-tested but still requires one real Linode service/reboot smoke test against the production SQLite database.

## Important current limitations

1. Public HTTPS still needs a live external smoke test after Linode has consumed the latest `main`.
2. Fast Momentum persistence/restart recovery still needs one real Linode service/reboot smoke test against the production SQLite database.
3. The older carry paper engine is not persisted/recovered to the same standard as Fast Momentum.
4. Forward-paper evidence is not yet large enough to claim the strategy is profitable.
5. Binance real order submission is not enabled or validated.
6. The current public Demo PWA is not the place to enable real-money execution; authentication/gating must be added before any future live-order layer.
7. M4 does not yet have durable experiment queue/lease/retry behavior, a generic strategy-to-backtest adapter, a separate evidence/provenance table, or automatic screening/promotion gates.
8. AI Strategy Factory, Verified Strategy Knowledge Base, Market Brain selector, portfolio selector, and outcome/drift engine remain later milestones.

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
- server-side scanning continues while the PWA is closed
- public Demo market data is sufficient for Fast paper scanning
- live execution remains locked

## Next tasks — strict order

### Production proof

1. Confirm Linode has automatically consumed the latest `main` and Settings shows the expected release/server build.
2. Confirm automatic public HTTPS succeeded and open the Linode HTTPS PWA from the phone/browser.
3. Smoke-test Home / Chart / Scan / Positions / History / Settings / trade detail from the Linode-served PWA.
4. Perform a real Linode restart/service-restart smoke test and verify Fast Momentum OPEN -> recovery -> MARK/CLOSE plus History persistence.
5. Run forward paper evidence and compare leverage tiers after fees/slippage; do not judge profitability from a handful of trades.
6. Persist/recover the older carry paper engine or remove it if Fast Momentum becomes the only supported paper strategy.

### M4 research-platform development

7. Add explicit experiment queue states plus durable worker claim/lease/retry fields.
8. Add restart recovery and duplicate-work prevention for experiment workers.
9. Add a generic adapter from immutable strategy specs to the existing backtest engine.
10. Add evidence/provenance records with source-data and result hashes.
11. Add automatic cheap-screen -> development -> robustness -> frozen-OOS gates without allowing post-OOS retuning.
12. Only after those controls are proven, add AI-generated strategy hypotheses/parameter families through the controlled experiment interface.

### Future execution work

13. Before any future real-order work, add authenticated control-plane access and a separate execution gate.
14. Build Binance Demo execution validation separately from forward paper; paper simulation alone is not Demo execution proof.
15. Only after the paper/demo/shadow path is restart-safe and statistically acceptable, design and validate a separately gated micro-live layer.

External production-proof tasks and M4 research-platform coding may proceed independently when the external Linode/phone proof cannot be performed from the current development environment. This does not waive the production proof gate and does not authorize live execution.

## Safety invariants

- No API secret is committed to GitHub.
- Withdrawal permission is never required.
- Real orders remain disabled until explicitly implemented and validated.
- The deterministic risk layer has veto authority.
- Server/PWA restart must not erase trade history or active Fast Momentum paper state.
- UI state is not the source of truth; Linode/SQLite is.
- Ports 8000 and 8765 remain loopback-only; public access goes through HTTPS reverse proxy.
- Fast paper may use public market data; account secrets are not a prerequisite for paper scanning.
- Public Demo controls must not be reused as a real-money execution surface.
- Strategy lifecycle eligibility cannot bypass deterministic risk authority.
- Strategy versions are immutable; changed specs require a new version and new evidence.

## Canonical docs

See `docs/LINODE_RUNTIME.md`, `docs/DEPLOYMENT_CHECKLIST.md`, `ARCHITECTURE.md`, `BACKTEST_PROTOCOL.md`, `STRATEGY_SPEC.md`, and `docs/M4_STRATEGY_PLATFORM_FOUNDATION.md`. Historical M1/M2/M3 documents remain evidence records only.
