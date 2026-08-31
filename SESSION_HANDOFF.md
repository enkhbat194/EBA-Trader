# EBA Trader — Session Handoff

_Last handoff prepared: 2026-08-31 (Asia/Ulaanbaatar)_

## Exact continuation point

Repository: `enkhbat194/EBA-Trader`

Canonical production `main`:

`28c6d12f378433395118b024a0a4132c6d4edf5d`

Current working branch:

`sf2-fresh-corpus-evaluation-pipeline`

Exact production proof for `28c6d12...`: **SUCCESS**. Public production smoke also passed.

## What was completed

### SF1 closeout

- SF1 used its full preregistered 48/48 candidate budget and closed with zero verified candidates.
- Top `mr_48z15x00` had 10/12 baseline wins and 30 trades but negative mean return/expectancy and adjusted p ~0.246, so it was rejected.
- Raw direct order-flow impulse candidates also failed economically.
- No SF1 threshold retuning on the same evidence is allowed.

### SF2 preregistration and frozen signal engine

- PR #91 preregistered 12 fresh four-hour windows, 24 candidates and all fixed execution/statistical assumptions before fresh evidence was inspected.
- PR #92 implemented all four direct-signal families with next-open execution and fixed anti-churn holds.
- Exact main `28c6d12...` passed regression/runtime checks and external/public production proof.
- Fresh SF2 production windows had not yet been materialized/evaluated at that freeze point.

### Current branch: fresh SF2 evidence pipeline

Implemented on `sf2-fresh-corpus-evaluation-pipeline`:

- `src/eba_trader/sf2_development.py`
  - validates a custom SF2 materialization against the preregistered corpus;
  - uses fixed EMA 12/26 as comparison baseline;
  - evaluates all 24 candidates across all 12 fresh windows;
  - computes per-window/aggregate return, expectancy, drawdown, trades, costs and baseline deltas;
  - runs exact 4096 sign-flip permutations;
  - retains Bonferroni budget 48;
  - requires positive mean return, positive mean expectancy, >=30 trades, >=9/12 baseline wins, positive mean baseline delta and adjusted p <=0.05;
  - produces immutable development and validation reports with no OOS/promotion/live authority.
- `src/eba_trader/sf2_runtime.py`
  - invokes the existing resumable Binance USD-M archive materializer with the custom SF2 corpus and namespace `sf2_orderflow_dev`;
  - checks window count and SHA-256 feature integrity;
  - persists immutable evidence plus `/var/lib/eba-trader/research/sf2-development-latest.json`;
  - safely reuses terminal COMPLETE evidence rather than rerunning evaluation;
  - fails closed.
- `src/eba_trader/sf2_dashboard.py`
  - exposes only sanitized scalar research results;
  - rejects report paths outside the evidence root;
  - strips credential/path/dataset/evidence-ref fields;
  - has no mutation, lifecycle, OOS or execution authority.
- `src/eba_trader/research_dashboard.py`
  - now includes read-only `sf2` status.
- `scripts/run_m5_research_maintenance_once.sh`
  - runs SF2 independently from the legacy `absorption_020` robustness path;
  - includes SF2 failure in the maintenance fail-closed result.
- tests added for significance, runtime reuse/failure safety, dashboard sanitization and maintenance independence.

## What is proven

### Binance USD-M Futures Demo execution plumbing

- real Demo BTCUSDT BUY/SELL round trip previously passed;
- terminal proof is preserved;
- one-shot probe is disabled;
- pre/post position was flat;
- real money was not used;
- real execution remains locked.

This proves execution plumbing only, not strategy profitability.

### M5 / `absorption_020`

- structurally an EMA-crossover entry filter rather than an independent absorption strategy;
- only 4 development trades;
- negative expectancy;
- center not profitable;
- sample insufficient;
- robustness not verified.

Do not promote it and do not open M5 Frozen OOS.

### SF1

Production result remains:

- `validationState=NO_VERIFIED_CANDIDATE`;
- `verifiedCandidateCount=0`;
- Frozen OOS closed;
- real execution locked.

### SF2 signal implementation

Production main `28c6d12...` proves the preregistered signal logic and safety tests/deployment path, not the fresh-data performance result. Fresh SF2 performance must be obtained only after the current evaluation pipeline passes CI, merges and production maintenance runs.

## Fixed SF2 contract

- 24 active candidates;
- four families × six candidates;
- 12 fresh non-overlapping four-hour windows;
- no SF1 window reuse;
- 2026-08-01 smoke day excluded;
- all within M5 development `2026-07-01 -> 2026-08-15`;
- M5 Frozen OOS `2026-08-15 -> 2026-08-22` sealed;
- 4 bps fees;
- 1.5 bps slippage;
- one-bar signal-to-execution delay;
- minimum hold 2 bars;
- maximum hold 12 bars;
- 64 warmup bars;
- exact 4096 sign-flip null model;
- Bonferroni budget 48.

Development -> robustness eligibility requires every one of:

1. mean return > 0;
2. mean expectancy > 0;
3. total trades >= 30;
4. baseline beaten in >=9/12 windows;
5. mean return delta vs baseline > 0;
6. Bonferroni-adjusted exact p <= 0.05.

This still does not open Frozen OOS.

## Next exact task

1. Open PR for `sf2-fresh-corpus-evaluation-pipeline`.
2. Inspect exact-head full regression, Ruff, runtime, continuity, repository hygiene and production-bundle checks.
3. Fix every red check; do not merge red CI.
4. Merge only when green.
5. Verify exact merged `main` on Linode.
6. Wait for/run the normal versioned maintenance service so SF2 materializes the 12 preregistered archive windows and evaluates 24 × 12 candidates.
7. Read `/api/research/status` and inspect the sanitized `sf2` object.
8. If `verifiedCandidateCount=0`, close SF2 without promotion.
9. If a candidate is robustness-eligible, create a fixed candidate-appropriate robustness suite before any robustness result is observed.
10. Keep M5 Frozen OOS sealed and real-money execution locked throughout.

## Hard locks

- Legacy 2025 Frozen OOS remains locked.
- M5 Frozen OOS (`2026-08-15 -> 2026-08-22` UTC) remains sealed/not opened.
- Real Binance execution remains locked.
- Demo execution has no strategy-promotion authority.
- Development/ranking results have no promotion authority.
- Fresh development passing does not itself authorize Frozen OOS.
- Repeated analysis of already-inspected development data cannot be relabelled as fresh verification.

## Startup rule

Read `AGENTS.md`, `PROJECT_STATE.md`, `ARCHITECTURE.md`, `DECISIONS.md`, `TODO.md`, `CHANGELOG.md`, this file and `docs/CONTINUITY_PROTOCOL.md`; then query actual GitHub and production proof state before editing.
