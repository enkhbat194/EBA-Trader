# EBA Trader — Session Handoff

_Last handoff prepared: 2026-09-01 (Asia/Ulaanbaatar)_

## Exact continuation point

Repository: `enkhbat194/EBA-Trader`

Canonical main before this handoff reconciliation:

`2ffb7ce23a6c2fdb7507ce3d9b264ef1966f99bd`

PR #109, PR #110, PR #112 and PR #113 are merged. PR #109 added deterministic resume-safe all-strata D0 pilot orchestration. PR #110 binds source provenance to the actual clean production checkout. PR #112 coordinates the five-minute auto-updater and D0 production wrapper through one shared nonblocking checkout lock. PR #113 reconciled continuity after that production guard.

Final exact-build production D0 source proof for `2ffb7ce23a6c2fdb7507ce3d9b264ef1966f99bd` passed in GitHub Actions run `33464296457` on 2026-09-01 UTC. No D0 campaign has been executed yet. No public or automatic campaign trigger was added.

## What was completed

1. Re-read current `main`, canonical project documents and production-proof workflow state.
2. Confirmed final exact production build `2ffb7ce23a6c2fdb7507ce3d9b264ef1966f99bd` is live through `/api/app-info` as observed by Actions run `33464296457`.
3. Confirmed the production D0 source remains valid and unchanged: 2,880 rows across 12 windows/12 strata, with discovery-only authority.
4. Confirmed production proof still reports `INSPECTED_REUSABLE_DISCOVERY_DATA`, not fresh confirmation evidence, with no verification authority.
5. Confirmed D1 unopened, Frozen OOS unopened and live execution disallowed in the exact final-build production proof.
6. Reconciled stale continuity prose that still described final exact-production proof as pending.
7. Preserved the operator-only campaign invocation boundary; no unauthenticated/public execution trigger was introduced.

## Exact D0 proof

Latest completed exact proof is production build `2ffb7ce23a6c2fdb7507ce3d9b264ef1966f99bd`, Actions run `33464296457`:

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

## Strategy Factory v2 state

- raw cap 500; exact pilot catalog 406; per-family cap 64; survivor cap 30;
- 8 existing causal strategy families;
- common causal evaluator with fees/slippage;
- immutable campaign/candidate/trial ledger;
- resume reuses terminal trials without re-evaluation;
- temporal-gap warmup protection active;
- production D0 source proven on exact final main;
- all-strata campaign orchestration merged;
- actual clean-checkout provenance binding merged;
- automatic-update checkout race guarded in merged code;
- D1 remains sealed and no survivor freeze has occurred.

## Research status and hard locks

There is still no verified profitable strategy. SF1, SF2 and SF3 closed with zero promoted candidates. D0 discovery ranking is not verification.

SF4 keeps exact `s3_vsm_s150` and `s3_cex_s075` parameters frozen for prospective replication using only `2026-09-01T00:00:00Z` through `2026-09-13T00:00:00Z`. Evaluation before `2026-09-13T00:00:00Z` is fail-closed. SF3 evidence cannot be pooled into the replication result.

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

1. When an authorized Linode shell path is available, invoke only `scripts/run_sfv2_d0_pilot_production_once.sh`; do not create an unauthenticated public trigger as an access workaround.
2. Run/resume the exact 406 candidates across all 12 D0 strata while the shared checkout lock is held.
3. Never rank incomplete candidates; aggregate selection-only economics/activity/cost/drawdown/benchmark metrics only after terminal all-strata coverage.
4. Behavioral-deduplicate while preserving raw candidate, unique-spec, cluster and family counts, then continue only under the existing D0 diversity/racing contract.
5. Freeze at most 30 survivors before any separately authorized D1 access; zero survivors is valid.
6. Keep D1, Frozen OOS, SF4 pre-unlock evaluation and real-money execution closed.

## Startup rule

Read `AGENTS.md`, `PROJECT_STATE.md`, `ARCHITECTURE.md`, `DECISIONS.md`, `TODO.md`, `CHANGELOG.md`, this file, `BACKTEST_PROTOCOL.md`, `docs/CONTINUITY_PROTOCOL.md` and `docs/STRATEGY_FACTORY_V2_DESIGN.md`; then query actual GitHub/production proof before editing.
