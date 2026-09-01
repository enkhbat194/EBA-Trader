# EBA Trader — Session Handoff

_Last handoff prepared: 2026-09-01 (Asia/Ulaanbaatar)_

## Exact continuation point

Repository: `enkhbat194/EBA-Trader`

Actual GitHub head must be queried at startup because documentation-only commits can advance `main`. Latest code-bearing research baseline reconciled in this handoff:

`cbe8cfd07587dda126234f853b47624f241f416e` — PR #115.

PR #109, #110, #112, #114 and #115 are merged. PR #109 added deterministic resume-safe all-strata D0 pilot orchestration. PR #110 binds source provenance to the actual clean production checkout. PR #112 coordinates the five-minute auto-updater and D0 production wrapper through one shared nonblocking checkout lock. PR #114 reconciled the successful exact production proof for `59f6a21e8736b53473fd99a7cb00236c407f5573`, Actions run `33466706747`. PR #115 adds auditable discovery-only behavioral cluster accounting without changing research gates or execution authority.

Exact-current-build D0 proof for `cbe8cfd07587dda126234f853b47624f241f416e` was triggered as Actions run `33470607755`; query its final status before relying on that commit as production-proven. The production 406-candidate × 12-strata campaign has not been executed yet. No public or automatic campaign trigger was added.

## What was completed in the latest engineering run

1. Re-read current GitHub state and all canonical project documents before editing.
2. Confirmed exact production D0 proof for `59f6a21e8736b53473fd99a7cb00236c407f5573` succeeded in run `33466706747`.
3. Audited low-fidelity selection and confirmed incomplete/rejected candidates were already excluded from behavioral representatives.
4. Identified the remaining accounting gap required by the Strategy Factory v2 contract: raw candidate, unique specification, independent-family and behavioral-cluster identities/counts were not exposed as one auditable campaign report.
5. Implemented discovery-only behavioral cluster accounting and attached it to the D0 campaign result/production CLI.
6. Added fail-closed validation for undeclared report candidates, family mismatch and representative drift.
7. Added regression tests proving incomplete/rejected candidates never enter behavioral clusters and behavioral clones collapse deterministically without losing family accounting.
8. PR #115 exact head `a48cc30c26829387544b92d24b16bb5e993e6b2b` passed test, hygiene, continuity and production-bundle validation, then was squash-merged with an expected-head SHA guard.
9. New code-bearing main from PR #115: `cbe8cfd07587dda126234f853b47624f241f416e`.
10. Exact-current-build D0 source proof run `33470607755` started for that commit; final status remains an explicit startup check until completed.
11. Preserved the operator-only campaign invocation boundary; no unauthenticated/public execution trigger was introduced.

## Exact completed D0 proof baseline

Latest completed and reconciled proof before PR #115 is build `59f6a21e8736b53473fd99a7cb00236c407f5573`, Actions run `33466706747`:

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
- existing D0 source is inspected/reusable discovery evidence only;
- all-strata campaign orchestration merged;
- actual clean-checkout provenance binding merged;
- automatic-update checkout race guarded in merged code;
- behavioral accounting merged: raw candidates, unique specs, families, eligible behaviors and clusters remain separate counts;
- clustering is deterministic under the existing fixed 0.90 pilot threshold;
- incomplete/rejected candidates cannot enter behavioral clusters;
- representative drift between accounting and the existing selector fails closed;
- actual empirical cluster counts do not exist until production campaign execution;
- D1 remains sealed and no survivor freeze has occurred.

## Research status and hard locks

There is still no verified profitable strategy. SF1, SF2 and SF3 closed with zero promoted candidates. D0 discovery ranking or clustering is not verification.

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

1. Query D0 exact-current-build production proof run `33470607755`; require green before relying on `cbe8cfd...` as production-proven.
2. When an authorized Linode shell path is available, invoke only `scripts/run_sfv2_d0_pilot_production_once.sh`; do not create an unauthenticated public trigger as an access workaround.
3. Run/resume the exact 406 candidates across all 12 D0 strata while the shared checkout lock is held.
4. Never rank incomplete candidates; aggregate selection-only economics/activity/cost/drawdown/benchmark metrics only after terminal all-strata coverage.
5. Record actual raw/unique-spec/family/eligible/cluster counts from the immutable production campaign evidence; do not confuse merged accounting capability with empirical results.
6. Continue only under the existing D0 diversity/racing contract; no new family, threshold or ranking weight is authorized by PR #115.
7. Freeze at most 30 survivors before any separately authorized D1 access; zero survivors is valid.
8. Keep D1, Frozen OOS, SF4 pre-unlock evaluation and real-money execution closed.

## Startup rule

Read `AGENTS.md`, `PROJECT_STATE.md`, `ARCHITECTURE.md`, `DECISIONS.md`, `TODO.md`, `CHANGELOG.md`, this file, `BACKTEST_PROTOCOL.md`, `docs/CONTINUITY_PROTOCOL.md` and `docs/STRATEGY_FACTORY_V2_DESIGN.md`; then query actual GitHub/production proof before editing.
