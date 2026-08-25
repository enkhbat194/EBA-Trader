# EBA Trader — Project State

_Last reconciled: 2026-08-26 (Asia/Ulaanbaatar)_
_Verified through GitHub `main` continuity merge: `368679fd232a1b9ef943147361346f57c36ff01c`._

This is the primary cross-chat continuation summary. Actual current implementation/config/tests and Git history override stale text.

## Current goal

Operate EBA Trader as a restart-safe 24/7 Linode paper/research system, build a controlled AI Strategy Factory on top of the M4 evidence platform, test whether order-flow/footprint features add incremental edge over candle-only baselines, and keep real-money execution locked until a separate evidence chain proves it.

The repository is also the shared memory bridge for ChatGPT branch chats and AI coding sessions. New connected sessions must read `AGENTS.md` and the continuity files before work, then write state/handoff back after meaningful work.

## Current stage

- Research platform: **M4 COMPLETE**.
- AI Strategy Factory: **M5 IN PROGRESS**.
- Continuity system: **INSTALLED / ENFORCED IN CI**.
- Current M5 frontier: historical order-flow acquisition/alignment -> allowlisted order-flow backtest adapter -> candle-vs-order-flow ablation.
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

Fixed footprint windows use causal `[start,end)` boundaries and can emit buy/sell volume, delta, delta ratio, POC and cumulative delta.

Key modules:

- `src/eba_trader/orderflow.py`
- `src/eba_trader/orderflow_dataset.py`
- `src/eba_trader/footprint_dataset.py`

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

1. Implement deterministic historical Binance `aggTrades` downloader/pagination with source/range provenance.
2. Implement missing-ID-range detection and repair; unresolved gaps remain fail-closed.
3. Implement causal footprint-to-candle alignment and boundary tests.
4. Add an allowlisted M4 backtest adapter for approved order-flow features.
5. Run controlled candle-only vs candle+delta/CVD development ablations under identical fees/slippage/gates.
6. Rank survivors only for triage; keep frozen OOS closed.
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
- A development win-rate increase is not promotion evidence.
- Generic research workers cannot open frozen OOS or real execution.

## Validation status

- PR #26 CI: full regression/Ruff/deployment/runtime checks passed before merge.
- PR #27 CI: full regression/Ruff/deployment/runtime checks passed after lint correction before merge.
- PR #28 CI: full regression/Ruff/deployment/runtime checks passed before merge.
- PR #29 continuity system: dedicated Continuity guard PASS; full regression/Ruff/shell/deployment contract PASS; Linode runtime checks PASS before merge.
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
