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
- Canonical `main`: `f9161ab091093d69f725b6b96ab6018443aaa6da`
- Main commit: `Strategy Factory v2: register executable pilot family catalog (#100)`
- Linode runtime checks on exact main: **PASS**.
- Linode production bundle on exact main: **PASS**.
- Continuity guard on exact main: **PASS**.
- Repository hygiene on exact main: **PASS**.
- No open pull requests at this reconciliation point.
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

Production result:

- `validationState=NO_VERIFIED_CANDIDATE`;
- `verifiedCandidateCount=0`;
- `s3_vsm_s150` had 10/12 baseline-beating windows but negative mean return, negative expectancy
  and only 11 trades;
- `s3_cex_s075` was economically positive and had adjusted p `0.046875`, but only 4 trades;
- `s3_cex_s065` was economically positive but had only 1 trade;
- sparse compression/expansion outcomes are hypothesis clues only, not verification evidence.

No SF3 candidate may be rescued by lowering the 30-trade minimum or tuning thresholds on the same
inspected evidence.

## SF4 — prospective replication track

PR #99 merged as `755bf719587c274570bf5c7258aaff74eb94d693` and preregistered two exact SF3
hypotheses for prospective replication:

- `s3_vsm_s150` -> `s4_vsm_s150_replication`;
- `s3_cex_s075` -> `s4_cex_s075_replication`.

Rules are fail-closed:

- parameters are copied exactly and cannot be retuned;
- replication uses only new BTCUSDT USD-M data from `2026-09-01T00:00:00Z` through
  `2026-09-13T00:00:00Z`;
- evaluation is locked until `2026-09-13T00:00:00Z`;
- SF3 trades, returns, expectancy and p-values cannot be pooled into the replication result;
- the conservative prior search budget of 48 remains carried forward for multiplicity control;
- the unchanged minimum economic/activity/statistical gate remains in force;
- passing replication would justify only a separately preregistered robustness phase, not Frozen
  OOS access.

SF4 has no Demo, live, real-execution or promotion authority.

## Strategy Factory v2 — merged discovery-only foundation and pilot catalog

The generic discovery foundation is merged. The first executable family catalog was merged in PR
#100 on exact main `f9161ab...`.

Current pilot contract:

- authority: `DISCOVERY_ONLY`;
- hard raw-candidate cap: 500;
- hard per-family cap: 64;
- hard survivor cap: 30;
- deterministic candidate/spec identity;
- immutable search-trial ledger with dataset and source-code identity;
- behavioral fingerprint and near-duplicate filtering;
- D0 discovery / D1 hidden confirmation / D2 robustness reserve / D3 Frozen OOS zoning;
- discovery survivors cannot transition durable StrategyLifecycle;
- no Frozen OOS, Demo-promotion or real-execution authority.

The first executable pilot catalog currently declares **8 economically distinct families and 406
raw candidate slots**, intentionally leaving 94 of the 500 maximum unused rather than manufacturing
low-value variants:

1. ATR trailing — 30;
2. Donchian breakout — 16;
3. z-score mean reversion — 64;
4. order-flow delta impulse — 40;
5. rolling flow trend — 64;
6. volume-shock momentum — 64;
7. VWAP reversion + flow — 64;
8. compression/expansion — 64.

Candidate generation is bounded and deterministic. The 406 count is a declaration ceiling for the
pilot catalog, not evidence of 406 independent edges.

Canonical design document: `docs/STRATEGY_FACTORY_V2_DESIGN.md`.
Pilot contract: `config/strategy_factory_v2_pilot_v1.json`.
Pilot family catalog: `src/eba_trader/strategy_factory_v2_catalog.py`.

## Validation status

There is still **no verified profitable strategy**. SF1, SF2 and SF3 are closed with zero promoted
candidates. SF4 is only prospective replication. Strategy Factory v2 ranking and survivor
selection remain discovery-only. Frozen OOS has not been opened and real execution remains locked.

## Verification quality gate — DO NOT LOWER

Broad discovery is not verification. Any candidate that eventually enters strict EBA verification
must satisfy its preregistered economic, activity, cross-window, multiple-testing and robustness
requirements before Frozen OOS can be considered.

The historical SF2/SF3 gate remains a minimum reference:

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

1. Add a standard D0 evaluator/adaptor layer that maps the 8 catalog families onto their existing
   causal backtest engines under one discovery-only contract.
2. Produce common low-fidelity D0 metrics and `BehavioralFingerprint` output without adding
   promotion authority.
3. Wire the evaluator into `run_discovery_batch` so every inspected candidate is ledgered with
   dataset SHA, source-code SHA, fidelity, metrics, behavior and compute accounting.
4. Add static/sanity rejection before performance ranking and tests for immutable trial accounting.
5. Add behavioral-cluster diagnostics on real batch outputs while keeping family/raw/cluster counts
   distinct.
6. Keep D1 hidden confirmation sealed; do not run it as part of D0 evaluator work.
7. Keep SF4 prospective replication untouched until its declared evaluation time.
8. Merge only when exact-head regression, Ruff, runtime, production-bundle, continuity and hygiene
   checks are green.

## Continuity protocol

New sessions read `AGENTS.md`, `PROJECT_STATE.md`, `ARCHITECTURE.md`, `DECISIONS.md`, `TODO.md`,
`CHANGELOG.md`, `SESSION_HANDOFF.md`, `BACKTEST_PROTOCOL.md` and
`docs/STRATEGY_FACTORY_V2_DESIGN.md`, then query actual GitHub/production state before editing.
