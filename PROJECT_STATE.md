# EBA Trader — Project State

_Last reconciled: 2026-08-27 (Asia/Ulaanbaatar)_
_Current implementation frontier: PR #41 lifecycle policy v2; GitHub `main` remains authoritative after merge._

This is the primary cross-chat continuation summary. Actual current implementation/config/tests and Git history override stale text.

## Current goal

Operate EBA Trader as a restart-safe 24/7 Linode paper/research system, build a controlled AI Strategy Factory on top of the M4 evidence platform, test whether order-flow/footprint features add incremental edge over candle-only baselines, expose progress in the phone-first PWA, and keep real-money execution locked until a separate evidence chain proves it.

## Current stage

- Research platform: **M4 COMPLETE**.
- AI Strategy Factory: **M5 IN PROGRESS**.
- Continuity system: **INSTALLED / ENFORCED IN CI**.
- Deterministic order-flow ablation orchestration: **MERGED in #34**.
- Venue-matched real USD-M feature-dataset workflow: **MERGED in #35**.
- Encrypted one-time Binance Demo credential persistence: **MERGED in #36 / real production save now observed**.
- Linode auto-update recovery/diagnostics: **MERGED in #37 / production-verified**.
- Binance market-data log-flood fix: **MERGED in #38 / production-verified**.
- Continuity reconciliation through production recovery: **MERGED in #39**.
- Persistent research runtime + real-ablation CLI/runner + repo-managed journald policy: **MERGED in #40** at `8876bc22b59f236e8df038440aaa6116c5d1afdf`; production PWA reports build `8876bc2`.
- Lifecycle policy v2 robustness-before-OOS migration: **IMPLEMENTED/CI-GREEN in PR #41 candidate; merge pending**.
- Current research frontier: complete #41, then run a real BTCUSDT USD-M development dataset outside frozen OOS and execute candle-only vs Delta/CVD through M4.
- Real-money execution: **LOCKED**.
- Frozen OOS automation: **LOCKED until a strategy passes v2 robustness evidence**.

## Source of truth and active infrastructure

- Repository: `enkhbat194/EBA-Trader`
- Code source of truth: GitHub `main`
- Active runtime target: Akamai/Linode Nanode 1 GB, Singapore 2, Ubuntu 24.04 LTS
- Server repository path: `/opt/Eba-Trader`
- Persistent runtime DB: `/var/lib/eba-trader/eba_trader.db`
- Persistent research DB: `/var/lib/eba-trader/research/eba_research.db`
- Persistent research datasets: `/var/lib/eba-trader/research/datasets`
- Persistent research evidence: `/var/lib/eba-trader/research/evidence`
- Market-data service: `eba-binance-data.service`
- Runtime API service: `eba-runtime-api.service` on `127.0.0.1:8765`
- PWA/web service: `eba-web.service` on `127.0.0.1:8000` behind nginx/Let's Encrypt HTTPS
- Bounded research worker: `eba-research-worker.service` + timer
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
- #40 persistent research runtime, bounded worker, repo-managed journald policy and real development ablation CLI/runner.
- #41 candidate lifecycle policy v2 with robustness-before-OOS and legacy-state migration.

Current enabled executed-trade features are buy/sell volume, delta, delta ratio, CVD and POC price. Stacked imbalance, absorption, exhaustion and LOB depth imbalance remain unimplemented/unapproved as edge features.

## Production research/runtime reality

### Host protection and persistent research

The production policy is versioned as `deploy/journald/eba-trader.conf`:

- `SystemMaxUse=250M`
- `SystemKeepFree=1G`
- `MaxRetentionSec=7day`

Long-running research state lives under `/var/lib/eba-trader/research` rather than the Git checkout. The bounded worker runs at most eight jobs per invocation with CPU 50% and memory 512 MB limits. Runtime `TradeLedger` remains separate.

### Verified real-ablation surface

`eba-m5-real-ablation` verifies workflow/data hashes, USD-M venue, symbol/interval/time range, dataset containment and frozen-OOS separation before emitting deterministic #34 development experiments. `scripts/run_m5_real_ablation.sh` performs verified dataset build -> deterministic queue -> bounded worker/evidence. This path is development-only and has no exchange/OOS authority.

### Lifecycle policy v2

PR #41 changes the current research promotion order to:

`GENERATED -> BACKTESTED -> ROBUSTNESS_VERIFIED -> OOS_VERIFIED -> PAPER_CANDIDATE -> ...`

Key migration rule: old M4 databases are not silently reinterpreted. Legacy pre-OOS rows may migrate safely to v2; legacy rows already at OOS or later remain policy v1/frozen and must enter `RETEST_REQUIRED` before v2 re-entry. A passed robustness verdict may promote only `BACKTESTED -> ROBUSTNESS_VERIFIED`; it cannot open OOS itself.

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
- old log cleanup, reducing root disk from ~90.1% used to ~21% and `/var/log` to ~162M;
- PWA reports server build `8876bc2`, confirming #40 reached the active Linode runtime;
- Binance Demo credential UI reports a real key encrypted and saved securely on Linode.

Still pending:

- direct server-internal proof of the #40 journald drop-in, research paths and research-worker timer;
- real BTCUSDT USD-M development dataset + actual candle-only vs Delta/CVD evidence run;
- standalone Chart / Positions / Research screen smoke;
- no-paste Demo reconnect after a real restart;
- active Fast Momentum position surviving service/server restart and later MARK/CLOSE;
- audit/disposition of the older carry paper engine.

## Immediate Next

1. Finish PR #41 continuity update, re-run required CI and squash merge only when all gates pass.
2. Verify the #40 server-internal runtime contract.
3. Execute one real BTCUSDT USD-M development-only window outside frozen OOS through `scripts/run_m5_real_ablation.sh`.
4. Inspect immutable M4 evidence and compare candle-only vs Delta/CVD under identical costs.
5. Add a deterministic comparison/verdict artifact if the real pipeline is sound; do not open frozen OOS unless v2 robustness evidence passes.
6. Finish Chart / Positions / Research smoke, Demo no-paste reconnect and active-position restart recovery proof.
7. Audit/retire-or-persist the carry paper engine.
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

- PR #40 merged after full Python regression, Ruff, shell syntax, deployment contract, Linode runtime checks and continuity guard passed.
- PR #41 code + migration tests have passed full Python regression, Ruff, shell syntax, deployment contract, Linode runtime checks and continuity guard before final continuity edits.
- No real Delta/CVD edge claim exists yet; the empirical development run remains pending.

## Continuity system

Canonical continuity files are `AGENTS.md`, `PROJECT_STATE.md`, `ARCHITECTURE.md`, `DECISIONS.md`, `TODO.md`, `CHANGELOG.md`, `SESSION_HANDOFF.md`, and `docs/CONTINUITY_PROTOCOL.md`. Every meaningful coding session must update them when state changes.
