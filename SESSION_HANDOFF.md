# EBA Trader — Session Handoff

_Last handoff prepared: 2026-09-01 (Asia/Ulaanbaatar)_

## Exact continuation point

Repository: `enkhbat194/EBA-Trader`

Actual GitHub head must be queried at startup because documentation-only commits can advance `main`. Latest code-bearing research baseline reconciled in this handoff:

`3d30199b3d4d59269e093b5cfebbce267c70afb9` — PR #122.

PR #109, #110, #112, #115, #117, #119, #121 and #122 are merged. The most recent research-integrity changes are: PR #119 fails closed on D0 selection-metric schema drift; PR #121 added a Factory-specific survivor-freeze completeness/diversity boundary; PR #122 corrected the remaining trust gap by rebuilding survivor eligibility from immutable registered campaign, declared candidate and trial-ledger evidence at freeze time instead of trusting a caller-supplied report/accounting object.

Exact-current-build D0 proof for `3d30199b3d4d59269e093b5cfebbce267c70afb9` completed successfully in Actions run `33484772388`, verify job `99782195060`; the exact-build wait and existing-only D0 source inspection both succeeded. The production 406-candidate × 12-strata campaign has not been executed yet. No public or automatic campaign trigger was added. No survivor selection has been frozen. D1 remains sealed.

## What was completed in the latest engineering run

1. Re-read current GitHub `main`, production evidence and all required canonical project documents before editing.
2. Confirmed the starting docs-only `main` had public-production and Linode external production proof green.
3. Re-audited the Strategy Factory v2 contract and preserved the existing 8-family / 406-candidate / 500-cap scope.
4. Re-audited SF4 structurally without inspecting replication data: exactly two frozen hypotheses remain, retuning and SF3 pooling are prohibited, the 48-test budget remains carried forward, and evaluation remains fail-closed before `2026-09-13T00:00:00Z`.
5. Found and fixed D0 selection-metric schema drift: complete non-rejected candidates now require the full fixed finite metric schema on every stratum before aggregate economics or behavioral eligibility exists. PR #119 merged and exact production proof succeeded.
6. Reconciled canonical docs in PR #120 after PR #119 and recorded a pre-D1 survivor-freeze completeness gap in the generic ledger path.
7. Implemented a Factory-specific survivor-freeze boundary in PR #121: complete/non-rejected/behaviorally eligible candidates only, exact expected-strata coverage, one selected candidate per behavioral cluster, frozen source/D0 identities, and downstream authority false.
8. Post-merge audit found PR #121 still trusted the caller-supplied `campaign_run.report/accounting` object, which could theoretically be fabricated or stale relative to immutable ledger evidence.
9. PR #122 closed that gap. The authorized Factory freeze path now reads the immutable campaign registration, cross-checks source/declaration/dataset/threshold identities, rebuilds the D0 report and cluster accounting from immutable candidates/trials, requires the full declared catalog to be terminal across all registered expected D0 strata, and only then permits immutable survivor selection.
10. PR #122 also preserves diversity: selected candidates must be behaviorally eligible and no two selected candidates may come from the same behavioral cluster.
11. The frozen survivor-selection record explicitly leaves D1, Frozen OOS and live execution false. Survivor freeze is still discovery evidence only and is not verification authority.
12. Final PR #122 head `fac8f8e46010cfcc4487588eb158248a323e89ed` passed all four required checks: test, hygiene, validate and continuity.
13. PR #122 was squash-merged with expected-head SHA guard. New code-bearing main: `3d30199b3d4d59269e093b5cfebbce267c70afb9`.
14. Exact-current-build D0 production proof run `33484772388`, verify job `99782195060`, completed successfully for that merged code-bearing baseline.
15. Preserved the operator-only campaign invocation boundary; no unauthenticated/public execution trigger was introduced.

## Exact completed D0 proof baseline

Latest completed exact proof is build `3d30199b3d4d59269e093b5cfebbce267c70afb9`, Actions run `33484772388`, verify job `99782195060`:

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
- aggregate selection-only economics are unavailable for incomplete or rejected candidates;
- complete non-rejected candidates fail closed unless every expected stratum exposes the fixed finite selection metric schema;
- representative drift between accounting and the existing selector fails closed;
- authorized Factory survivor freeze is `freeze_d0_pilot_survivors()`; generic ledger freeze is not the sanctioned Factory path;
- at freeze time, immutable campaign registration and ledger candidates/trials are authoritative; caller report/accounting objects are not trusted for eligibility;
- the full declared catalog must have terminal evidence over the exact registered D0 strata before survivor selection can be written;
- selected survivors must be complete, non-rejected, behaviorally eligible and one-per-behavioral-cluster;
- frozen survivor evidence binds exact source SHA, D0 declaration/dataset identities, expected strata and fixed 0.90 threshold while leaving D1/Frozen OOS/live false;
- actual empirical cluster counts do not exist until production campaign execution;
- no survivor freeze has occurred;
- D1 remains sealed.

## Research status and hard locks

There is still no verified profitable strategy. SF1, SF2 and SF3 closed with zero promoted candidates. D0 discovery ranking, clustering or survivor freeze is not verification.

SF4 keeps exact `s3_vsm_s150` and `s3_cex_s075` parameters frozen for prospective replication using only `2026-09-01T00:00:00Z` through `2026-09-13T00:00:00Z`. Evaluation before `2026-09-13T00:00:00Z` is fail-closed. SF3 evidence cannot be pooled into the replication result. The conservative 48-test search budget remains carried forward.

Hard locks:

- M5 Frozen OOS remains sealed/not opened.
- Factory v2 D1 hidden confirmation remains sealed.
- Factory v2 survivor freeze guard is implemented, but no production D0 campaign evidence or frozen survivor set exists yet.
- SF4 cannot be evaluated before `2026-09-13T00:00:00Z`.
- Real Binance execution remains locked.
- Demo execution has no strategy-promotion authority.
- D0/development ranking has no promotion authority.
- Reused/inspected D0 data cannot be called fresh confirmation evidence.
- A discovery survivor is not a verified strategy and cannot transition durable StrategyLifecycle.

## Next exact task

1. When an authorized Linode shell path is available, invoke only `scripts/run_sfv2_d0_pilot_production_once.sh`; do not create an unauthenticated public trigger as an access workaround.
2. Run/resume the exact 406 candidates across all 12 D0 strata while the shared checkout lock is held.
3. Record actual raw/unique-spec/family/eligible/cluster counts from the immutable production campaign evidence; do not confuse merged accounting capability with empirical results.
4. Continue only under the existing D0 diversity/racing contract; no new family, threshold or ranking weight is authorized.
5. Freeze at most 30 survivors only through the ledger-backed Factory-specific guard after actual D0 evidence exists; zero survivors is valid. D1 still requires separate authorization.
6. Open D1 only through a separately authorized hidden-confirmation workflow after survivor freeze prerequisites pass.
7. Keep D1, Frozen OOS, SF4 pre-unlock evaluation and real-money execution closed.

## Startup rule

Read `AGENTS.md`, `PROJECT_STATE.md`, `ARCHITECTURE.md`, `DECISIONS.md`, `TODO.md`, `CHANGELOG.md`, this file, `BACKTEST_PROTOCOL.md`, `docs/CONTINUITY_PROTOCOL.md` and `docs/STRATEGY_FACTORY_V2_DESIGN.md`; then query actual GitHub/production proof before editing.
