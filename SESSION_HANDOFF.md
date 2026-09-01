# EBA Trader — Session Handoff

_Last handoff prepared: 2026-09-01 (Asia/Ulaanbaatar)_

## Exact continuation point

Repository: `enkhbat194/EBA-Trader`

Canonical `main` before current PR #104:

`14472dee7224d5caff6819ea142f01ba6729d3a0`

Main commit:

`Strategy Factory v2: add immutable D0 dataset contract`

Exact-main Linode runtime and production evidence proof are green. PR #104 is the active
low-fidelity D0 orchestration branch.

## What was completed

### Research phases and safety

SF1, SF2 and SF3 remain closed with `NO_VERIFIED_CANDIDATE`. Frozen OOS was not opened. Real-money
execution remains locked. Demo execution is plumbing proof only and has no verification authority.

SF4 keeps exact `s3_vsm_s150` and `s3_cex_s075` parameters frozen for prospective replication using
only `2026-09-01T00:00:00Z` through `2026-09-13T00:00:00Z`. Evaluation before the end time is
fail-closed. SF3 evidence cannot be pooled into the replication result.

### Strategy Factory v2 merged state

The discovery-only foundation, 8-family/406-candidate pilot catalog, common D0 evaluator and
immutable D0 dataset contract are merged. PR #103 added deterministic candle/order-flow/composite
hashes, explicit `INSPECTED_REUSABLE_DISCOVERY_DATA` provenance, causal alignment checks and
declared temporal strata.

### Current PR #104

PR #104 adds:

- recomputation of the parent D0 manifest before any pilot slice can run;
- causal pre-stratum warmup while trading starts exactly at the declared stratum boundary;
- immutable per-stratum dataset SHA derived from parent identity, stratum, warmup and content;
- a ledgered one-stratum execution wrapper using the common D0 evaluator;
- all-strata completion accounting;
- selection-only metric aggregation across completed strata;
- behavioral fingerprint combination across all declared strata;
- near-duplicate representative filtering only for complete, non-rejected candidates.

Initial PR #104 regression tests passed. Ruff found only import formatting/line-length issues, which
were fixed on the branch before continuing.

## Next exact task

Finish PR #104 exact-head CI and merge only when regression, Ruff, runtime, production-bundle,
continuity and hygiene checks are green. Then materialize/declare the actual production D0 dataset,
generate the deterministic 406 candidates, and execute resumable low-fidelity D0 evaluation across
every declared temporal stratum. Do not rank incomplete candidates.

After complete low-fidelity coverage, report raw candidates, unique specs, behavioral clusters and
independent families separately. Higher-fidelity D0 racing may use diverse representatives only.
D1 remains sealed until survivor specs are frozen under separate authority.

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
