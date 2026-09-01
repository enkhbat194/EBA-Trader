# EBA Trader — Project State

_Last reconciled: 2026-09-01 (Asia/Ulaanbaatar)_

Actual GitHub code, workflow state and production proof override stale prose.

## Current goal

Build a research-first automated trading system that can discover many candidate ideas without
weakening verification quality. Broad discovery and strict verification remain separate
authorities. Real-money execution remains locked.

## Canonical repository/runtime state

- Repository: `enkhbat194/EBA-Trader`
- Production URL: `https://eba-trader-172-236-150-62.sslip.io`
- Canonical `main`: `78fcb3d8ad4bc7eef559932bb836a4eedf251630`
- Main commit: `Strategy Factory v2: add existing-only D0 production loader` (PR #106).
- Exact-main push workflow `Linode production bundle` run 385: **PASS**.
- Exact-main push workflow `Linode runtime checks` run 397: **PASS**.
- Exact-main regression, Ruff, shell/collector syntax and deployment contract: **PASS**.
- PR #107 is the active audit-hardening work before any production D0 pilot execution.
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
`2026-09-13T00:00:00Z`. SF3 evidence cannot be pooled into the replication result and parameters
cannot be retuned.

### Strategy Factory v2 merged state

- `DISCOVERY_ONLY` authority;
- raw-candidate hard cap 500, per-family cap 64, survivor cap 30;
- 8 executable causal families with 406 declared raw candidate slots;
- immutable campaign/candidate/trial ledger;
- deterministic candidate/spec identity;
- common D0 evaluator/adaptor for all 8 families;
- normalized selection-only metrics and behavioral fingerprints;
- behavioral similarity/deduplication foundation;
- D0 discovery / D1 hidden confirmation / D2 robustness / D3 Frozen OOS zoning;
- immutable D0 manifest with candle/order-flow/composite content hashes;
- explicit `INSPECTED_REUSABLE_DISCOVERY_DATA` provenance;
- 12 declared temporal strata bound to the already-inspected default M5 development corpus;
- PR #104 stratified low-fidelity orchestration and all-strata completeness accounting;
- PR #105 exact inspected-M5 source binding, file-hash validation and path containment;
- PR #106 existing-only production loader that cannot fetch/rebuild missing evidence.

## Audit result before production pilot

The post-merge audit of #104-#106 verified their exact-head CI and exact-main production bundle,
and confirmed no accidental `PLACEHOLDER` content exists on `main`. It also found two pre-pilot
infrastructure defects that must be fixed before running the 406-candidate campaign:

1. D0 warmup could walk backward across the multi-day gaps between the 12 independently sampled
   M5 development windows, making discontinuous observations appear adjacent.
2. A compute-budget resume could re-evaluate an already-terminal immutable trial, allowing runtime
   `compute_ms` variation to collide with the previously recorded immutable result.

PR #107 fixes both fail-closed: warmup stops at temporal discontinuities, and terminal trials are
reused without evaluator execution or additional compute accounting. Production pilot execution
remains blocked until #107 exact-head checks are green and the PR is merged.

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

1. Merge PR #107 only after exact-head regression, Ruff, runtime, production-bundle, continuity and
   hygiene checks are green.
2. On exact merged `main`, use the existing-only loader against production research storage. If the
   complete inspected M5 corpus is absent or mismatched, stop without acquiring replacement data.
3. If the existing corpus validates, record the immutable D0 source declaration/dataset SHA.
4. Generate the deterministic 406 candidates and ledger low-fidelity trials across every declared
   D0 temporal stratum, resuming safely after compute-budget stops.
5. Do not rank incomplete candidates; aggregate selection-only metrics only after required stratum
   coverage is terminal.
6. Cluster behavioral near-duplicates while keeping raw candidate, unique spec, behavioral cluster
   and family counts distinct.
7. Keep D1 sealed until survivor specifications are frozen and a separate confirmation protocol is
   authorized.
8. Keep SF4 untouched until `2026-09-13T00:00:00Z`.
9. Keep Frozen OOS and real-money execution locked.

## Continuity protocol

New sessions read `AGENTS.md`, `PROJECT_STATE.md`, `ARCHITECTURE.md`, `DECISIONS.md`, `TODO.md`,
`CHANGELOG.md`, `SESSION_HANDOFF.md`, `BACKTEST_PROTOCOL.md` and
`docs/STRATEGY_FACTORY_V2_DESIGN.md`, then query actual GitHub/production state before editing.
