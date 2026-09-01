# EBA Trader — Session Handoff

_Last handoff prepared: 2026-09-01 (Asia/Ulaanbaatar)_

## Exact continuation point

Repository: `enkhbat194/EBA-Trader`

Canonical `main` before current PR #109:

`ff849e25c741ff0170ab90db03e22fda18082fde`

Latest merged work: PR #108, `Strategy Factory v2: prove existing D0 source on production`.

Exact-main production checks are green, including Linode runtime checks, public production smoke, D0 existing-source production proof, SF3 production evidence proof and Linode external production proof.

PR #109 is the active Strategy Factory v2 D0 campaign-orchestration branch. Do not run the production 406-candidate campaign until #109 exact-head checks pass and it is merged.

## What was completed

PR #107 merged the pre-pilot audit hardening:

1. D0 warmup stops at temporal discontinuities and cannot bridge independently sampled M5 windows.
2. `run_discovery_batch` reuses terminal evaluated/rejected trials during resume without evaluator re-execution or new compute accounting.

PR #108 then proved the existing-only D0 source on the exact production build. The prior production-data blocker is closed.

Exact D0 proof on build `ff849e25c741ff0170ab90db03e22fda18082fde`:

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

## PR #109 scope

The minimum missing layer was campaign-level production orchestration. Existing code had candidate generation, evaluator, per-stratum execution and immutable ledger primitives, but no single deterministic runner tying them together.

PR #109 adds:

- `strategy_factory_v2_campaign.py` campaign runner;
- immutable binding to D0 declaration/dataset hashes, exact pilot seed/count, source-code SHA, warmup and behavioral threshold;
- all-stratum run/resume through the existing immutable trial ledger;
- `scripts/run_sfv2_d0_pilot_once.py` explicit existing-only entrypoint;
- tests for campaign immutability and downstream safety locks.

The runner intentionally does **not** open D1, freeze survivors, transition StrategyLifecycle, open Frozen OOS or enable demo/live execution.

## Strategy Factory v2 state

- discovery authority remains `DISCOVERY_ONLY`;
- raw cap 500, exact executable pilot catalog 406, per-family cap 64, survivor cap 30;
- 8 existing causal strategy families;
- common D0 evaluator with existing execution/cost semantics;
- immutable campaign/candidate/trial accounting;
- exact inspected production D0 source now proven;
- 12 D0 strata; all required strata must be terminal before complete-candidate aggregation;
- behavioral dedup foundation present;
- D1 hidden confirmation remains sealed.

## Research status and hard locks

There is still no verified profitable strategy. SF1, SF2 and SF3 closed with zero promoted candidates. D0 discovery ranking is not verification.

SF4 keeps exact `s3_vsm_s150` and `s3_cex_s075` parameters frozen for prospective replication using only `2026-09-01T00:00:00Z` through `2026-09-13T00:00:00Z`. Evaluation before the declared end time is fail-closed. SF3 evidence cannot be pooled into the replication result.

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

1. Finish PR #109 exact-head CI; merge only if regression, Ruff, runtime and production-bundle checks are green.
2. On merged exact `main`, run/resume the frozen 406 candidates over all 12 proven D0 strata with the immutable campaign ledger.
3. Never rank incomplete candidates.
4. After terminal all-strata coverage, aggregate selection-only economics/activity/cost/drawdown/benchmark metrics and behavioral fingerprints.
5. Deduplicate behavior while preserving raw candidate, unique specification, behavioral cluster and family counts.
6. Continue only under the predeclared D0 racing/diversity contract; keep D1 closed until survivor freeze and separate authorization.
7. Leave SF4 untouched before its preregistered end time.

## Startup rule

Read `AGENTS.md`, `PROJECT_STATE.md`, `ARCHITECTURE.md`, `DECISIONS.md`, `TODO.md`, `CHANGELOG.md`, this file, `BACKTEST_PROTOCOL.md`, `docs/CONTINUITY_PROTOCOL.md` and `docs/STRATEGY_FACTORY_V2_DESIGN.md`; then query actual GitHub/production proof before editing.
