# EBA Trader — Project State

_Last reconciled: 2026-08-27 (Asia/Ulaanbaatar)_
_Current implementation frontier: PR #40 `m5-real-ablation-cli`; GitHub `main` remains authoritative after merge._

This is the primary cross-chat continuation summary. Actual current implementation/config/tests and Git history override stale text.

## Current goal

Operate EBA Trader as a restart-safe 24/7 Linode paper/research system, build a controlled AI Strategy Factory on top of the M4 evidence platform, test whether order-flow/footprint features add incremental edge over candle-only baselines, expose progress in the phone-first PWA, and keep real-money execution locked until a separate evidence chain proves it.

## Current stage

- Research platform: **M4 COMPLETE**.
- AI Strategy Factory: **M5 IN PROGRESS**.
- Continuity system: **INSTALLED / ENFORCED IN CI**.
- Deterministic order-flow ablation orchestration: **MERGED in #34**.
- Venue-matched real USD-M feature-dataset workflow: **MERGED in #35**.
- Encrypted one-time Binance Demo credential persistence: **MERGED in #36**.
- Linode auto-update recovery/diagnostics: **MERGED in #37 / production-verified**.
- Binance market-data log-flood fix: **MERGED in #38 / production-verified**.
- Continuity reconciliation through production recovery: **MERGED in #39**.
- Persistent research runtime + verified real-ablation runner: **IMPLEMENTED in PR #40; production deployment/run proof pending**.
- Current research frontier: deploy PR #40, build a real BTCUSDT USD-M development dataset outside frozen OOS, execute candle-only vs Delta/CVD through M4, then evaluate evidence without promotion.
- Real-money execution: **LOCKED**.
- Frozen OOS automation: **LOCKED pending lifecycle-order reconciliation**.

## Source of truth and active infrastructure

- Repository: `enkhbat194/EBA-Trader`
- Code source of truth: GitHub `main`
- Active runtime target: Akamai/Linode Nanode 1 GB, Singapore 2, Ubuntu 24.04 LTS
- Server repository path: `/opt/Eba-Trader`
- Persistent runtime DB: `/var/lib/eba-trader/eba_trader.db`
- Persistent research DB after PR #40 deployment: `/var/lib/eba-trader/research/eba_research.db`
- Persistent research datasets: `/var/lib/eba-trader/research/datasets`
- Persistent research evidence: `/var/lib/eba-trader/research/evidence`
- Market-data service: `eba-binance-data.service`
- Runtime API service: `eba-runtime-api.service` on `127.0.0.1:8765`
- PWA/web service: `eba-web.service` on `127.0.0.1:8000` behind nginx/Let's Encrypt HTTPS
- Research worker after PR #40 deployment: bounded `eba-research-worker.service` + timer
- Public PWA: `https://eba-trader-172-236-150-62.sslip.io/`
- Auto deploy: `eba-auto-update.timer`; exact `origin/main`, dirty-checkout refusal, health checks, rollback and persistent diagnostics are implemented.
- Replit/Render: deprecated backend/runtime paths.

## Completed research milestones

### M4 — complete

PRs #20-#24 provide immutable strategy versions, deterministic experiment IDs, restart-safe queue/leases, allowlisted workers, content-addressed evidence, declarative gates and bounded robustness evidence. Generic workers do not unlock frozen OOS or execution.

### M5 — foundation implemented so far

- #25 executed-trade order-flow/footprint foundation.
- #26 constrained strategy DSL, approved feature registry and deterministic candidate emission.
- #27 family templates, near-duplicate guard, cheap screening and survivor ranking.
- #28 aggregate-trade normalization/cache, integrity gate and footprint windows.
- #30 venue-aware acquisition, gap repair and causal candle alignment.
- #31 same-dataset candle-only/order-flow backtest adapters.
- #32 phone-first Research / AI Lab dashboard.
- #33 carry-label clarification and Fast Momentum heartbeat.
- #34 deterministic one-control-to-many-treatment ablation orchestration.
- #35 verified venue-matched USD-M candle + order-flow feature-dataset workflow.
- #36 encrypted one-time Binance Demo credential vault.
- #40 implementation adds persistent research runtime and the real development ablation execution surface.

Current enabled executed-trade features are buy/sell volume, delta, delta ratio, CVD and POC price. Stacked imbalance, absorption, exhaustion and LOB depth imbalance remain unimplemented/unapproved as edge features.

## PR #40 implementation reality

### Reproducible host protection

The manual production journald policy is now versioned as `deploy/journald/eba-trader.conf`:

- `SystemMaxUse=250M`
- `SystemKeepFree=1G`
- `MaxRetentionSec=7day`

Both install and update paths provision the drop-in. It is treated as a host-safety invariant so application rollback does not intentionally remove the disk-protection policy.

### Persistent research control plane

Long-running research state is moved outside the Git checkout under `/var/lib/eba-trader/research`. This prevents valid research artifacts from dirtying `/opt/Eba-Trader` and blocking fail-closed auto-update. Runtime `TradeLedger` remains separate.

An existing Linode environment file is upgraded idempotently with research path defaults without overwriting explicit operator values.

### Bounded worker

