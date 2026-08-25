# EBA Trader — Project State

_Last reconciled: 2026-08-26 (Asia/Ulaanbaatar)_
_Verified through GitHub `main` PR #34 merge `ee5fd3f16ed5ad88ca928ced0efdb5790cbf568d`._

This is the primary cross-chat continuation summary. Actual current implementation/config/tests and Git history override stale text.

## Current goal

Operate EBA Trader as a restart-safe 24/7 Linode paper/research system, build a controlled AI Strategy Factory on top of the M4 evidence platform, test whether order-flow/footprint features add incremental edge over candle-only baselines, expose research/runtime progress in the phone-first PWA, and keep real-money execution locked until a separate evidence chain proves it.

## Current stage

- Research platform: **M4 COMPLETE**.
- AI Strategy Factory: **M5 IN PROGRESS**.
- Continuity system: **INSTALLED / ENFORCED IN CI**.
- Current M5 frontier: materialize a real BTCUSDT USD-M development feature dataset, then execute the deterministic candle-only vs delta/CVD ablation batch through M4.
- Historical order-flow acquisition, missing-ID repair, causal candle alignment, feature-dataset materialization and allowlisted ablation adapters: **IMPLEMENTED / MERGED through #31**.
- Deterministic ablation orchestration: **MERGED in #34**.
- Research / AI Lab PWA: **MERGED in #32**; read-only observability only.
- Scanner heartbeat UI: **MERGED in #33**.
- Real-money execution: **LOCKED**.
- Frozen OOS automation: **LOCKED pending lifecycle-order reconciliation**.

## Source of truth and active infrastructure

- Repository: `enkhbat194/EBA-Trader`
- Code source of truth: GitHub `main`
- Active runtime target: Akamai/Linode Nanode 1 GB, Singapore 2, Ubuntu 24.04 LTS
- Server repository path: `/opt/Eba-Trader`
- Persistent runtime DB: `/var/lib/eba-trader/eba_trader.db`
- Market-data service: `eba-binance-data.service`
- Runtime API service: `eba-runtime-api.service` on `127.0.0.1:8765`
- PWA/web service: `eba-web.service` on `127.0.0.1:8000` behind nginx/Let's Encrypt HTTPS
- Public PWA verified on 2026-08-26: `https://eba-trader-172-236-150-62.sslip.io/`
- Auto deploy: `eba-auto-update.timer`; exact `origin/main`, dirty-checkout refusal, service/API health checks and rollback are implemented in `scripts/update_linode_runtime.sh`
- Replit/Render: deprecated EBA Trader backend/runtime paths

## Completed research milestones

### M4 — complete

Merged PRs #20-#24 provide immutable strategy versions, deterministic experiment IDs, restart-safe queue/leases, allowlisted workers, content-addressed evidence, declarative gates and bounded robustness evidence. Generic workers do not unlock frozen OOS or execution.

### M5 — completed foundation so far

- #25 order-flow/footprint research foundation.
- #26 constrained strategy DSL, approved feature registry, bounded deterministic parameter expansion and M4 candidate emission.
- #27 strategy-family templates, near-duplicate guard, cheap screening and deterministic survivor ranking.
- #28 historical Binance aggregate-trade normalization/cache, sequence/integrity gate and deterministic footprint windows.
- #30 venue-aware historical aggregate-trade acquisition, request/range provenance, missing-ID repair and causal closed-footprint/candle alignment.
- #31 causal feature-dataset materialization plus allowlisted candle-only/order-flow backtest adapters on the exact same aligned feature CSV.
- #32 phone-first Research / AI Lab PWA dashboard.
- #33 carry-label clarification and Fast Momentum heartbeat observability.
- #34 deterministic one-control-to-many-treatment order-flow ablation orchestration.

Enabled order-flow features: executed buy/sell volume, delta, delta ratio, CVD and POC price. Stacked imbalance, absorption, exhaustion and LOB depth imbalance remain disabled/unimplemented.

## Current implementation reality

### M5 Strategy Factory and ablation

AI hypotheses are constrained structured data. Unknown/disabled features fail closed. Parameter fan-out is bounded and candidates are deterministically identified/emitted into the M4 research store/queue.

PR #34 adds `M5OrderFlowAblationOrchestrator`:

