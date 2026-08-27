# EBA Trader — Project State

_Last reconciled: 2026-08-27 (Asia/Ulaanbaatar)_
_Current implementation frontier: verified first real M5 USD-M development ablation; next is evidence interpretation and richer executed-trade candidate families._

This is the primary cross-chat continuation summary. Actual current implementation/config/tests and Git history override stale text.

## Current goal

Operate EBA Trader as a restart-safe 24/7 Linode paper/research system, build a controlled AI Strategy Factory on top of the M4 evidence platform, test whether executed-trade order-flow/footprint features add incremental development evidence over candle-only baselines, expose progress in the phone-first PWA, and keep real-money execution locked until a separate evidence chain proves it.

## Current stage

- Research platform: **M4 COMPLETE**.
- AI Strategy Factory: **M5 IN PROGRESS — FIRST REAL DEVELOPMENT ABLATION COMPLETE**.
- Continuity system: **INSTALLED / ENFORCED IN CI**.
- Historical fixed-window USD-M order-flow acquisition: **VERIFIED BINANCE PUBLIC ARCHIVE + SHA-256 CHECKSUM**.
- Hardened external production proof: **MERGED #52** at `7e24df486839c92f9c324cbd910efc00dfe7bc4d` and production verified.
- First real M5 batch: **COMPLETE / ALL TERMINAL / ALL EXPERIMENTS PASSED / EVIDENCE COMPLETE**.
- Fast restart proof: **PASS** in exact-build external production proof.
- Real-money execution: **LOCKED**.
- Frozen OOS: **LOCKED**; development comparisons have no promotion authority.

## Source of truth and active infrastructure

- Repository: `enkhbat194/EBA-Trader`
- Code source of truth: GitHub `main`
- Verified production build: `7e24df486839c92f9c324cbd910efc00dfe7bc4d`
- Active runtime target: Linode Nanode, Ubuntu 24.04 LTS
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
- M5 autorun: `eba-m5-real-ablation.service` + timer
- Public PWA: `https://eba-trader-172-236-150-62.sslip.io/`
- Auto deploy: `eba-auto-update.timer` with exact-main deployment and health/proof checks.
- Replit/Render: deprecated backend/runtime paths.

## Completed research milestones

### M4 — complete

PRs #20-#24 provide immutable strategy versions, deterministic experiment IDs, restart-safe queue/leases, allowlisted workers, content-addressed evidence, declarative development gates and bounded robustness evidence.

### M5 — implemented foundation and first real run

- #25 executed-trade order-flow/footprint foundation.
- #26 constrained strategy DSL, approved feature registry and deterministic candidate emission.
- #27 family templates, near-duplicate guard, cheap screening and survivor ranking.
- #28 aggregate-trade normalization/cache, integrity gate and footprint windows.
- #30 venue-aware acquisition, gap repair and causal candle alignment.
- #31 same-dataset candle-only/order-flow backtest adapters.
- #32 phone-first Research / AI Lab dashboard.
- #34 deterministic one-control-to-many-treatment ablation orchestration.
- #35 venue-matched USD-M candle + order-flow feature-dataset workflow.
- #36 encrypted one-time Binance Demo credential vault.
- #40 persistent research runtime, bounded worker, journald policy and real-ablation CLI/runner.
- #41 lifecycle v2: `BACKTESTED -> ROBUSTNESS_VERIFIED -> OOS_VERIFIED`.
- #42/#43 public/external production proof and restart-proof automation.
- #44 legacy carry removed from active production entry authority.
- #45 bounded/idempotent real development autorun and immutable comparison reporting foundation.
- #51 verified historical Binance USD-M public archive acquisition for fixed-window M5 research; merged at `1c1b683b7bfc9dd62cff9d96fcb3160213cd2595`.
- #52 terminal M5 requirements added to external production proof; merged at `7e24df486839c92f9c324cbd910efc00dfe7bc4d`.

Current executed-trade features include buy/sell volume, delta, delta ratio, CVD and POC price. Stacked imbalance, absorption, exhaustion, price/delta divergence and LOB depth remain later work.

## Historical M5 data-plane decision

The fixed first real M5 development window is `2026-08-01T00:00:00Z -> 2026-08-01T04:00:00Z`. Binance USD-M REST `aggTrades` later returned HTTP 400 for that historical window because it was outside the useful REST retention path. The project **does not roll the study window forward** to hide that provider limitation.

