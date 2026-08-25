# EBA Trader — Project State

_Last updated: 2026-08-26 (Asia/Ulaanbaatar)_

This is the authoritative cross-chat continuation record. If older chat text, old deployment notes, screenshots, old PRs, or old branches conflict with this file, this file wins.

## Current goal

Run EBA Trader as a restart-safe 24/7 Linode system, validate strategies with paper trading first, persist every trade, expose clear runtime state to the PWA, and keep real-money execution locked until separately proven.

The M4 research control plane is now complete. The next research milestone is M5: AI Strategy Factory built on the controlled M4 interfaces rather than direct AI-to-live code.

## Source of truth and infrastructure

- Repository: `enkhbat194/EBA-Trader`
- Source of truth: GitHub `main`
- Sole active runtime target: Akamai/Linode Nanode 1 GB, Singapore 2, Ubuntu 24.04 LTS
- Server repo path: `/opt/Eba-Trader`
- Persistent runtime state: `/var/lib/eba-trader/eba_trader.db`
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
- BestCode integration remains separate from EBA Trader.

## M4 research platform — COMPLETE

Merged milestones:

- PR #20 — strategy-platform foundation
- PR #21 — restart-safe experiment queue and worker leases
- PR #22 — generic backtest worker and immutable evidence
- PR #23 — development screening gates and immutable verdicts
- PR #24 — bounded robustness fan-out and aggregate verdicts

M4 now provides:

1. Generic strategy decisions: `LONG`, `SHORT`, `EXIT`, `NO_TRADE`; historical `Decision.BUY` remains only a temporary LONG compatibility alias.
2. Symmetric deterministic LONG/SHORT risk sizing.
3. Machine-enforced `StrategyLifecycle` with evidence-required promotion transitions.
4. Separate `ResearchStore` SQLite control plane; runtime `TradeLedger` positions remain isolated.
5. Immutable strategy versions; changed specs require a new version.
6. Deterministic experiment IDs from strategy/version/stage/parameters/dataset.
7. Restart-safe `ExperimentQueue` with transactional claims, worker leases, retries, max-attempt handling, expired-lease recovery and duplicate-work prevention.
8. Fail-closed `BacktestAdapterRegistry` with initial allowlisted `ema_trend_v1` adapter wrapping the existing backtester.
9. Exact dataset interval/window validation and default frozen first-cycle OOS block in the generic worker path.
10. Immutable content-addressed research evidence with dataset/spec/source hashes and SQLite evidence index.
11. `ResearchBacktestWorker` and `eba-research-worker` CLI for queue -> backtest -> evidence -> result execution.
12. Versioned declarative `GateSet` development screening and immutable screening verdicts.
13. Promotion from `GENERATED -> BACKTESTED` only when declared development gates pass and evidence integrity matches.
14. Bounded `RobustnessPlan`/`RobustnessBatch` fan-out for parameter-neighborhood and fee/slippage cost-stress scenarios.
15. Hard 250-job robustness plan cap and fixed-strategy-field override protection.
16. Immutable aggregate robustness verdict requiring every scenario experiment to be completed and pass its declared gates.

M4 deliberately does **not** unlock frozen OOS, Binance Demo order execution, shadow/live execution, or later lifecycle stages.

## Validation-order issue to resolve before automated OOS promotion

The current lifecycle machine is:

```text
GENERATED -> BACKTESTED -> OOS_VERIFIED -> ROBUSTNESS_VERIFIED -> ...
```

The desired research workflow conceptually performs robustness checks before opening frozen OOS. M4 therefore records robustness evidence without force-promoting lifecycle state. M5/M6 must explicitly reconcile the canonical validation order before adding automated frozen-OOS orchestration. Do not bypass this by manually skipping lifecycle states.

## Existing research/evidence core

- Binance public historical downloader and integrity gates exist.
- Backtest, cost, walk-forward, regime and OOS-guard tooling exists.
- Historical Trend V2 rejection remains valid evidence that the framework can reject weak strategies.
- Existing historical research files are evidence, not deployment instructions.

## Linode/runtime core

