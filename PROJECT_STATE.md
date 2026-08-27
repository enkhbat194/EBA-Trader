# EBA Trader — Project State

_Last reconciled: 2026-08-27 (Asia/Ulaanbaatar)_
_Current implementation frontier: PR #45 real M5 development autorun candidate; GitHub `main` remains authoritative after merge._

This is the primary cross-chat continuation summary. Actual current implementation/config/tests and Git history override stale text.

## Current goal

Operate EBA Trader as a restart-safe 24/7 Linode paper/research system, build a controlled AI Strategy Factory on top of the M4 evidence platform, test whether order-flow/footprint features add incremental development evidence over candle-only baselines, expose progress in the phone-first PWA, and keep real-money execution locked until a separate evidence chain proves it.

## Current stage

- Research platform: **M4 COMPLETE**.
- AI Strategy Factory: **M5 IN PROGRESS**.
- Continuity system: **INSTALLED / ENFORCED IN CI**.
- Lifecycle policy v2 robustness-before-OOS: **MERGED #41** at `32a39c57cb9c86bd2b956ea670fa3031229d0efc`.
- External public production smoke automation: **MERGED #42** at `a1425c5eb0e839bed4645f4a31bd95512c8d1995`.
- Production proof + natural Fast OPEN restart watcher: **MERGED #43** at `4a46a0fbec7d20007bda9061572756841de190c6`.
- Legacy carry active-entry retirement: **MERGED #44** at `0df5f4d9a7ce054b1a2b65002b9329ba0c8143aa` and production-verified.
- First bounded real BTCUSDT M5 development autorun + immutable comparison report: **PR #45 CI-GREEN candidate**.
- Real-money execution: **LOCKED**.
- Frozen OOS: **LOCKED**; development comparisons have no promotion authority.

## Source of truth and active infrastructure

- Repository: `enkhbat194/EBA-Trader`
- Code source of truth: GitHub `main`
- Active runtime target: Linode Nanode 1 GB, Ubuntu 24.04 LTS
- Server repository path: `/opt/Eba-Trader`
- Persistent runtime DB: `/var/lib/eba-trader/eba_trader.db`
- Persistent research DB: `/var/lib/eba-trader/research/eba_research.db`
- Persistent research datasets: `/var/lib/eba-trader/research/datasets`
- Persistent research evidence: `/var/lib/eba-trader/research/evidence`
- Market-data service: `eba-binance-data.service`
- Runtime API: `eba-runtime-api.service` on `127.0.0.1:8765`
- PWA/web: `eba-web.service` on `127.0.0.1:8000` behind HTTPS
- Research worker: `eba-research-worker.service` + timer
- Fast restart proof watcher: `eba-fast-restart-proof.service` + timer
- PR #45 candidate adds `eba-m5-real-ablation.service` + timer
- Public PWA: `https://eba-trader-172-236-150-62.sslip.io/`
- Auto deploy: `eba-auto-update.timer` with exact-main deploy, dirty-checkout refusal, health gates and rollback.
- Replit/Render: deprecated backend/runtime paths.

## Completed research milestones

### M4 — complete

PRs #20-#24 provide immutable strategy versions, deterministic experiment IDs, restart-safe queue/leases, allowlisted workers, content-addressed evidence, declarative development gates and bounded robustness evidence.

### M5 — implemented foundation

- #25 executed-trade order-flow/footprint foundation.
- #26 constrained strategy DSL, approved feature registry and deterministic candidate emission.
- #27 family templates, near-duplicate guard, cheap screening and survivor ranking.
- #28 aggregate-trade normalization/cache, integrity gate and footprint windows.
- #30 venue-aware acquisition, gap repair and causal candle alignment.
- #31 same-dataset candle-only/order-flow backtest adapters.
- #32 phone-first Research / AI Lab dashboard.
- #33 Fast Momentum heartbeat and carry-label clarification.
- #34 deterministic one-control-to-many-treatment ablation orchestration.
- #35 verified venue-matched USD-M candle + order-flow feature-dataset workflow.
- #36 encrypted one-time Binance Demo credential vault.
- #40 persistent research runtime, bounded worker, journald policy and real-ablation CLI/runner.
- #41 lifecycle v2: `BACKTESTED -> ROBUSTNESS_VERIFIED -> OOS_VERIFIED`.
- #42/#43 external/sanitized production proof and restart-proof automation.
- #44 legacy carry removed from active production entry authority.
- #45 candidate: automatic first real development ablation plus immutable baseline-vs-Delta/CVD report.

Current executed-trade features are buy/sell volume, delta, delta ratio, CVD and POC price. Stacked imbalance, absorption, exhaustion and LOB depth imbalance remain later work.