- one deduplicated `ema_feature_baseline_v1` control experiment;
- bounded deterministic `ema_orderflow_v1` treatment variants;
- exact shared dataset identity, symbol/time window, EMA parameters, initial capital, fees, slippage and trade-start semantics;
- only delta-ratio/CVD gate parameters may differ;
- treatment fan-out capped at 64;
- duplicate, empty or non-finite gates fail closed;
- gate input ordering does not alter deterministic batch identity;
- fixed stage `m5_orderflow_ablation_dev`; no OOS or lifecycle-promotion authority.

### Order flow / footprint

Footprint is derived from raw executed market events, not chart pixels. Historical datasets are content-addressed and validated for duplicate/conflicting IDs, timestamp ordering, file hash and sequence gaps. Unresolved gaps are not backtest-ready.

USD-M Futures is the default venue for BTCUSDT perpetual research. Closed footprint `[t-step,t)` is available to the candle opening at `t`; still-forming same-candle flow is never injected into that decision.

### Runtime / PWA

- Fast Momentum runs server-side every ~15 seconds and remains paper-only.
- `TradeLedger` runtime persistence is separate from M4/M5 research state.
- Fast Momentum supports persistent OPEN/MARK/CLOSE state/history.
- The PWA consumes server truth rather than browser memory.
- Research / AI Lab and scanner heartbeat are read-only observability.

## Production proof — manual evidence on 2026-08-26

Confirmed:

- Linode checkout consumed GitHub `main` through state commit `050cd9be203a09aca95a152d7102fa280c397ee7`.
- nginx + Certbot configured `eba-trader-172-236-150-62.sslip.io`.
- External iPhone access to the HTTPS PWA succeeded.
- Home, Scan and Settings displayed live server state; Binance Demo connection and Fast Paper scanner were observed operating.

Still unproven:

- complete smoke test of Chart / Positions / History / Research / trade detail;
- active Fast Momentum paper position surviving a service/server restart and later MARK/CLOSE;
- final disposition of the older carry paper engine.

## Known architecture issue

Current lifecycle path is:

`GENERATED -> BACKTESTED -> OOS_VERIFIED -> ROBUSTNESS_VERIFIED -> PAPER_CANDIDATE -> ...`

Desired methodology conceptually wants robustness before opening frozen OOS. Do not bypass the machine lifecycle; redesign/migrate/test it before automated frozen-OOS orchestration.

## Immediate Next

1. Add a CLI/workflow to materialize the real development feature dataset from candle CSV + verified order-flow/acquisition manifests.
2. Run controlled BTCUSDT USD-M development ablations through M4 queue/worker/evidence/gates.
3. Persist/rank survivors only for triage; do not open frozen OOS from ranking results.
4. In parallel, finish remaining production smoke/restart-recovery proof.

## Important constraints

- No API secrets in Git; withdrawal permission is never required.
- Deterministic risk has veto authority.
- Runtime state must survive Git pulls, browser refreshes and process/server restarts.
- Strategy versions/evidence are immutable.
- AI strategy generation does not execute arbitrary generated Python.
- Order-flow executed trades and resting LOB liquidity are separate data domains.
- Order-flow dataset gaps fail closed.
- Spot and USD-M futures order flow are separate experiment datasets.
- Same-candle still-forming footprint data cannot be used in candle decisions.
- A development win-rate increase is not promotion evidence.
- Generic research workers and ablation orchestration cannot open frozen OOS or real execution.

## Validation status

- PRs #29-#33 passed their full regression/Ruff/deployment/runtime/continuity gates before merge.
- PR #34 final head passed Continuity guard, Linode runtime checks and Linode production bundle before squash merge at `ee5fd3f16ed5ad88ca928ced0efdb5790cbf568d`.
- External HTTPS/latest-main proof is manually established; restart-recovery proof remains open.

## Continuity system

Canonical continuity files are `AGENTS.md`, `PROJECT_STATE.md`, `ARCHITECTURE.md`, `DECISIONS.md`, `TODO.md`, `CHANGELOG.md`, `SESSION_HANDOFF.md`, and `docs/CONTINUITY_PROTOCOL.md`. Every meaningful AI/coding session must update them when state changes.
