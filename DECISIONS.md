# EBA Trader — Decisions

This file records current architectural and research-policy decisions. Historical chat statements do not override accepted decisions unless code and this record are deliberately changed together.

## 2026-08-26 — Repository continuity is mandatory

### Decision
GitHub repository state is the shared continuity bridge between ChatGPT branches and AI sessions. Every session reads continuity files and actual code before work, then writes state/handoff back after meaningful work.

### Status
Accepted.

## 2026-08-26 — GitHub main + Linode is the canonical runtime path

### Decision
GitHub `main` is the code source of truth. Linode is the sole active backend/runtime target. Replit and Render are deprecated for EBA Trader backend work.

### Status
Accepted.

## 2026-08-26 — Runtime, research and credential persistence are separate domains

### Decision
Runtime position/trade state remains in `TradeLedger` at `/var/lib/eba-trader/eba_trader.db`. Research strategy versions, experiments, datasets and evidence are separate. Binance Demo credentials are a third encrypted persistence domain.

### Reason
Mass research, experimental lifecycle operations and secret handling must not corrupt runtime positions or each other.

### Status
Accepted.

## 2026-08-26 — Real-money execution remains locked

### Decision
No current M5 work enables real Binance order submission. Deterministic risk has veto authority and future execution promotion requires explicit evidence and a separately validated milestone.

### Status
Accepted.

## 2026-08-26 — Strategy lifecycle evidence is immutable

### Decision
Strategy specifications are immutable per version, experiment evidence is content-addressed/verified, and lifecycle promotion requires evidence. Generic research workers cannot silently skip gates.

### Status
Accepted.

## 2026-08-26 — M5 AI Strategy Factory uses constrained DSL, not arbitrary code

### Decision
AI-generated hypotheses are constrained structured data validated against an approved feature registry and bounded parameter families. Arbitrary generated production Python/expression execution is not an accepted generation path.

### Status
Accepted.

## 2026-08-26 — Footprint/order flow is a research feature family, not assumed edge

### Decision
Executed-trade footprint features (buy/sell volume, delta, delta ratio, CVD, POC) are candidate features that must prove incremental value against candle-only baselines. They are derived from raw executed events, never chart-image interpretation. Resting LOB liquidity is a separate future dataset.

### Status
Experimental feature family; architecture decision accepted.

## 2026-08-26 — Gapped or tampered historical order-flow data fails closed

### Decision
Historical aggregate-trade/order-flow datasets with duplicate/conflicting IDs, backward timestamps, integrity hash mismatch or unresolved sequence gaps are not research-ready.

### Status
Accepted.

## 2026-08-26 — Development ranking cannot unlock frozen OOS

### Decision
Cheap screening, development comparison and survivor ranking are triage only. A development win-rate/profitability improvement is insufficient to open frozen OOS, paper, demo, shadow or live stages.

### Status
Accepted.

## 2026-08-26 — Lifecycle ordering mismatch required deliberate reconciliation

### Decision
Do not bypass the historical code path `GENERATED -> BACKTESTED -> OOS_VERIFIED -> ROBUSTNESS_VERIFIED`. Accepted methodology requires robustness before frozen OOS, so storage semantics and transition rules had to be migrated deliberately rather than changing enum order in place.

### Status
Resolved by the lifecycle-policy-v2 design below; historical policy v1 remains readable but promotion-frozen.

## 2026-08-26 — Linode auto-deploy can self-heal HTTPS without making CA/DNS part of rollback

### Decision
Runtime deploy success is gated by local systemd/API health. Public HTTPS bootstrap may retry independently; temporary DNS/CA failure does not roll back an otherwise healthy runtime deployment.

### Status
Accepted.

## 2026-08-26 — Order-flow acquisition is venue-specific and causal

### Decision
Historical order-flow acquisition records exact venue and request/range provenance. USD-M futures is the current BTCUSDT perpetual research venue. Spot remains an explicit alternative dataset and must not be silently mixed with futures flow.

A closed footprint `[t-step,t)` may be used by the candle opening at `t`; still-forming `[t,t+step)` data cannot enter that same candle decision.

### Status
Accepted in PR #30.

## 2026-08-26 — Order-flow ablations use the same aligned dataset and execution assumptions

### Decision
The candle-only arm and candle+order-flow arm consume the exact same causally aligned feature dataset. EMA/capital/fees/slippage/trade-start/exits remain identical; only allowlisted already-available Delta/CVD entry filters may differ.

A permissive treatment is an invariant/sanity check and should reproduce the candle-only control when its gate does not reject entries.

### Status
Accepted in PR #31/#34.

## 2026-08-26 — Research / AI Lab is read-only observability

### Decision
The PWA Research / AI Lab may display repository state and read-only research-store summaries but has no mutation, lifecycle-promotion, risk, OOS-unlock or execution authority.

### Status
Accepted in PR #32.

## 2026-08-26 — M5 ablation orchestration uses one deterministic control plus bounded treatments

### Decision
A development order-flow ablation emits one deduplicated candle-only baseline plus bounded deterministic order-flow treatments. Treatment fan-out is capped, duplicate/empty/non-finite gates fail closed, and the stage is fixed to development.

### Status
Accepted and merged in PR #34.

## 2026-08-26 — Real M5 BTCUSDT ablations require venue-matched USD-M candles and order flow

### Decision
Real BTCUSDT perpetual development experiments require Binance USD-M futures candles and USD-M aggregate trades end-to-end, with request provenance, exact coverage and immutable content links. Spot/futures mixing is rejected.

### Status
Accepted and merged in PR #35.

