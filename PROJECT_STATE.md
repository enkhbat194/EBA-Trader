# EBA Trader — Project State

_Last reconciled: 2026-09-01 (Asia/Ulaanbaatar)_

Actual GitHub code, workflow state and production proof override stale prose.

## Current goal

Build a research-first automated trading system that can discover many candidate ideas without
weakening verification quality. Broad discovery and strict verification are separate authorities.
Real-money execution remains locked.

## Canonical repository/runtime state

- Repository: `enkhbat194/EBA-Trader`
- Production URL: `https://eba-trader-172-236-150-62.sslip.io`
- Canonical `main`: `14472dee7224d5caff6819ea142f01ba6729d3a0`
- Main commit: `Strategy Factory v2: add immutable D0 dataset contract` (PR #103).
- Exact-main Linode runtime check: **PASS**.
- Exact-main SF2 production evidence proof: **PASS**.
- PR #104 is the current Strategy Factory v2 low-fidelity orchestration work.
- Fast Momentum remains a paper/runtime test-bed, not a verified profitable strategy.
- Binance USD-M Futures Demo execution plumbing is execution proof only.
- M5 Frozen OOS (`2026-08-15 -> 2026-08-22` UTC): **SEALED / NOT OPENED**.
- Real-money execution: **LOCKED**.

## Validation status

There is still **no verified profitable strategy**. SF1, SF2 and SF3 closed with zero promoted
candidates. SF4 is prospective replication only. Strategy Factory v2 is discovery-only. Demo,
development ranking and D0 survivor status have no verification authority.

### SF4 prospective replication

PR #99 merged as `755bf719587c274570bf5c7258aaff74eb94d693` and froze exact
`s3_vsm_s150` and `s3_cex_s075` hypotheses. Replication uses only new BTCUSDT USD-M data from
`2026-09-01T00:00:00Z` through `2026-09-13T00:00:00Z`. Evaluation is fail-closed before
`2026-09-13T00:00:00Z`. SF3 trades, returns, expectancy and p-values cannot be pooled into the
replication result, and parameters cannot be retuned.

### Strategy Factory v2

Merged state:

- `DISCOVERY_ONLY` authority;
- raw-candidate hard cap 500, per-family cap 64, survivor cap 30;
- 8 executable causal families with 406 declared raw candidate slots;
- immutable campaign/candidate/trial ledger;
- deterministic candidate/spec identity;
- common D0 evaluator/adaptor for all 8 families;
- normalized selection-only metrics and behavioral fingerprints;
- behavioral similarity/deduplication foundation;
- D0 discovery / D1 hidden confirmation / D2 robustness / D3 Frozen OOS zoning;
- PR #103 immutable D0 manifest with candle/order-flow/composite content hashes;
- explicit `INSPECTED_REUSABLE_DISCOVERY_DATA` provenance;
- fail-closed order-flow time/causality alignment;
- declared D0 temporal strata so low-fidelity racing cannot use chronological first-N selection.

PR #104 now adds the next safe layer: deterministic per-stratum dataset identities, causal warmup
slices with trading beginning exactly at the declared stratum boundary, one-stratum ledgered
execution, all-strata completion accounting and behavioral deduplication only after full stratified
coverage. Rejected or incomplete candidates are not eligible for behavioral representative
selection.

## Verification quality gate — DO NOT LOWER

Historical SF2/SF3 minimum reference gates remain:

1. mean return > 0;
2. mean expectancy > 0;
3. total trades >= 30;
4. baseline beaten in at least 9 of 12 declared windows;
5. positive mean return delta versus baseline;
6. corrected significance threshold satisfied.

Factory v2 D0 metrics are selection-only and do not satisfy these gates. A later confirmation
protocol must account for broad-search history and use evidence that was not adaptively inspected
as D0.

## Safety invariants

- Discovery ranking has no promotion authority.
- A discovery survivor is not verified.
- Frozen OOS cannot be opened by discovery workflows.
- Reused/adaptively inspected data cannot be relabelled fresh evidence.
- Full candidate/search history must be accounted for when evaluating selection bias.
- Demo execution proof has no strategy-verification authority.
- Spot and USD-M futures data are never silently mixed.
- Executed footprint and resting order-book liquidity remain separate data planes.
- Gapped/tampered/missing-version research evidence fails closed.
- Real-money Binance execution remains disabled.

## Next exact tasks

1. Merge PR #104 only after exact-head regression, Ruff, runtime, production-bundle, continuity and
   hygiene checks are green.
2. Materialize/declare the actual production D0 dataset and immutable manifest from inspected,
   reusable discovery data only.
3. Generate the deterministic 406 candidates and ledger low-fidelity evaluations across every
   declared D0 temporal stratum.
4. Resume safely after compute-budget stops; do not rank candidates until required stratum coverage
   is complete.
5. Produce selection-only aggregate metrics and behavioral near-duplicate representatives while
   keeping raw candidate, unique spec, behavioral cluster and family counts distinct.
6. Keep D1 sealed until survivor specifications are frozen and a separate confirmation protocol is
   authorized.
7. Keep SF4 untouched until `2026-09-13T00:00:00Z`.
8. Keep Frozen OOS and real-money execution locked.

## Continuity protocol

New sessions read `AGENTS.md`, `PROJECT_STATE.md`, `ARCHITECTURE.md`, `DECISIONS.md`, `TODO.md`,
`CHANGELOG.md`, `SESSION_HANDOFF.md`, `BACKTEST_PROTOCOL.md` and
`docs/STRATEGY_FACTORY_V2_DESIGN.md`, then query actual GitHub/production state before editing.
