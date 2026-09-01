# EBA Trader — Session Handoff

_Last handoff prepared: 2026-09-01 (Asia/Ulaanbaatar)_

## Exact continuation point

Repository: `enkhbat194/EBA-Trader`

Engine baseline before this documentation reconciliation:

`425952afbf1a1f057ad659670004c8defcd7edd5`

PR #109, PR #110 and PR #112 are merged. PR #109 added deterministic resume-safe all-strata D0 pilot orchestration. PR #110 binds source provenance to the actual clean production checkout. PR #112 coordinates the five-minute auto-updater and D0 production wrapper through one shared nonblocking checkout lock.

No D0 campaign has been executed yet. No public or automatic campaign trigger was added.

## What was completed

1. Reconciled canonical state against actual merged code and exact production evidence.
2. Confirmed the existing inspected production D0 source: 2,880 rows across 12 windows/12 strata, with discovery-only authority.
3. Merged PR #109 after full exact-head regression, Ruff, runtime, production-bundle, hygiene and continuity checks passed.
4. Confirmed exact production build `9b2d31efd00981282acc405b944d0b913960fca1` retained the D0 source hashes and all downstream locks.
5. Found and fixed a source-provenance weakness: operator text can no longer label the immutable campaign with an arbitrary source SHA. PR #110 derives the SHA from the actual clean checkout and rejects dirty/mismatched provenance.
6. Found and fixed the production checkout race with the five-minute updater. PR #112 makes the updater and D0 wrapper share `/run/lock/eba-trader-runtime-mutation.lock`; the updater skips safely while research holds the lock and retries on its normal timer.
7. Added `scripts/run_sfv2_d0_pilot_production_once.sh`, an operator-only exact-build production wrapper using canonical research paths and the actual clean checkout SHA.
8. Re-audited low-fidelity materialization/reporting: supplied D0 content is rehashed against the manifest, temporal-gap warmup stays isolated, duplicate stratum trials fail, and a candidate is complete only after terminal coverage of every declared stratum.

## Exact D0 proof

Latest completed exact proof before the current final deployment cycle was production build `9b2d31efd00981282acc405b944d0b913960fca1`:

- source kind: `INSPECTED_M5_DEVELOPMENT_CORPUS`;
- materialization ID: `m5corpusmat_25007f47e456b5f2d42ef16b`;
- policy ID: `m5policy_3b90b051bd27eeab0e79be74`;
- corpus ID: `m5corpus_28c69171b3657be02bffd556`;
- declaration SHA-256: `88365779d6821c1fb30372148bbcedbfadf11471843f57722723286a43cbc77c`;
- dataset SHA-256: `aa13bcfc111c00f6da19621353a3ca8044f58eca1ab95e837d9490a205aa72eb`;
- candle SHA-256: `6368c9f41ff635d2474860a8d4579fc00e57488871020a9df38222f32d9f4744`;
- order-flow SHA-256: `3398d17c48dd282c86a13a3ccf9daafcd2784e1e64732bb52c29b9b294e82da3`;
- row count: 2,880;
- windows/strata: 12 / 12;
- authority: `DISCOVERY_ONLY`;
- provenance: `INSPECTED_REUSABLE_DISCOVERY_DATA`;
- fresh confirmation evidence: false;
- verification authority: false;
- D1/Frozen OOS/live: closed/closed/locked.

Require a successful exact-production proof for the final merged main build before campaign invocation.

## Strategy Factory v2 state

- raw cap 500; exact pilot catalog 406; per-family cap 64; survivor cap 30;
- 8 existing causal strategy families;
- common causal evaluator with fees/slippage;
- immutable campaign/candidate/trial ledger;
- resume reuses terminal trials without re-evaluation;
- temporal-gap warmup protection active;
- production D0 source proven;
- all-strata campaign orchestration merged;
- actual clean-checkout provenance binding merged;
- automatic-update checkout race guarded in merged code;
- D1 remains sealed and no survivor freeze has occurred.

## Research status and hard locks

There is still no verified profitable strategy. SF1, SF2 and SF3 closed with zero promoted candidates. D0 discovery ranking is not verification.

SF4 keeps exact `s3_vsm_s150` and `s3_cex_s075` parameters frozen for prospective replication using only `2026-09-01T00:00:00Z` through `2026-09-13T00:00:00Z`. Evaluation before `2026-09-13T00:00:00Z` is fail-closed. SF3 evidence cannot be pooled into the replication result.

Hard locks:

- M5 Frozen OOS remains sealed/not opened.
- Factory v2 D1 hidden confirmation remains sealed.
- SF4 cannot be evaluated before `2026-09-13T00:00:00Z`.
- Real Binance execution remains locked.
- Demo execution has no strategy-promotion authority.
- D0/development ranking has no promotion authority.
- Reused/inspected D0 data cannot be called fresh confirmation evidence.
- A discovery survivor is not a verified strategy and cannot transition durable StrategyLifecycle.

## Next exact task

1. Confirm exact production proof for the final merged main build containing PR #112 and this continuity reconciliation.
2. When an authorized Linode shell path is available, invoke only `scripts/run_sfv2_d0_pilot_production_once.sh`; do not create an unauthenticated public trigger as an access workaround.
3. Run/resume the exact 406 candidates across all 12 D0 strata while the shared checkout lock is held.
4. Never rank incomplete candidates; aggregate selection-only economics/activity/cost/drawdown/benchmark metrics only after terminal all-strata coverage.
5. Behavioral-deduplicate while preserving raw candidate, unique-spec, cluster and family counts, then continue only under the existing D0 diversity/racing contract.
6. Keep D1, Frozen OOS, SF4 pre-unlock evaluation and real-money execution closed.

## Startup rule

Read `AGENTS.md`, `PROJECT_STATE.md`, `ARCHITECTURE.md`, `DECISIONS.md`, `TODO.md`, `CHANGELOG.md`, this file, `BACKTEST_PROTOCOL.md`, `docs/CONTINUITY_PROTOCOL.md` and `docs/STRATEGY_FACTORY_V2_DESIGN.md`; then query actual GitHub/production proof before editing.
