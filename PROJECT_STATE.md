# EBA Trader — Project State

_Last updated: 2026-08-26 (Asia/Ulaanbaatar)_

This is the authoritative cross-chat continuation record. If older chat text, old deployment notes, screenshots, old PRs, or old branches conflict with this file, this file wins.

## Current goal

Run EBA Trader as a restart-safe 24/7 Linode system, validate strategies with paper trading first, persist every trade, expose clear runtime state to the PWA, and keep real-money execution locked until separately proven.

M4 research control plane is complete. M5 AI Strategy Factory is now in progress. M5 includes an Order Flow / Footprint research feature layer so generated strategies can be tested with executed-trade microstructure data instead of relying only on candle-derived indicators.

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

M4 provides immutable strategy versions, deterministic experiment IDs, a restart-safe experiment queue, allowlisted generic backtest workers, content-addressed evidence/provenance, declarative screening gates, bounded robustness fan-out, aggregate robustness verdicts and evidence-required lifecycle transitions. Generic M4 workers do not unlock frozen OOS or execution.

## M5 AI Strategy Factory — IN PROGRESS

### Order Flow / Footprint foundation — merged PR #25

Order flow is a research feature family, not a trusted signal. PR #25 adds:

1. Typed executed `TradeEvent` and aggressor-side contracts.
2. Deterministic closed-window price-level footprint aggregation.
3. Buy volume, sell volume, delta, delta ratio, total volume and trade count.
4. Price-level bid/ask-style executed-flow buckets and POC (maximum traded-volume bucket).
5. Cumulative volume delta helper.
6. Fail-closed event/window validation and deterministic tests.
7. Canonical `docs/M5_ORDER_FLOW_FOUNDATION.md` with anti-leakage rules and controlled ablation plan.

Planned feature expansion:

- stacked/diagonal imbalance candidates;
- absorption/exhaustion candidates;
- price/delta divergence;
- historical trade-flow ingestion/cache with source hashes and integrity checks;
- separately reconstructed limit-order-book depth/imbalance features after sequence integrity is proven.

Footprint features are derived from raw market events, never chart pixels. Executed trade flow and resting order-book liquidity remain separate datasets. No claim is made that footprint identifies all hidden/institutional orders.

Required ablation comparisons include candle baseline versus baseline+delta/CVD, footprint imbalance, absorption/exhaustion, LOB imbalance and approved combined features. A higher development win rate is not sufficient; incremental value must survive fees/slippage, robustness, frozen OOS and forward paper evidence.

### Next M5 implementation order

1. Define constrained strategy-hypothesis schema/DSL; AI outputs schema data, not arbitrary production code.
2. Define an approved feature registry including candle and order-flow feature names.
3. Add strategy-family templates and parameter-family generation.
4. Add hypothesis validation and duplicate/near-duplicate detection.
5. Generate deterministic experiment families into the M4 queue.
6. Add historical trade-flow ingestion/cache and provenance, then connect approved footprint features to experiments.
7. Add cheap-screen -> development-screen orchestration and survivor ranking without opening frozen OOS.
8. Run controlled candle-vs-order-flow ablation experiments.
9. Reconcile lifecycle validation order before separately authorized frozen-OOS orchestration.
10. Later expand validated survivors into Verified Strategy KB, forward-paper factory, Binance Demo execution lab, Market Brain/Selector, portfolio selection and outcome/drift engine.

## Validation-order issue

Current lifecycle is `GENERATED -> BACKTESTED -> OOS_VERIFIED -> ROBUSTNESS_VERIFIED -> ...`, while desired research workflow conceptually performs robustness before opening frozen OOS. Do not bypass lifecycle states manually. M5/M6 must reconcile this before automated frozen-OOS promotion.

## Existing runtime

- Binance public market data has been observed running on Linode through NautilusTrader.
- Canonical services are `eba-binance-data.service`, `eba-runtime-api.service`, and `eba-web.service`.
- SQLite runtime `TradeLedger` remains separate from research state.
- `eba-auto-update.timer` checks GitHub `main` every five minutes and exact-main deployment has health/rollback support.
- PWA source is in `web/`.
- Fast Momentum supports LONG/SHORT BTCUSDT perpetual paper decisions and persistent OPEN/MARK/CLOSE state.
- Real Binance order execution remains locked.

## Production proof still pending

Repository CI does not prove these external items:

1. Confirm Linode consumed latest `main`.
2. Confirm public HTTPS from an external phone/browser.
3. Smoke-test Home / Chart / Scan / Positions / History / Settings / trade detail.
4. Perform one real Linode restart/service-restart and verify Fast Momentum `OPEN -> recovery -> MARK/CLOSE` plus History persistence against production SQLite.
5. Continue forward-paper evidence collection; profitability is not proven from a handful of trades.
6. Persist/recover the older carry paper engine or retire it.

External production proof and research development may proceed independently, but this does not waive the proof gate.

## Safety invariants

- No API secret is committed to GitHub.
- Withdrawal permission is never required.
- Real orders remain disabled until explicitly implemented and validated.
- Deterministic risk has veto authority.
- Runtime restart must not erase trade history or active Fast Momentum paper state.
- UI is not the source of truth; Linode/SQLite is.
- Public Demo controls are not a real-money execution surface.
- Strategy versions are immutable; changed specs require new versions/evidence.
- Generic workers cannot open frozen first-cycle OOS.
- Robustness verdicts do not silently promote OOS/live lifecycle state.
- Order-flow features cannot bypass lifecycle/risk gates.

## Canonical docs

See `docs/LINODE_RUNTIME.md`, `docs/DEPLOYMENT_CHECKLIST.md`, `ARCHITECTURE.md`, `BACKTEST_PROTOCOL.md`, `STRATEGY_SPEC.md`, M4 documents under `docs/`, and `docs/M5_ORDER_FLOW_FOUNDATION.md`. Historical M1/M2/M3 documents remain evidence records only.
