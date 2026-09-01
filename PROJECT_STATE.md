# EBA Trader — Project State

_Last reconciled: 2026-09-01 (Asia/Ulaanbaatar)_

Actual merged code, exact-build production evidence and latest explicit decision documents override stale prose.

## Current goal

Build a research-first automated trading system that can discover repeatable trading edges efficiently without weakening statistical or verification integrity. Broad discovery and strict verification remain separate authorities. Real-money execution remains locked.

## Canonical repository/runtime state

- Repository: `enkhbat194/EBA-Trader`
- Production URL: `https://eba-trader-172-236-150-62.sslip.io`
- Engine baseline before this documentation reconciliation: `0f3ee0745b643abeda3fb9c796f7d6c1a219f6a8`.
- PR #109 merged the resume-safe Strategy Factory v2 D0 pilot campaign runner.
- PR #110 merged source-provenance hardening: the production runner derives the source SHA from the actual clean Git checkout and fails closed on an expected-SHA mismatch or dirty tracked tree.
- Exact production build `9b2d31efd00981282acc405b944d0b913960fca1` passed D0 existing-source proof after PR #109. The subsequent #110 build must likewise pass exact-build production proof before campaign execution.
- Fast Momentum remains a paper/runtime test-bed, not a verified profitable strategy.
- Binance USD-M Futures Demo execution plumbing is execution proof only.
- M5 Frozen OOS (`2026-08-15 -> 2026-08-22` UTC): **SEALED / NOT OPENED**.
- Real-money execution: **LOCKED**.

## Validation status

There is still **no verified profitable strategy**. SF1, SF2 and SF3 closed with zero promoted candidates. SF4 is prospective replication only. Strategy Factory v2 is discovery-only. Demo, development ranking and D0 survivor status have no verification authority.

### SF4 prospective replication

PR #99 froze exact `s3_vsm_s150` and `s3_cex_s075` hypotheses. Replication uses only new BTCUSDT USD-M data from `2026-09-01T00:00:00Z` through `2026-09-13T00:00:00Z`. Evaluation is fail-closed before `2026-09-13T00:00:00Z`. SF3 evidence cannot be pooled into the replication result and parameters cannot be retuned.

### Strategy Factory v2 merged state

- `DISCOVERY_ONLY` authority;
- raw-candidate hard cap 500, per-family cap 64, survivor cap 30;
- 8 executable causal families with an exact deterministic 406-candidate pilot catalog;
- immutable campaign/candidate/trial ledger;
- deterministic candidate/spec identity;
- common D0 evaluator/adaptor for all 8 families;
- normalized selection-only metrics and behavioral fingerprints;
- behavioral similarity/deduplication foundation;
- D0 discovery / D1 hidden confirmation / D2 robustness / D3 Frozen OOS zoning;
- immutable D0 manifest with candle/order-flow/composite content hashes;
- explicit `INSPECTED_REUSABLE_DISCOVERY_DATA` provenance;
- 12 declared temporal strata bound to the already-inspected default M5 development corpus;
- D0 warmup cannot bridge independently sampled temporal windows;
- compute-budget resume reuses immutable terminal trials without re-evaluation;
- existing-only D0 loader cannot fetch, rebuild or extend missing evidence;
- campaign definition binds D0 declaration/dataset hashes, catalog seed/count, warmup, behavioral threshold and exact source checkout;
- production source attribution comes from a clean actual checkout, not operator-supplied provenance text.

## Exact production D0 evidence

Exact production build `9b2d31efd00981282acc405b944d0b913960fca1` passed D0 proof with:

- source kind: `INSPECTED_M5_DEVELOPMENT_CORPUS`;
- materialization ID: `m5corpusmat_25007f47e456b5f2d42ef16b`;
- policy ID: `m5policy_3b90b051bd27eeab0e79be74`;
- corpus ID: `m5corpus_28c69171b3657be02bffd556`;
- declaration SHA-256: `88365779d6821c1fb30372148bbcedbfadf11471843f57722723286a43cbc77c`;
- dataset SHA-256: `aa13bcfc111c00f6da19621353a3ca8044f58eca1ab95e837d9490a205aa72eb`;
- candle SHA-256: `6368c9f41ff635d2474860a8d4579fc00e57488871020a9df38222f32d9f4744`;
- order-flow SHA-256: `3398d17c48dd282c86a13a3ccf9daafcd2784e1e64732bb52c29b9b294e82da3`;
- rows: 2,880;
- windows/strata: 12 / 12;
- authority: `DISCOVERY_ONLY`;
- provenance: `INSPECTED_REUSABLE_DISCOVERY_DATA`;
- fresh confirmation evidence: false;
- verification authority: false;
- D1 opened: false;
- Frozen OOS opened: false;
- live execution allowed: false.

The data-source and campaign-orchestration blockers are closed. The remaining production blocker is a safe execution path that pins one exact clean build for the campaign and prevents the five-minute auto-updater from mutating the checkout while a campaign process is active.

## Verification quality gate — DO NOT LOWER

Historical SF2/SF3 minimum reference gates remain:

1. mean return > 0;
2. mean expectancy > 0;
3. total trades >= 30;
4. baseline beaten in at least 9 of 12 declared windows;
5. positive mean return delta versus baseline;
6. corrected significance threshold satisfied.

Factory v2 D0 metrics are selection-only and do not satisfy these gates. A later confirmation protocol must account for broad-search history and use evidence that was not adaptively inspected as D0.

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

1. Require exact-build production proof for the latest merged source-provenance hardening.
2. Add the minimum production-safe D0 campaign execution mechanism with exact-build pinning and an updater/concurrency guard; do not expose a public unauthenticated trigger.
3. Run/resume the exact 406-candidate catalog across all 12 D0 strata only after that guard is proven.
4. Never rank incomplete candidates; require terminal required-stratum coverage before aggregate selection metrics.
5. Build behavioral near-duplicate clusters while keeping raw candidate, unique spec, behavioral cluster and family counts distinct.
6. Continue higher-fidelity D0 racing only under the predeclared diversity/search contract; D0 remains selection-only.
7. Freeze at most 30 survivors before any separately authorized D1 access. Zero survivors is valid.
8. Keep SF4 untouched until `2026-09-13T00:00:00Z`.
9. Keep Frozen OOS and real-money execution locked.

## Continuity protocol

New sessions read `AGENTS.md`, `PROJECT_STATE.md`, `ARCHITECTURE.md`, `DECISIONS.md`, `TODO.md`, `CHANGELOG.md`, `SESSION_HANDOFF.md`, `BACKTEST_PROTOCOL.md` and `docs/STRATEGY_FACTORY_V2_DESIGN.md`, then query actual GitHub/production state before editing.
