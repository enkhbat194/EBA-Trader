# EBA Trader — Session Handoff

_Last handoff prepared: 2026-09-01 (Asia/Ulaanbaatar)_

## Exact continuation point

Repository: `enkhbat194/EBA-Trader`

Canonical `main` before current PR #107:

`78fcb3d8ad4bc7eef559932bb836a4eedf251630`

Main commit:

`Strategy Factory v2: add existing-only D0 production loader`

Exact-main push workflows are green: Linode production bundle run 385 and Linode runtime checks
run 397 both passed. The production-bundle job also passed the full regression suite, Ruff,
shell/collector syntax and deployment contract.

PR #107 is the active audit-hardening branch. Do not run the production 406-candidate D0 pilot
until #107 exact-head checks pass and it is merged.

## Audit completed before further work

Merged PRs #104, #105 and #106 were re-reviewed at code, CI, production-proof and research-integrity
levels. Their exact-head required workflows had passed before merge. `main` contains no accidental
`PLACEHOLDER` content from the temporary #106 branch mistake.

The audit found two material pre-pilot infrastructure defects:

1. The low-fidelity warmup slicer could bridge the multi-day gaps between the 12 independently
   sampled M5 development windows. PR #107 now walks backward only through truly contiguous candles,
   so a temporal gap terminates warmup context.
2. `run_discovery_batch` could re-evaluate a terminal immutable trial after a compute-budget stop.
   A repeated measurement could then differ only in runtime `compute_ms` and collide with immutable
   evidence. PR #107 now reuses matching terminal evaluated/rejected trials without evaluator
   execution or new compute accounting; only new/declared trials consume the current compute budget.

Focused regression tests cover multi-day gap isolation, partial-run resume and fully idempotent
terminal replay.

## Strategy Factory v2 merged state

- discovery authority remains `DISCOVERY_ONLY`;
- raw cap 500, executable pilot catalog 406, per-family cap 64, survivor cap 30;
- common D0 evaluator across 8 existing causal strategy engines;
- immutable campaign/candidate/trial accounting;
- immutable D0 candle/order-flow/composite hashes;
- explicit `INSPECTED_REUSABLE_DISCOVERY_DATA` provenance;
- one declared D0 stratum per inspected M5 development source window;
- all-strata completion required before behavioral representative selection;
- source binding rejects alternate corpus, tampered hashes and path escape;
- existing-only production loader cannot fetch, rebuild or extend missing evidence.

## Research status and hard locks

There is still no verified profitable strategy. SF1, SF2 and SF3 closed with zero promoted
candidates. D0 discovery ranking is not verification.

SF4 keeps exact `s3_vsm_s150` and `s3_cex_s075` parameters frozen for prospective replication using
only `2026-09-01T00:00:00Z` through `2026-09-13T00:00:00Z`. Evaluation before the declared end time
is fail-closed. SF3 evidence cannot be pooled into the replication result.

Hard locks:

- M5 Frozen OOS (`2026-08-15 -> 2026-08-22` UTC) remains sealed/not opened.
- Factory v2 D1 hidden confirmation remains sealed.
- SF4 cannot be evaluated before `2026-09-13T00:00:00Z`.
- Real Binance execution remains locked.
- Demo execution has no strategy-promotion authority.
- D0/development ranking has no promotion authority.
- Reused/inspected D0 data cannot be called fresh confirmation evidence.
- A discovery survivor is not a verified strategy and cannot transition durable StrategyLifecycle.

## Next exact task

1. Finish PR #107 exact-head CI; merge only if regression, Ruff, runtime, production-bundle,
   continuity and hygiene are all green.
2. On merged exact `main`, invoke the existing-only D0 loader against production research storage.
   If the complete inspected M5 materialization is absent, incomplete or hash-mismatched, stop and
   report the blocker without acquiring replacement evidence.
3. If it validates, record the immutable D0 declaration/dataset SHA and generate the deterministic
   406 candidates.
4. Execute low-fidelity trials across every declared stratum with resumable immutable accounting.
   Never rank candidates until required stratum coverage is terminal.
5. Aggregate selection-only metrics and behavioral clusters only after full coverage; keep raw
   candidate, unique spec, behavioral cluster and family counts distinct.

## Startup rule

Read `AGENTS.md`, `PROJECT_STATE.md`, `ARCHITECTURE.md`, `DECISIONS.md`, `TODO.md`, `CHANGELOG.md`,
this file, `BACKTEST_PROTOCOL.md`, `docs/CONTINUITY_PROTOCOL.md` and
`docs/STRATEGY_FACTORY_V2_DESIGN.md`; then query actual GitHub/production proof before editing.
