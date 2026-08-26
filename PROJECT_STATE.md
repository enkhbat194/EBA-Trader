# EBA Trader — Project State

_Last reconciled: 2026-08-26 (Asia/Ulaanbaatar)_
_Verified through GitHub `main` PR #34 merge `ee5fd3f16ed5ad88ca928ced0efdb5790cbf568d`; PR #35 real USD-M feature-dataset workflow is implemented and under final validation._

This is the primary cross-chat continuation summary. Actual current implementation/config/tests and Git history override stale text.

## Current goal

Operate EBA Trader as a restart-safe 24/7 Linode paper/research system, build a controlled AI Strategy Factory on top of the M4 evidence platform, test whether order-flow/footprint features add incremental edge over candle-only baselines, expose research/runtime progress in the phone-first PWA, and keep real-money execution locked until a separate evidence chain proves it.

## Current stage

- Research platform: **M4 COMPLETE**.
- AI Strategy Factory: **M5 IN PROGRESS**.
- Continuity system: **INSTALLED / ENFORCED IN CI**.
- Deterministic order-flow ablation orchestration: **MERGED in #34**.
- Real USD-M development feature-dataset workflow: **IMPLEMENTED in PR #35 pending final CI/merge**.
- Next research frontier after #35: build a real BTCUSDT USD-M development dataset on Linode, then execute the deterministic candle-only vs delta/CVD ablation batch through M4.
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
- #35 adds venue-aware candle acquisition plus one-command verified USD-M candle+order-flow feature-dataset build; final merge is pending.

Enabled order-flow features: executed buy/sell volume, delta, delta ratio, CVD and POC price. Stacked imbalance, absorption, exhaustion and LOB depth imbalance remain disabled/unimplemented.

## Current implementation reality

### M5 Strategy Factory and ablation

AI hypotheses are constrained structured data. Unknown/disabled features fail closed. Parameter fan-out is bounded and candidates are deterministically identified/emitted into the M4 research store/queue.

`M5OrderFlowAblationOrchestrator` emits one deduplicated `ema_feature_baseline_v1` control and bounded deterministic `ema_orderflow_v1` treatments. All arms share dataset identity, symbol/time window, EMA parameters, initial capital, fees, slippage and trade-start semantics; only allowlisted delta/CVD thresholds differ. Fan-out is capped at 64 and the stage is fixed to development only.

### Real USD-M feature dataset workflow

PR #35 prevents Spot/Futures contamination by making the real M5 pipeline venue-explicit end to end:

- Binance USD-M futures candles are acquired from the futures kline endpoint with request provenance and exact interval coverage validation;
- Binance USD-M `aggTrades` cover one prior footprint window plus the development candle range;
- aggregate-trade gaps are repaired and unresolved integrity errors fail closed;
- candle and order-flow manifests are content-linked and hash verified;
- closed footprint `[t-step,t)` is aligned to the candle opening at `t`;
- `eba-build-orderflow-features` emits an immutable feature CSV/workflow manifest plus an M4-safe relative `dataset_ref`;
- the existing frozen-OOS guard remains authoritative.

Core implementation tests, full regression, Ruff, deployment/runtime and continuity checks passed on the pre-doc-update PR #35 head. Final continuity head must be green before merge.

### Runtime / PWA

- Fast Momentum runs server-side every ~15 seconds and remains paper-only.
- `TradeLedger` runtime persistence is separate from M4/M5 research state.
- Fast Momentum supports persistent OPEN/MARK/CLOSE state/history.
- The PWA consumes server truth rather than browser memory.
- Research / AI Lab and scanner heartbeat are read-only observability.
- Binance Demo API credentials are currently re-entered manually in the app; next production UX task is encrypted server-side one-time credential persistence with replace/delete controls. Secrets must never be returned to the browser or stored in browser localStorage.

## Production proof — manual evidence on 2026-08-26

Confirmed:

- Linode checkout consumed GitHub `main` through state commit `050cd9be203a09aca95a152d7102fa280c397ee7`.
- nginx + Certbot configured `eba-trader-172-236-150-62.sslip.io`.
- External iPhone access to the HTTPS PWA succeeded.
- Home, Scan and Settings displayed live server state.
- History displayed persisted Fast Paper trades with entry/exit, fees and exit reasons.
- Fast Paper trade detail displayed persisted execution facts, strategy evidence and trade chart.
- Binance Demo connection modal is present and currently accepts optional API key/secret manually.

Still unproven:

- standalone Chart / Positions / Research screen smoke against server truth;
- active Fast Momentum paper position surviving a service/server restart and later MARK/CLOSE;
- final disposition of the older carry paper engine.

## Known architecture issue

Current lifecycle path is:

`GENERATED -> BACKTESTED -> OOS_VERIFIED -> ROBUSTNESS_VERIFIED -> PAPER_CANDIDATE -> ...`

Desired methodology conceptually wants robustness before opening frozen OOS. Do not bypass the machine lifecycle; redesign/migrate/test it before automated frozen-OOS orchestration.

## Immediate Next

1. Final-CI and squash-merge PR #35.
2. Add encrypted server-side one-time Binance Demo credential persistence; browser receives status/masked metadata only and supports explicit replace/delete.
3. Build a real BTCUSDT USD-M development dataset on Linode outside frozen OOS using `eba-build-orderflow-features`.
4. Run the #34 deterministic ablation batch through M4 queue/worker/evidence/gates.
5. Persist/rank survivors only for triage; do not open frozen OOS from ranking results.
6. Finish remaining production smoke/restart-recovery proof in parallel.

## Important constraints

- No API secrets in Git or browser persistent storage; withdrawal permission is never required.
- Deterministic risk has veto authority.
- Runtime state must survive Git pulls, browser refreshes and process/server restarts.
- Strategy versions/evidence are immutable.
- AI strategy generation does not execute arbitrary generated Python.
- Order-flow executed trades and resting LOB liquidity are separate data domains.
- Order-flow dataset gaps fail closed.
- Spot and USD-M futures data are separate experiment datasets and must not be silently mixed.
- Same-candle still-forming footprint data cannot be used in candle decisions.
- A development win-rate increase is not promotion evidence.
- Generic research workers and ablation orchestration cannot open frozen OOS or real execution.

## Validation status

- PRs #29-#34 passed their full regression/Ruff/deployment/runtime/continuity gates before merge.
- PR #35 pre-continuity-update head passed full regression, Ruff, Linode runtime checks, Linode production bundle and Continuity guard after two lint-only findings were fixed.
- External HTTPS/latest-main proof is manually established; restart-recovery proof remains open.

## Continuity system

Canonical continuity files are `AGENTS.md`, `PROJECT_STATE.md`, `ARCHITECTURE.md`, `DECISIONS.md`, `TODO.md`, `CHANGELOG.md`, `SESSION_HANDOFF.md`, and `docs/CONTINUITY_PROTOCOL.md`. Every meaningful AI/coding session must update them when state changes.
