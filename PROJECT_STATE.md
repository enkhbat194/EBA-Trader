# EBA Trader — Project State

_Last reconciled: 2026-08-26 (Asia/Ulaanbaatar)_
_Verified through GitHub `main` PR #32 merge: `931b8a7dff68c659f2fa21d4fea33c87053c5022`._

This is the primary cross-chat continuation summary. Actual current implementation/config/tests and Git history override stale text.

## Current goal

Operate EBA Trader as a restart-safe 24/7 Linode paper/research system, build a controlled AI Strategy Factory on top of the M4 evidence platform, test whether order-flow/footprint features add incremental edge over candle-only baselines, expose research progress in the phone-first PWA, and keep real-money execution locked until a separate evidence chain proves it.

The repository is the shared memory bridge for ChatGPT branch chats and AI coding sessions. New connected sessions must read `AGENTS.md` and the continuity files before work, then write state/handoff back after meaningful work.

## Current stage

- Research platform: **M4 COMPLETE**.
- AI Strategy Factory: **M5 IN PROGRESS**.
- Continuity system: **INSTALLED / ENFORCED IN CI**.
- Current M5 frontier: deterministic candle-only vs candle+delta/CVD development ablation orchestration on verified BTCUSDT USD-M historical data.
- Historical order-flow acquisition, missing-ID repair, causal candle alignment, feature-dataset materialization and allowlisted ablation adapters: **IMPLEMENTED / MERGED through #31**.
- Research / AI Lab PWA: **IMPLEMENTED / MERGED in #32**; read-only observability only.
- Runtime: persistent paper system on the Linode architecture; external production-proof checks remain partially unverified from repository evidence alone.
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
- PWA/web service: `eba-web.service` on `127.0.0.1:8000` behind public HTTPS bootstrap
- Auto deploy: `eba-auto-update.timer`; exact `origin/main`, dirty-checkout refusal, service/API health checks and rollback are implemented in `scripts/update_linode_runtime.sh`
- Replit/Render: deprecated EBA Trader backend/runtime paths

## Completed research milestones

### M4 — complete

Merged PRs:

- #20 strategy-platform foundation;
- #21 restart-safe experiment queue and worker leases;
- #22 generic backtest worker and immutable evidence;
- #23 development screening gates and immutable verdicts;
- #24 bounded robustness fan-out and aggregate verdicts.

M4 provides immutable strategy versions, deterministic experiment IDs, restart-safe queue/leases, allowlisted workers, content-addressed evidence, declarative gates and evidence-required lifecycle transitions. Generic workers do not unlock frozen OOS or execution.

### M5 — completed foundation so far

- #25 order-flow/footprint research foundation.
- #26 constrained strategy DSL, approved feature registry, bounded deterministic parameter expansion and M4 candidate emission.
- #27 strategy-family templates, near-duplicate guard, cheap screening and deterministic survivor ranking.
- #28 historical Binance aggregate-trade normalization/cache, sequence/integrity gate and deterministic footprint windows.
- #30 venue-aware historical aggregate-trade acquisition, request/range provenance, missing-ID repair and causal closed-footprint/candle alignment.
- #31 causal feature-dataset materialization plus allowlisted candle-only/order-flow backtest adapters on the exact same aligned feature CSV.
- #32 phone-first Research / AI Lab PWA dashboard with read-only research status and explicit safety-lock visibility.

Enabled order-flow feature registry entries today:

- executed buy volume;
- executed sell volume;
- delta;
- delta ratio;
- CVD;
- POC price.

Disabled/not yet implemented entries:

- stacked imbalance;
- absorption;
- exhaustion;
- LOB depth imbalance.

## Current implementation reality

### M5 Strategy Factory

AI hypotheses are constrained structured data. Unknown/disabled features fail closed. Parameter fan-out is bounded and candidates are deterministically identified/emitted into the M4 research store/queue. Cheap screening and ranking are triage only and carry no lifecycle promotion authority.

Key modules:

- `src/eba_trader/m5_hypothesis.py`
- `src/eba_trader/m5_features.py`
- `src/eba_trader/m5_factory.py`
- `src/eba_trader/m5_emitter.py`
- `src/eba_trader/m5_family.py`
- `src/eba_trader/m5_similarity.py`
- `src/eba_trader/m5_selection.py`

### Order flow / footprint

Footprint is derived from raw executed market events, not chart pixels. Binance aggregate-trade buyer-maker semantics are normalized into aggressor BUY/SELL. Historical datasets are content-addressed and validated for duplicate/conflicting IDs, timestamp ordering, file hash and sequence gaps. Unresolved gaps mean the dataset is not backtest-ready.

The acquisition layer supports Binance Spot and USD-M Futures explicitly. USD-M Futures is the default for the current BTCUSDT perpetual research target; Spot is not silently mixed with futures order flow. Acquisition uses a time bootstrap followed by deterministic aggregate-trade ID pagination, records request/range provenance, detects missing ID ranges and attempts exact `fromId` repairs. An unsuccessful repair remains fail-closed through the research-ready gate.

Fixed footprint windows use `[start,end)` event boundaries and emit buy/sell volume, delta, delta ratio, POC and cumulative delta. Candle alignment is causal: the closed footprint `[t-step,t)` becomes available to the candle opening at `t`; the same candle's still-forming `[t,t+step)` footprint is never injected into its decision.

