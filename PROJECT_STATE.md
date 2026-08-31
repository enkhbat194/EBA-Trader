# EBA Trader — Project State

_Last reconciled: 2026-09-01 (Asia/Ulaanbaatar)_

Actual GitHub code, workflow state and Linode production proof override stale prose.

## Current goal

Build a research-first automated trading system that can discover many candidate ideas without
weakening verification quality. Broad discovery and strict verification are separate authorities.
Real-money execution remains locked.

## Canonical repository/runtime state

- Repository: `enkhbat194/EBA-Trader`
- Production URL: `https://eba-trader-172-236-150-62.sslip.io`
- Canonical production `main`: `423cf92225cbc75fb8bf3d89d2eddc1d2fba21a6`
- Main commit: `SF3: evaluate fresh preregistered development evidence`
- Exact-build SF3 production evidence proof: **PASS**.
- Linode runtime checks: **PASS**.
- Linode production bundle: **PASS**.
- Public production smoke: **PASS**.
- Fast Momentum remains a paper/runtime test-bed, not a verified profitable strategy.
- Binance USD-M Futures Demo execution plumbing has a verified demo round-trip.
- M5 Frozen OOS (`2026-08-15 -> 2026-08-22` UTC): **SEALED / NOT OPENED**.
- Real-money execution: **LOCKED**.

## Closed research phases

### Historical M5

`absorption_020` was rejected: sparse sample, negative expectancy and no robustness proof. It was
structurally an EMA-entry filter rather than an independent absorption signal generator.

### SF1 — CLOSED

- 48 preregistered candidates across ATR, Donchian, z-score mean reversion and direct order-flow.
- 12 development windows.
- Production result: `NO_VERIFIED_CANDIDATE`, `0` verified.
- No post-hoc extension on inspected SF1 evidence.

### SF2 — CLOSED

- 24 preregistered candidates in four independent direct-signal families.
- 12 fresh development windows.
- Production result: `NO_VERIFIED_CANDIDATE`, `0/24` verified.
- Top `s2_fpc_s030` remained economically negative and failed the fixed gate.
- Closed without Frozen OOS access or promotion.

### SF3 — CLOSED

SF3 used 24 candidates in four families across 12 new four-hour BTCUSDT USD-M development windows.
Fixed research assumptions included 4 bps fees, 1.5 bps adverse slippage, causal next-open
execution, a planned multiple-testing budget of 48, exact 4096 sign-flip tests and the unchanged
30-trade / 9-of-12 / positive-return / positive-expectancy gate.

Exact production result on `423cf922...`:

- `validationState=NO_VERIFIED_CANDIDATE`;
- `verifiedCandidateCount=0`;
- top development-ranked `s3_vsm_s150` had 10/12 baseline-beating windows but negative mean return,
  negative expectancy and only 11 trades;
- `s3_cex_s075` was economically positive and had adjusted p `0.046875`, but only 4 trades;
- `s3_cex_s065` was economically positive but had only 1 trade;
- sparse compression/expansion outcomes are hypothesis clues only, not verification evidence.

No SF3 candidate may be rescued by lowering the 30-trade minimum or tuning thresholds on the same
inspected evidence.

## Validation status

The current canonical production validation result is **no verified strategy**. SF1, SF2 and SF3
are closed development phases with zero promoted candidates. Frozen OOS has not been opened, and
real execution remains locked. Strategy Factory v2 work is infrastructure-only until its own
foundation CI passes and a later, separately authorized discovery pilot is declared.

## Current work — Strategy Factory v2 foundation

Working branch:

`strategy-factory-v2-discovery-foundation`

Reason for the change: verification quality is strong, but discovery throughput/diversity is the
current bottleneck. SF1/SF2/SF3 proved that small fixed batches can be audited correctly, while
also showing that repeatedly hand-authoring 24-candidate phases is not an efficient long-term
search architecture.

Strategy Factory v2 is being added **in front of**, not instead of, the current verification
pipeline.

Current foundation scope:

- discovery-only authority contract;
- hard first-pilot raw candidate cap of 500;
- per-family cap of 64;
- discovery-survivor cap of 30;
- deterministic candidate/spec identity;
- immutable search-trial ledger with dataset and source-code identity;
- behavioral fingerprint and near-duplicate filtering;
- D0 discovery / D1 hidden confirmation / D2 robustness reserve / D3 Frozen OOS zoning;
- explicit rule that discovery survivors cannot transition StrategyLifecycle;
- no Frozen OOS, Demo-promotion or real-execution authority.

Canonical design document:

`docs/STRATEGY_FACTORY_V2_DESIGN.md`

Pilot contract:

`config/strategy_factory_v2_pilot_v1.json`

## Verification quality gate — DO NOT LOWER

Broad discovery is not verification. Any candidate that eventually enters the current EBA
verification pipeline must still satisfy its declared economic, activity, cross-window,
multiple-testing and robustness requirements before Frozen OOS can be considered.

The historical SF2/SF3 development gate remains a useful minimum reference:

1. mean return > 0;
2. mean expectancy > 0;
3. total trades >= 30;
4. baseline beaten in at least 9 of 12 declared windows;
5. positive mean return delta versus baseline;
6. corrected significance threshold satisfied.

A future Factory v2 confirmation protocol may use a more suitable hierarchical/dependency-aware
multiple-testing method, but it may not weaken promotion integrity.

## Safety invariants

- Discovery ranking has no promotion authority.
- A discovery survivor is not `BACKTESTED` or verified.
- Frozen OOS cannot be opened by discovery workflows.
- Reused/adaptively inspected data cannot be relabelled fresh confirmation evidence.
- Full candidate/search history must be accounted for when evaluating selection bias.
- Demo execution proof has no strategy-verification authority.
- Runtime trade persistence remains separate from research persistence.
- Spot and USD-M futures data are never silently mixed.
- Executed footprint and resting order-book liquidity remain separate data planes.
- Gapped/tampered/missing-version research evidence fails closed.
- Real-money Binance execution remains disabled.

## Next exact tasks

1. Finish Strategy Factory v2 foundation code and regression tests on the working branch.
2. Reconcile `BACKTEST_PROTOCOL.md`, `TODO.md` and decision records with lifecycle policy v2 and
   completed SF3 evidence.
3. Add pilot-contract validation that fails closed if discovery authority/caps/data-zone locks are
   weakened.
4. Add bounded candidate-family registration/generation and deterministic sampling infrastructure.
5. Add behavioral-cluster reporting and trial-accounting diagnostics.
6. Open a single foundation PR only after the package is coherent.
7. Fix all CI failures; merge only with exact-head regression/Ruff/runtime/continuity/hygiene checks
   green.
8. Do **not** run hidden confirmation, Frozen OOS or real execution as part of this foundation PR.

## Continuity protocol

New sessions read `AGENTS.md`, `PROJECT_STATE.md`, `ARCHITECTURE.md`, `DECISIONS.md`, `TODO.md`,
`CHANGELOG.md`, `SESSION_HANDOFF.md`, `BACKTEST_PROTOCOL.md` and
`docs/STRATEGY_FACTORY_V2_DESIGN.md`, then query actual GitHub/production state before editing.