- Binance public market data has been observed running on Linode through NautilusTrader.
- `eba-binance-data.service`, `eba-runtime-api.service`, and `eba-web.service` are canonical runtime services.
- SQLite-backed `TradeLedger` exists outside the Git checkout.
- Runtime API exposes health, positions and events.
- `scripts/install_linode_runtime.sh` is the canonical first-install script.
- `scripts/update_linode_runtime.sh` supports exact-main automatic deployment, health verification and rollback.
- `eba-auto-update.timer` has been observed active and checks GitHub `main` every five minutes.
- `scripts/bootstrap_linode_public_https.sh` attempts Nginx + Certbot HTTPS with sslip.io/nip.io fallback.
- HTTPS failure is non-fatal to trading runtime and can be retried by deployment automation.

## PWA and Fast Momentum

- PWA/dashboard source is in `web/` on `main`.
- Fast Momentum supports LONG and SHORT BTCUSDT perpetual paper decisions.
- Fast Momentum stores OPEN / MARK / CLOSE state in SQLite through `PersistentMomentumPaperEngine`.
- Open positions/history can be restored from SQLite after process restart in repository tests.
- Server-side scanning can use public Binance Demo market data without requiring account secrets.
- Real Binance order execution remains locked.

## Production proof still pending

These are **not** complete and must not be inferred from repository CI:

1. Confirm Linode has consumed the latest `main`.
2. Confirm public HTTPS from an external phone/browser.
3. Smoke-test Home / Chart / Scan / Positions / History / Settings / trade detail on the Linode-served PWA.
4. Perform one real Linode restart/service-restart and verify Fast Momentum `OPEN -> recovery -> MARK/CLOSE` plus History persistence against the production SQLite database.
5. Continue forward-paper evidence collection; profitability is not proven from a handful of trades.
6. Persist/recover the older carry paper engine or retire it if Fast Momentum is the only supported paper strategy.

External production proof and research development may proceed independently when external Linode/phone access is unavailable, but this does not waive the proof gate.

## Next research milestone — M5 AI Strategy Factory

Strict implementation order:

1. Define a constrained strategy-hypothesis schema/DSL; AI must output schema data, not arbitrary production code.
2. Add strategy-family templates and parameter-family generation.
3. Add hypothesis validation and duplicate/near-duplicate detection.
4. Generate deterministic experiment families into the existing M4 queue.
5. Add cheap-screen -> development-screen orchestration using existing immutable evidence/gates.
6. Add survivor ranking without opening frozen OOS.
7. Reconcile lifecycle validation order and then implement separately authorized frozen-OOS orchestration.
8. Only after validated survivors exist, expand to Verified Strategy KB, forward-paper factory, Binance Demo execution lab, Market Brain/Selector, portfolio selection and outcome/drift engine.

## Safety invariants

- No API secret is committed to GitHub.
- Withdrawal permission is never required.
- Real orders remain disabled until explicitly implemented and validated.
- The deterministic risk layer has veto authority.
- Server/PWA restart must not erase trade history or active Fast Momentum paper state.
- UI state is not the source of truth; Linode/SQLite is.
- Ports 8000 and 8765 remain loopback-only; public access goes through HTTPS reverse proxy.
- Fast paper may use public market data; account secrets are not required for paper scanning.
- Public Demo controls must not be reused as a real-money execution surface.
- Strategy lifecycle eligibility cannot bypass deterministic risk authority.
- Strategy versions are immutable; changed specs require new versions and new evidence.
- Generic M4 workers cannot open the frozen first-cycle OOS path.
- Robustness verdicts do not silently promote OOS/live lifecycle state.

## Canonical docs

See `docs/LINODE_RUNTIME.md`, `docs/DEPLOYMENT_CHECKLIST.md`, `ARCHITECTURE.md`, `BACKTEST_PROTOCOL.md`, `STRATEGY_SPEC.md`, `docs/M4_STRATEGY_PLATFORM_FOUNDATION.md`, `docs/M4_EXPERIMENT_QUEUE.md`, `docs/M4_BACKTEST_WORKER_EVIDENCE.md`, `docs/M4_DEVELOPMENT_SCREENING.md`, and `docs/M4_ROBUSTNESS_FANOUT.md`. Historical M1/M2/M3 documents remain evidence records only.