## 2026-08-26 — Binance Demo credentials persist only in an encrypted server vault

### Decision
The PWA may accept a Binance **Demo** key/secret once for test-before-save encrypted persistence. The secret is never returned to browser JavaScript, written to browser persistent storage, committed to Git or pasted into chat. Live/non-Binance credentials are outside this milestone.

### Status
Accepted and merged in PR #36. Real production save is now observed in the PWA; no-paste reconnect after a real restart remains pending.

## 2026-08-27 — Linode deployment recovery is fail-closed and stays outside PWA authority

### Decision
A stuck Linode deployment is repaired by root-side tooling that refuses dirty checkouts, records diagnostics and restores timer operation. The browser does not gain systemd/deployment authority.

### Status
Accepted in PR #37 and production-verified.

## 2026-08-27 — High-frequency market events are data, not normal INFO diagnostics

### Decision
`eba-binance-data` must keep subscriptions active but must not emit every raw `QuoteTick`/`TradeTick` to normal INFO logs. Research datasets come from explicit acquisition/materialization pipelines, not syslog/journal reconstruction.

### Status
Accepted in PR #38 and production-verified.

## 2026-08-27 — Production journald protection is a versioned host-safety invariant

### Decision
The production journald policy is `SystemMaxUse=250M`, `SystemKeepFree=1G`, `MaxRetentionSec=7day`. It is versioned in `deploy/journald/eba-trader.conf` and provisioned by both install/update paths.

Application rollback does not intentionally remove this policy because disk-exhaustion protection is a host invariant, not application business state.

### Reason
The original manual-only fix left rebuild/new-server continuity risk after a ~18 GB logging incident. Reproducible provisioning closes that gap.

### Status
Accepted and merged in PR #40. Production PWA build `8876bc2` proves #40 deployed; direct server-internal verification of the actual journald values remains pending.

## 2026-08-27 — Long-running Linode research state lives outside the Git checkout

### Decision
Production research DB, datasets and immutable evidence use `/var/lib/eba-trader/research/...`; local development may still use `artifacts/research/...`. Runtime `TradeLedger` remains separate.

Existing Linode env files are upgraded idempotently with default research paths without overwriting explicit operator choices.

### Reason
The auto-deployer correctly refuses dirty checkouts. Research artifacts inside `/opt/Eba-Trader` would turn valid research work into a deployment blocker.

### Status
Accepted and merged in PR #40. Direct server-internal path/timer proof remains pending.

## 2026-08-27 — Persistent research worker is bounded and has no promotion/execution authority

### Decision
The Linode research worker is a oneshot queue consumer triggered approximately once per minute. It is bounded to eight jobs per invocation, CPU 50%, memory 512 MB and write access to the research namespace. It cannot create arbitrary strategy code, open frozen OOS, promote lifecycle by itself or submit exchange orders.

### Reason
24/7 research automation is useful only if resource usage and authority are explicitly bounded on the 1 GB Nanode runtime.

### Status
Accepted and merged in PR #40.

## 2026-08-27 — Real M5 ablation execution fails closed before queue emission

### Decision
`eba-m5-real-ablation` may emit development experiments only after verifying the PR #35 workflow schema, USD-M venue, symbol/interval/time range, contained relative dataset path, feature CSV SHA-256, matching feature manifest and no first-cycle frozen-OOS overlap.

The versioned initial Delta/CVD gate set is an experiment policy, not a promotion policy. The one-command runner may build, queue and execute M4 research jobs but cannot open frozen OOS or execution.

### Status
Accepted and merged in PR #40. First real development run remains pending.

## 2026-08-27 — Lifecycle policy v2 requires robustness before frozen OOS

### Decision
New/current research uses lifecycle policy v2:

`GENERATED -> BACKTESTED -> ROBUSTNESS_VERIFIED -> OOS_VERIFIED -> PAPER_CANDIDATE -> PAPER_VERIFIED -> DEMO_CANDIDATE -> DEMO_VERIFIED -> SHADOW_VERIFIED -> MICRO_LIVE_ELIGIBLE -> LIVE_ELIGIBLE -> LIVE_ACTIVE`

A v2 strategy cannot transition directly from `BACKTESTED` to `OOS_VERIFIED`. Robustness fan-out requires v2 `BACKTESTED`, and an immutable passing robustness verdict may promote only to `ROBUSTNESS_VERIFIED`. OOS still requires a separate later evidence-bearing transition.

### Legacy migration rule
Existing M4 SQLite rows predate lifecycle policy versioning. They are not silently reinterpreted:

- legacy `GENERATED`, `BACKTESTED` and `RETEST_REQUIRED` rows may adopt v2 safely because they have not already consumed frozen OOS under the old order;
- legacy rows at `OOS_VERIFIED` or later remain policy v1 and promotion-frozen;
- a legacy post-OOS row must enter `RETEST_REQUIRED`, explicitly upgrade to v2, produce fresh development evidence to return to `BACKTESTED`, then pass fresh robustness before OOS can be opened again.

### Reason
Changing enum order alone would make persisted `OOS_VERIFIED` records appear valid under a different methodology. Policy versioning preserves historical meaning, prevents silent state reinterpretation and enforces robustness-before-OOS prospectively.

### Related implementation
- `src/eba_trader/lifecycle.py`
- `src/eba_trader/research_store.py`
- `src/eba_trader/robustness_fanout.py`
- `src/eba_trader/robustness_verdict.py`
- lifecycle and legacy-migration regression tests

### Status
Accepted design; implemented and CI-green in PR #41 candidate. Frozen OOS remains locked until actual v2 robustness evidence exists.