PR #31 adds an aligned feature CSV and two development adapters:

- `ema_feature_baseline_v1` — candle-only control arm using the same feature dataset but consuming no order-flow feature;
- `ema_orderflow_v1` — EMA crossover with causal `of_delta_ratio` and/or `of_cvd` entry gates.

A permissive order-flow gate is tested to match the baseline, while negative delta/CVD can suppress an otherwise valid EMA entry. Frozen OOS remains guarded.

Key modules:

- `src/eba_trader/orderflow.py`
- `src/eba_trader/orderflow_dataset.py`
- `src/eba_trader/footprint_dataset.py`
- `src/eba_trader/orderflow_acquisition.py`
- `src/eba_trader/orderflow_alignment.py`
- `src/eba_trader/orderflow_feature_dataset.py`
- `src/eba_trader/backtest_adapter.py`

### Research / AI Lab PWA

PR #32 adds a seventh mobile PWA tab and read-only `/api/research/status` endpoint. It reports:

- current M5 focus from repository continuity;
- M5 completed/remaining TODO counts;
- order-flow data-plane and ablation-adapter readiness;
- optional M4 research SQLite strategy/experiment/lifecycle counts when that DB exists on the web runtime;
- explicit Frozen OOS, real-execution and ranking-authority locks.

The dashboard is observational only. It cannot promote lifecycle state, modify research data, or enable trading.

### Runtime / paper state

- Binance public market-data path exists through NautilusTrader.
- `TradeLedger` SQLite runtime persistence is separate from M4/M5 research state.
- Fast Momentum supports BTCUSDT perpetual paper LONG/SHORT decisions and persistent OPEN/MARK/CLOSE history/recovery.
- PWA consumes server truth rather than browser memory.
- Real exchange order submission is still disabled.

## Known problems / unresolved architecture

### Lifecycle validation order

Current `src/eba_trader/lifecycle.py` promotion path is:

`GENERATED -> BACKTESTED -> OOS_VERIFIED -> ROBUSTNESS_VERIFIED -> PAPER_CANDIDATE -> ...`

The desired research policy conceptually wants robustness before opening frozen OOS. This mismatch is real. Do not bypass the machine lifecycle manually; redesign/migrate/test it before automated frozen-OOS orchestration.

### External production proof

Repository code/CI cannot prove the following current external state:

- latest `main` is actually deployed on Linode;
- public HTTPS works from an external phone/browser at this moment;
- one real restart/service-restart preserved a live Fast Momentum paper position through recovery and later MARK/CLOSE;
- older carry paper engine persistence has been completed or retired.

These remain explicit manual/remote proof tasks.

## Immediate Next

1. Add a deterministic ablation orchestrator that emits paired candle-only vs candle+delta/CVD experiments with identical dataset/EMA/cost parameters.
2. Add a CLI/workflow to materialize the real development feature dataset from candle CSV + verified order-flow/acquisition manifests.
3. Run controlled BTCUSDT USD-M development ablations through M4 evidence/gates.
4. Surface real experiment counts/results automatically in Research / AI Lab when a research DB is present on the runtime used for research.
5. Persist/rank survivors only for triage; do not open frozen OOS from ranking results.
6. Reconcile lifecycle ordering before any automated frozen-OOS orchestration.
7. In parallel, complete the Linode external HTTPS + restart/recovery production proof.

See `TODO.md` for the full ordered backlog.

## Important constraints

- No API secrets in Git.
- Withdrawal permission is never required.
- Deterministic risk has veto authority.
- Runtime state must survive Git pulls, browser refreshes and process/server restarts.
- Strategy versions/evidence are immutable.
- AI strategy generation does not execute arbitrary generated Python.
- Order-flow executed trades and resting LOB liquidity are separate data domains.
- Order-flow dataset gaps fail closed.
- Spot and USD-M futures order flow are separate experiment datasets.
- Same-candle still-forming footprint data cannot be used in candle decisions.
- A development win-rate increase is not promotion evidence.
- Generic research workers cannot open frozen OOS or real execution.
- Research / AI Lab is read-only observability and has no lifecycle/risk authority.

## Validation status

- PR #29 continuity system: Continuity guard/full regression/Ruff/shell/deployment/runtime checks passed before merge.
- PR #30 acquisition/alignment: full regression/Ruff/shell/deployment/runtime/continuity checks passed before merge.
- PR #31 ablation adapters: full regression/Ruff/shell/deployment/runtime/continuity checks passed before merge.
- PR #32 Research / AI Lab: final head passed full regression/Ruff/shell/deployment/runtime/continuity checks before squash merge.
- External Linode/public-phone/restart proof: still not established by repo CI.

## Continuity system

Canonical continuity files:

- `AGENTS.md`
- `PROJECT_STATE.md`
- `ARCHITECTURE.md`
- `DECISIONS.md`
- `TODO.md`
- `CHANGELOG.md`
- `SESSION_HANDOFF.md`
- `docs/CONTINUITY_PROTOCOL.md`

Every meaningful AI/coding session must update these when state changes. `python scripts/check_continuity.py` verifies that the continuity contract has not regressed to empty/template state, and `.github/workflows/continuity.yml` enforces it on PRs and `main` pushes.
