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
- Canonical `main` before the current D0 dataset-contract PR: `4c5a6a9fe30f29b772a5c2fe4d1e99b38b4262b1`
- Main commit: `Strategy Factory v2: add common D0 evaluator adapters (#102)`.
- Exact-main continuity guard: **PASS**.
- Exact-main Linode external production proof: **PASS**.
- No open pull requests existed before the current D0 dataset-contract branch was created.
- Fast Momentum remains a paper/runtime test-bed, not a verified profitable strategy.
- Binance USD-M Futures Demo execution plumbing has a verified demo round-trip only.
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

Merged foundation and pilot state:

- `DISCOVERY_ONLY` authority;
- raw-candidate hard cap 500, per-family cap 64, survivor cap 30;
- immutable campaign/candidate/trial ledger;
- deterministic candidate/spec identity;
- dataset SHA and source-code SHA accounting;
- behavioral fingerprints/similarity/deduplication;
- D0 discovery / D1 hidden confirmation / D2 robustness / D3 Frozen OOS zoning;
- 8 executable causal families with 406 declared raw candidate slots;
- common D0 evaluator/adaptor merged in PR #102;
- normalized selection-only metrics and actual behavioral fingerprints;
- static/sanity failure closes invalid or zero-opportunity evaluations;
- `run_discovery_batch` integration records immutable dataset/source/fidelity/compute evidence.

Current work adds the missing immutable D0 dataset-input contract: deterministic content hashing,
explicit inspected/reusable provenance, causal order-flow alignment checks and declared temporal
strata so low-fidelity racing cannot silently become chronological first-N selection.

## Verification quality gate — DO NOT LOWER

Broad discovery is not verification. Historical SF2/SF3 minimum reference gates remain:

1. mean return > 0;
2. mean expectancy > 0;
3. total trades >= 30;
4. baseline beaten in at least 9 of 12 declared windows;
5. positive mean return delta versus baseline;
6. corrected significance threshold satisfied.

Factory v2 may later use a separately preregistered confirmation protocol, but no method may weaken
promotion integrity or relabel inspected D0 evidence as fresh confirmation evidence.

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

1. Merge the immutable D0 dataset contract only after exact-head regression, Ruff, runtime,
   production-bundle, continuity and hygiene checks are green.
2. Materialize/declare the actual production D0 dataset and its immutable hash using inspected,
   reusable discovery data only; never call it fresh evidence.
3. Evaluate the deterministic 406-candidate pilot across every declared temporal stratum rather
   than chronological first-N racing.
4. Aggregate selection-only D0 metrics while ledgering every inspected candidate/dataset/fidelity
   trial.
5. Run behavioral near-duplicate clustering and keep raw/unique/cluster/family counts distinct.
6. Keep D1 hidden confirmation sealed until survivor specifications are frozen and a separate
   confirmation protocol is authorized.
7. Keep SF4 untouched until `2026-09-13T00:00:00Z`.
8. Keep Frozen OOS and real-money execution locked.

## Continuity protocol

New sessions read `AGENTS.md`, `PROJECT_STATE.md`, `ARCHITECTURE.md`, `DECISIONS.md`, `TODO.md`,
`CHANGELOG.md`, `SESSION_HANDOFF.md`, `BACKTEST_PROTOCOL.md` and
`docs/STRATEGY_FACTORY_V2_DESIGN.md`, then query actual GitHub/production state before editing.
