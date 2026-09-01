# EBA Trader — Session Handoff

_Last handoff prepared: 2026-09-01 (Asia/Ulaanbaatar)_

## Exact continuation point

Repository: `enkhbat194/EBA-Trader`

Canonical `main` before the current D0 dataset-contract PR:

`4c5a6a9fe30f29b772a5c2fe4d1e99b38b4262b1`

Main commit:

`Strategy Factory v2: add common D0 evaluator adapters (#102)`

Exact-main production/continuity proof is green, including external production proof. No open PR
existed before the current branch was created.

## What was completed

### Research phases and safety

SF1, SF2 and SF3 remain closed with `NO_VERIFIED_CANDIDATE`. Frozen OOS was not opened. Real-money
execution remains locked. Demo execution is plumbing proof only and has no verification authority.

SF4 keeps exact `s3_vsm_s150` and `s3_cex_s075` parameters frozen for prospective replication using
only `2026-09-01T00:00:00Z` through `2026-09-13T00:00:00Z`. Evaluation before the end time is
fail-closed. SF3 evidence cannot be pooled into the replication result.

### Strategy Factory v2

The discovery-only foundation, 8-family/406-candidate pilot catalog and common D0 evaluator are
merged. PR #102 added:

- one evaluator/adaptor path for all 8 existing causal engines;
- common selection-only metrics;
- actual behavioral fingerprints from signals/trades/exposure/turnover;
- fail-closed invalid/zero-opportunity handling;
- `run_discovery_batch` ledger integration with dataset SHA, source SHA, fidelity and compute time.

The current branch advances the next missing boundary: immutable D0 input identity. It adds a
versioned manifest that hashes candle and executed-order-flow content, labels the data explicitly as
`INSPECTED_REUSABLE_DISCOVERY_DATA`, rejects time-misaligned/non-causal order-flow rows and declares
temporal strata for non-first-N low-fidelity racing.

## Next exact task

Finish and merge the D0 dataset-contract PR only after exact-head checks are green. Then materialize
the actual production D0 dataset, record its immutable composite hash, generate the deterministic
406 candidates, and evaluate every low-fidelity candidate across all declared temporal strata.
Every inspected trial must enter the immutable discovery ledger.

After low-fidelity evaluation, compute behavioral clusters and keep raw candidate, unique spec,
behavioral cluster and independent family counts distinct. Higher-fidelity D0 racing may use diverse
representatives only. D1 must remain sealed until survivor specs are frozen under separate
authority.

## Hard locks

- M5 Frozen OOS (`2026-08-15 -> 2026-08-22` UTC) remains sealed/not opened.
- SF4 cannot be evaluated before `2026-09-13T00:00:00Z`.
- Real Binance execution remains locked.
- Demo execution has no strategy-promotion authority.
- D0/development ranking has no promotion authority.
- Reused/inspected D0 data cannot be called fresh confirmation evidence.
- A discovery survivor is not a verified strategy and cannot transition durable StrategyLifecycle.

## Startup rule

Read `AGENTS.md`, `PROJECT_STATE.md`, `ARCHITECTURE.md`, `DECISIONS.md`, `TODO.md`, `CHANGELOG.md`,
this file, `BACKTEST_PROTOCOL.md`, `docs/CONTINUITY_PROTOCOL.md` and
`docs/STRATEGY_FACTORY_V2_DESIGN.md`; then query actual GitHub/production proof before editing.