For fixed historical USD-M executed-trade research, EBA Trader now uses official Binance public daily `aggTrades` archives under `data.binance.vision`, verifies the published `.CHECKSUM` SHA-256, streams ZIP data to temporary storage, filters the exact requested window, supports the prior closed-footprint minute across UTC midnight, records archive provenance, and fails closed on integrity/sequence problems. Recent REST acquisition remains separate for recent data.

## First real M5 development result

The production autorun reached a valid terminal result on the fixed development window:

- phase: `COMPLETE`
- safe: `true`
- all terminal: `true`
- all experiments passed: `true`
- evidence complete: `true`
- batch: `abl_6c4a8eeb83a662894a3f2816`
- immutable report: `/var/lib/eba-trader/research/evidence/m5-real-ablation-20260801T000000Z-20260801T040000Z.json`
- frozen OOS opened: `false`
- real/live execution allowed: `false`

This proves the research pipeline and this development batch completed; it does **not** by itself prove an out-of-sample edge or grant lifecycle promotion.

## Production runtime reality

### Paper execution

Fast Momentum is the sole active production paper engine. It runs server-side and stores OPEN/MARK/CLOSE state in SQLite. Legacy carry is compatibility/historical code only and cannot create new production carry positions by default. Real orders remain disabled.

### Credential and public proof

The Binance Demo key is encrypted on Linode and never returned to the browser. Exact-build external runners verify the public production build, saved Demo reconnect, Chart, Positions, Research/locks, and now terminal M5 evidence.

### Fast restart proof

The passive watcher never manufactures a trade. The latest exact-build external production proof reports `fastRestartPhase=PASS` and `fastRestartPassed=true`.

## Production proof status

Confirmed on exact build `7e24df486839c92f9c324cbd910efc00dfe7bc4d`:

- public HTTPS PWA;
- exact-main deployed build;
- public production smoke PASS;
- encrypted saved Binance Demo credential and reconnect;
- Chart and Positions server-truth smoke;
- Research server truth and safety locks;
- Fast restart proof PASS;
- M5 real ablation `COMPLETE`, safe, all-terminal, all-experiments-passed and evidence-complete;
- frozen OOS locked;
- real execution locked.

## Validation status

- PR #51 passed full Python regression, Ruff, shell syntax, deployment contract, active Linode runtime and continuity before squash merge.
- PR #52 passed the same required gates before squash merge.
- Exact #52 main build later passed hardened external production proof and public production smoke.
- No OOS edge claim is made from the development batch.

## Next exact tasks

1. Read and interpret the immutable per-treatment metrics for batch `abl_6c4a8eeb83a662894a3f2816`, comparing candle-only control against Delta/CVD treatments under the recorded fee/slippage assumptions.
2. Persist the interpretation as development evidence only; do not open frozen OOS or promote lifecycle state from ranking alone.
3. Add stacked/diagonal footprint imbalance candidates with causal definitions, deterministic emission, cheap screening and regression tests.
4. Add absorption/exhaustion and price/delta divergence candidate families.
5. Strengthen family-scale duplicate filtering/orchestration as generated-candidate volume grows.
6. Keep LOB reconstruction separate and keep real-money execution locked.

## Important constraints

- No API secrets in Git, chat, logs or browser persistent storage; withdrawal permission is never required.
- Deterministic risk has veto authority.
- Runtime and research persistence remain separate.
- Strategy versions/evidence are immutable.
- AI strategy generation does not execute arbitrary generated Python.
- Executed-trade order flow and resting LOB liquidity are separate data domains.
- Gapped/tampered order-flow data fails closed.
- Spot and USD-M futures must not be silently mixed.
- Same-candle still-forming footprint data cannot be used in candle decisions.
- Historical fixed research windows are not silently shifted to accommodate API retention.
- Development ranking or ablation wins are not promotion evidence.
- Generic research workers cannot open frozen OOS or exchange execution.
- High-frequency raw market ticks are data, not normal INFO service logs.

## Continuity system

Canonical continuity files are `AGENTS.md`, `PROJECT_STATE.md`, `ARCHITECTURE.md`, `DECISIONS.md`, `TODO.md`, `CHANGELOG.md`, `SESSION_HANDOFF.md`, and `docs/CONTINUITY_PROTOCOL.md`. Every meaningful coding session must update them when state changes.
