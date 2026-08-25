# EBA Trader — Project State

_Last updated: 2026-08-26 (Asia/Ulaanbaatar)_

This is the authoritative cross-chat continuation record. If older chat text, old deployment notes, screenshots, old PRs, or old branches conflict with this file, this file wins.

## Current goal

Run EBA Trader as a restart-safe 24/7 Linode system, validate strategies with paper trading first, persist every trade, expose clear runtime state to the PWA, and keep real-money execution locked until separately proven.

M4 research control plane is complete. M5 AI Strategy Factory is in progress. M5 now includes a constrained strategy DSL, bounded family generation, duplicate control, cheap screening and a reproducible Order Flow / Footprint historical-data foundation.

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

Merged M5 milestones:

- PR #25 — Order Flow / Footprint numerical feature foundation
- PR #26 — constrained strategy DSL and deterministic candidate emission
- PR #27 — bounded family templates, near-duplicate guard, cheap screening and survivor ranking
- PR #28 — historical aggregate-trade dataset integrity/provenance and closed footprint windows

### Strategy-generation control plane

M5 now has:

1. An approved feature registry separating enabled candle/order-flow features from reserved disabled features.
2. A constrained LONG/SHORT strategy-hypothesis DSL with numeric comparisons only; arbitrary Python/expression execution is prohibited.
3. Structural hypothesis fingerprints that ignore free-text rationale so cosmetic AI explanations do not create new strategies.
4. Exact and near-duplicate suppression.
5. Bounded deterministic parameter-family expansion with a hard 500-variant cap.
6. Deterministic candidate IDs and an M5 emitter into the existing M4 `ResearchStore`/`ExperimentQueue`.
7. Initial bounded candle-only `ema_momentum` and candle+order-flow `ema_orderflow_momentum` templates.
8. Static cheap-screen rejection for excessive complexity/fan-out.
9. Deterministic survivor ranking for PASSED development experiments; ranking is triage only and has no lifecycle authority.

### Order Flow / Footprint research data

Order flow remains a candidate feature family, not a trusted signal. The current implementation provides:

1. Typed executed `TradeEvent` and aggressor-side contracts.
2. Binance aggregate-trade parsing using `m` semantics: buyer-is-maker means seller was aggressive; otherwise buyer was aggressive.
3. Deterministic aggregate-trade normalization with duplicate/conflict/backward-timestamp rejection.
4. Sequence-gap accounting. Gapped datasets may be cached for diagnosis but `require_research_ready()` rejects them for research until repaired/re-downloaded.
5. Canonical JSONL content-addressed records and manifest provenance with SHA-256 verification.
6. Deterministic fixed-width `[start,end)` footprint windows.
7. Buy volume, sell volume, delta, delta ratio, total volume, trade count, price-bucket POC and cumulative delta.
8. Empty windows retained as neutral rows and exact range/window alignment required.
9. Explicit anti-leakage rule: completed footprint values are unavailable before `end_ms`.

Footprint features are derived from raw market events, never chart pixels. Executed flow and resting order-book liquidity remain separate datasets. No claim is made that footprint identifies all hidden/institutional orders.

### Next M5 implementation order

1. Add a paginated historical Binance aggregate-trade acquisition layer that fills/retries ranges until sequence integrity passes.
2. Join research-ready footprint windows to candle datasets by timestamp with explicit feature availability time.
3. Add an allowlisted order-flow backtest adapter that consumes only approved causal features.
4. Run controlled candle-only vs candle+order-flow ablation families through M4 development/robustness gates.
5. Add stacked/diagonal imbalance, absorption/exhaustion and price/delta divergence only after explicit numerical definitions/tests.
6. Add separately reconstructed limit-order-book depth/imbalance only after event-sequence integrity is proven.
7. Add cheap-screen -> development-screen orchestration and survivor promotion workflow without opening frozen OOS.
8. Reconcile lifecycle validation order before separately authorized frozen-OOS orchestration.
9. Later expand validated survivors into Verified Strategy KB, forward-paper factory, Binance Demo execution lab, Market Brain/Selector, portfolio selection and outcome/drift engine.

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
- Incomplete/gapped order-flow datasets cannot be used for research.
- AI hypotheses cannot execute arbitrary code or directly reach exchange execution.

## Canonical docs

See `docs/LINODE_RUNTIME.md`, `docs/DEPLOYMENT_CHECKLIST.md`, `ARCHITECTURE.md`, `BACKTEST_PROTOCOL.md`, `STRATEGY_SPEC.md`, M4 documents under `docs/`, `docs/M5_ORDER_FLOW_FOUNDATION.md`, `docs/M5_STRATEGY_DSL.md`, `docs/M5_FAMILY_SCREENING.md`, and `docs/M5_ORDER_FLOW_DATASET.md`. Historical M1/M2/M3 documents remain evidence records only.