`eba-research-worker.timer` runs a oneshot research worker approximately once per minute. Each invocation is bounded to eight jobs, CPU quota 50% and memory 512 MB, with write access limited to the persistent research namespace. It only consumes queued research jobs and has no OOS/exchange authority.

### Verified real-ablation queue CLI

`eba-m5-real-ablation` verifies before queue emission:

- PR #35 workflow schema;
- USD-M futures venue;
- symbol/interval/time-range consistency;
- relative `dataset_ref` containment under the configured dataset root;
- feature CSV existence and SHA-256;
- matching feature manifest and SHA;
- no overlap with the frozen first-cycle OOS range;
- allowlisted Delta/CVD gate fields only.

It then emits the existing deterministic #34 development ablation batch into M4 and reports machine-readable experiment IDs. The stage is fixed to `m5_orderflow_ablation_dev`; frozen OOS and live execution remain false.

### One-command development runner

`scripts/run_m5_real_ablation.sh` performs:

`verified USD-M feature build -> verified deterministic ablation queue -> exact emitted job count through M4 worker/evidence`

using the persistent research paths and a process lock. The first versioned gate set includes a permissive Delta-ratio sanity arm plus bounded Delta/CVD treatments. These are hypotheses, not promotion thresholds.

## Runtime / PWA

- Fast Momentum runs server-side every ~15 seconds and remains paper-only.
- Fast Paper OPEN/MARK/CLOSE state/history persists in `TradeLedger`.
- Research / AI Lab and scanner heartbeat remain read-only observability.
- The PWA consumes server truth rather than browser memory.
- Binance Demo credential secrets are encrypted server-side and never returned to browser JavaScript.

## Production proof status

Confirmed on 2026-08-26/27:

- public HTTPS PWA from external iPhone;
- Home / Scan / Settings server-backed state;
- persisted Fast Paper History and trade detail/chart;
- #37 auto-update recovery on real Linode;
- #38 deployment with active market-data service and no raw per-tick INFO flood;
- old log cleanup, reducing root disk from ~90.1% used to ~21% and `/var/log` to ~162M.

Still pending:

- PR #40 production deployment verification (journald policy, research paths, research-worker timer);
- real BTCUSDT USD-M development dataset + actual candle-only vs Delta/CVD evidence run;
- standalone Chart / Positions / Research screen smoke;
- one real Binance Demo credential save followed by no-paste reconnect;
- active Fast Momentum position surviving service/server restart and later MARK/CLOSE;
- audit/disposition of the older carry paper engine.

## Known architecture issue

Current machine lifecycle is:

`GENERATED -> BACKTESTED -> OOS_VERIFIED -> ROBUSTNESS_VERIFIED -> PAPER_CANDIDATE -> ...`

Accepted research methodology requires robustness before opening frozen OOS. Automated frozen OOS remains locked until a deliberate lifecycle redesign/migration/test changes this; no manual bypass is allowed.

## Immediate Next

1. Finish PR #40 final CI and merge only when all gates pass.
2. Verify Linode auto-deployed the merged package and that journald/research-worker/persistent research state are active.
3. Execute one real BTCUSDT USD-M development-only window outside frozen OOS through `scripts/run_m5_real_ablation.sh`.
4. Inspect immutable M4 evidence; require the permissive treatment sanity invariant and compare Delta/CVD treatments under identical costs.
5. Add a deterministic comparison/verdict artifact if the real pipeline is sound; do not open frozen OOS.
6. Redesign lifecycle ordering with migration/tests so robustness precedes frozen OOS.
7. Continue remaining production proofs and carry-engine audit in parallel.
8. Only after real executed-trade evidence, add stacked imbalance/absorption/exhaustion candidates; LOB remains a separate later data plane.

## Important constraints

- No API secrets in Git, chat or browser persistent storage; withdrawal permission is never required.
- Only Binance Demo credentials use the current encrypted vault.
- Deterministic risk has veto authority.
- Runtime and research persistence remain separate.
- Strategy versions/evidence are immutable.
- AI strategy generation does not execute arbitrary generated Python.
- Executed-trade order flow and resting LOB liquidity are separate data domains.
- Gapped/tampered order-flow data fails closed.
- Spot and USD-M futures must not be silently mixed.
- Same-candle still-forming footprint data cannot be used in candle decisions.
- Development win rate/ranking is not promotion evidence.
- Generic research workers and ablation orchestration cannot open frozen OOS or exchange execution.
- High-frequency raw market ticks are data, not normal INFO service logs.

## Validation status

- PR #40 pre-continuity head passed full Python regression, Ruff, shell syntax, deployment contract, Linode runtime checks and continuity guard after the import-format correction.
- Final continuity-updated PR #40 head must pass the same required CI before squash merge.
- PR #40 has not yet been production-run on Linode, so no real Delta/CVD edge claim exists yet.

## Continuity system

Canonical continuity files are `AGENTS.md`, `PROJECT_STATE.md`, `ARCHITECTURE.md`, `DECISIONS.md`, `TODO.md`, `CHANGELOG.md`, `SESSION_HANDOFF.md`, and `docs/CONTINUITY_PROTOCOL.md`. Every meaningful coding session must update them when state changes.