## Production runtime reality

### Paper execution

Fast Momentum is the sole active production paper engine. It runs server-side and stores OPEN/MARK/CLOSE state in SQLite. The old carry engine remains compatibility/historical code only and cannot create new production carry positions by default. Real orders remain disabled.

### Credential and public proof

The Binance Demo key is encrypted on Linode and never returned to the browser. External GitHub runners have verified exact deployed main builds over public HTTPS. For merge `0df5f4d9...`, production proof passed Demo reconnect, Chart, Positions, frozen-OOS lock and real-execution lock.

### Fast restart proof

PR #43 installs a passive watcher. It waits for a **natural** Fast Momentum paper OPEN, verifies the OPEN in `TradeLedger`, restarts `eba-web.service` once, requires recovery of the same `position_id`, and then waits for post-restart MARK/CLOSE. It never manufactures a trade. The mechanism is deployed; the market-dependent proof must not be called complete until its persisted phase reaches PASS/COMPLETE.

### Real M5 development ablation

PR #45 candidate automates a bounded first real run on BTCUSDT Binance USD-M 1m data for `2026-08-01T00:00Z` through `04:00Z`. It builds a verified dataset, emits the deterministic candle control + Delta/CVD treatment batch, executes through the immutable M4 worker/evidence pipeline, and writes a sanitized immutable comparison report.

The comparison report always records `developmentComparisonOnly=true`, `edgeClaimAllowed=false`, `promotionAuthority=false`, `frozenOosOpened=false`, and `liveExecutionAllowed=false`. A development winner is not a validated edge and cannot promote lifecycle state.

## Production proof status

Confirmed:

- public HTTPS PWA;
- exact-main external production build verification;
- encrypted saved Binance Demo credential;
- no-paste Demo autoconnect after application/service deployment restart;
- Chart public/server smoke;
- Positions server-truth smoke;
- Research server-truth/lock smoke;
- journald and persistent research runtime proof through sanitized production collector;
- legacy carry active entry retired and #44 exact production build verified;
- real execution locked and frozen OOS locked.

Still pending observational completion:

- a natural qualifying Fast Momentum OPEN followed by watcher-controlled restart, same-position recovery, MARK and CLOSE;
- PR #45 merge/deploy and completion of its first real M5 development batch/report;
- empirical interpretation of that batch without overstating edge.

## Validation status

- PR #41 merged only after lifecycle/migration regression, Ruff, shell, deployment, runtime and continuity gates passed.
- PR #42 external production smoke passed against exact build `a1425c5...`.
- PR #44 full regression/Ruff/shell/deployment/runtime/continuity passed; exact production merge `0df5f4d9...` later passed external sanitized proof.
- PR #45 pre-continuity head has passed full Python regression, Ruff, shell syntax, deployment contract, active Linode runtime checks and continuity guard.
- No real Delta/CVD edge claim exists. The first actual development autorun must finish before metrics are interpreted.

## Next exact tasks

1. Re-run PR #45 CI after this continuity reconciliation and squash-merge only if every required gate remains green.
2. Verify the exact #45 merge deploys to Linode and the new M5 timer is active via sanitized production proof.
3. Observe the real 2026-08-01 development autorun marker until it reaches terminal COMPLETE or a real failure is exposed; fix real failures rather than claiming success.
4. Compare candle-only vs Delta/CVD immutable evidence, explicitly as development evidence only.
5. Observe the passive Fast OPEN restart watcher until a natural position allows full recovery proof.
6. After real executed-trade evidence is sound, add stacked imbalance, absorption/exhaustion and divergence candidates. LOB stays a separate later data plane.

## Important constraints

- No API secrets in Git, chat or browser persistent storage; withdrawal permission is never required.
- Deterministic risk has veto authority.
- Runtime and research persistence remain separate.
- Strategy versions/evidence are immutable.
- AI strategy generation does not execute arbitrary generated Python.
- Executed-trade order flow and resting LOB liquidity are separate data domains.
- Gapped/tampered order-flow data fails closed.
- Spot and USD-M futures must not be silently mixed.
- Same-candle still-forming footprint data cannot be used in candle decisions.
- Development ranking or ablation wins are not promotion evidence.
- Generic research workers cannot open frozen OOS or exchange execution.
- High-frequency raw market ticks are data, not normal INFO service logs.

## Continuity system

Canonical continuity files are `AGENTS.md`, `PROJECT_STATE.md`, `ARCHITECTURE.md`, `DECISIONS.md`, `TODO.md`, `CHANGELOG.md`, `SESSION_HANDOFF.md`, and `docs/CONTINUITY_PROTOCOL.md`. Every meaningful coding session must update them when state changes.
