# EBA Trader — Session Handoff

_Last handoff prepared: 2026-09-01 (Asia/Ulaanbaatar)_

## Exact continuation point

Repository: `enkhbat194/EBA-Trader`

Actual GitHub head must be queried at startup because documentation-only commits can advance `main`. Latest code-bearing research baseline reconciled in this handoff:

`6024bb069f458ffae4253b493a87cfd15aaaca93` — PR #119.

PR #109, #110, #112, #115, #117 and #119 are merged. PR #109 added deterministic resume-safe all-strata D0 pilot orchestration. PR #110 binds source provenance to the actual clean production checkout. PR #112 coordinates the five-minute auto-updater and D0 production wrapper through one shared nonblocking checkout lock. PR #115 adds auditable discovery-only behavioral cluster accounting. PR #117 prevents incomplete/rejected candidates from exposing partial aggregate economics. PR #119 closes the remaining metric-schema drift path: a complete non-rejected candidate cannot expose aggregate selection metrics or behavioral eligibility unless every D0 stratum supplies the full fixed finite selection-metric schema; invalid `trade_count` also fails closed.

Exact-current-build D0 proof for `6024bb069f458ffae4253b493a87cfd15aaaca93` completed successfully in Actions run `33483175058`, verify job `99777142101`; the exact-build wait and existing-only D0 source inspection both succeeded. The production 406-candidate × 12-strata campaign has not been executed yet. No public or automatic campaign trigger was added.

## What was completed in the latest engineering run

1. Re-read current GitHub `main`, exact production evidence and all canonical project documents before editing.
2. Confirmed the previous docs-only `main` had both public-production and Linode external production proof green before making code changes.
3. Re-audited the accepted Strategy Factory v2 contract and preserved the existing 8-family / 406-candidate / 500-cap scope.
4. Re-audited SF4 structurally without inspecting replication data: exactly two frozen hypotheses remain, retuning and SF3 pooling are prohibited, the 48-test budget remains carried forward, and evaluation remains fail-closed before `2026-09-13T00:00:00Z`.
5. Identified a D0 cross-window integrity gap: complete non-rejected candidates could silently average a metric over fewer strata if evaluator/schema drift omitted a selection metric on one terminal stratum.
6. Implemented fail-closed validation requiring all fixed selection metrics on every complete non-rejected stratum; values must be numeric and finite and `trade_count` must be a non-negative integer.
7. Added regression coverage for missing metrics, non-finite values and invalid trade counts while preserving incomplete/rejected exclusion behavior.
8. The first PR head passed tests but validate caught one Ruff E501 formatting failure; only formatting was changed and CI was rerun rather than bypassed.
9. Final PR #119 head `395c85bf089f9bc235da397d00e20789166eb345` passed all four required checks: test, hygiene, validate and continuity.
10. PR #119 was squash-merged with expected-head SHA guard. New code-bearing main: `6024bb069f458ffae4253b493a87cfd15aaaca93`.
11. Exact-current-build D0 production proof run `33483175058`, verify job `99777142101`, completed successfully for the merged code-bearing baseline.
12. A separate structural audit found a pre-D1 safety blocker: generic `DiscoveryTrialLedger.freeze_survivor_selection()` does not itself bind selected survivors to the Factory campaign's full declared expected-strata set. No survivor freeze has occurred and D1 remains sealed. This must be fixed fail-closed before Factory survivor freeze or D1 authorization.
13. Preserved the operator-only campaign invocation boundary; no unauthenticated/public execution trigger was introduced.

## Exact completed D0 proof baseline

Latest completed exact proof is build `6024bb069f458ffae4253b493a87cfd15aaaca93`, Actions run `33483175058`, verify job `99777142101`:

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
- actual empirical cluster counts do not exist until production campaign execution;
- no survivor freeze has occurred;
- D1 remains sealed.

## Research status and hard locks

There is still no verified profitable strategy. SF1, SF2 and SF3 closed with zero promoted candidates. D0 discovery ranking or clustering is not verification.

SF4 keeps exact `s3_vsm_s150` and `s3_cex_s075` parameters frozen for prospective replication using only `2026-09-01T00:00:00Z` through `2026-09-13T00:00:00Z`. Evaluation before `2026-09-13T00:00:00Z` is fail-closed. SF3 evidence cannot be pooled into the replication result. The conservative 48-test search budget remains carried forward.

Hard locks:

- M5 Frozen OOS remains sealed/not opened.
- Factory v2 D1 hidden confirmation remains sealed.
- Factory v2 survivor freeze is blocked pending the expected-strata completeness guard plus actual D0 survivor evidence.
- SF4 cannot be evaluated before `2026-09-13T00:00:00Z`.
- Real Binance execution remains locked.
- Demo execution has no strategy-promotion authority.
- D0/development ranking has no promotion authority.
- Reused/inspected D0 data cannot be called fresh confirmation evidence.
- A discovery survivor is not a verified strategy and cannot transition durable StrategyLifecycle.

## Next exact task

1. Implement and test a minimum fail-closed Factory v2 survivor-freeze guard requiring every selected survivor to match all declared terminal D0 strata and frozen D0 eligibility before immutable survivor selection is written. Do not open D1 as part of this fix.
2. When an authorized Linode shell path is available, invoke only `scripts/run_sfv2_d0_pilot_production_once.sh`; do not create an unauthenticated public trigger as an access workaround.
3. Run/resume the exact 406 candidates across all 12 D0 strata while the shared checkout lock is held.
4. Record actual raw/unique-spec/family/eligible/cluster counts from the immutable production campaign evidence; do not confuse merged accounting capability with empirical results.
5. Continue only under the existing D0 diversity/racing contract; no new family, threshold or ranking weight is authorized.
6. Freeze at most 30 survivors only after the completeness guard is active; zero survivors is valid. D1 still requires separate authorization.
7. Keep D1, Frozen OOS, SF4 pre-unlock evaluation and real-money execution closed.

## Startup rule

Read `AGENTS.md`, `PROJECT_STATE.md`, `ARCHITECTURE.md`, `DECISIONS.md`, `TODO.md`, `CHANGELOG.md`, this file, `BACKTEST_PROTOCOL.md`, `docs/CONTINUITY_PROTOCOL.md` and `docs/STRATEGY_FACTORY_V2_DESIGN.md`; then query actual GitHub/production proof before editing.
