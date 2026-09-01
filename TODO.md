# EBA Trader — TODO

Actual merged code, exact production evidence and latest explicit decisions override stale prose. Query `main`, open PRs and workflows before continuing. Documentation commits may move `main`; the latest code-bearing research baseline reconciled here is `6024bb069f458ffae4253b493a87cfd15aaaca93` (PR #119).

## DONE — Repository/runtime and research foundation

- [x] Canonical GitHub `main` + Linode production path.
- [x] Production HTTPS/PWA/runtime proof and five-minute auto-update path.
- [x] Keep real-money execution locked.
- [x] Seal M5 development and Frozen OOS boundaries.
- [x] Close SF1, SF2 and SF3 with zero verified/promoted candidates.
- [x] Preserve fixed statistical/sample/provenance gates; do not rescue sparse outcomes.

## DONE — Strategy Factory v2 foundation

- [x] Separate broad discovery from strict verification authority.
- [x] Hard-cap raw candidates at 500, per-family candidates at 64, survivors at 30.
- [x] Register 8 executable causal families with exact deterministic 406-candidate pilot catalog.
- [x] Add common causal D0 evaluator with fees/slippage.
- [x] Add immutable campaign/candidate/trial accounting and behavioral fingerprints.
- [x] Add D0/D1/D2/D3 evidence zoning and keep D1/Frozen OOS closed.
- [x] Bind D0 only to the already-inspected default M5 development corpus.
- [x] Prevent temporal-gap warmup leakage and reuse terminal trials on resume.
- [x] Prove production D0 source: 2,880 rows, 12 windows/strata, `DISCOVERY_ONLY`, inspected reusable evidence only.
- [x] Merge PR #109: resume-safe all-strata D0 campaign orchestration.
- [x] Merge PR #110: derive campaign source SHA from the actual clean checkout and fail closed on dirty/mismatched source provenance.
- [x] Merge PR #112: shared `flock` checkout guard between the five-minute updater and operator-only D0 production wrapper.
- [x] Keep campaign invocation non-public and non-automatic.
- [x] Merge PR #115: discovery-only behavioral cluster accounting with separate raw/unique-spec/family/eligible/cluster counts; incomplete/rejected candidates excluded; representative drift fails closed.
- [x] Merge PR #117: aggregate D0 selection economics are exposed only for complete, non-rejected candidates; incomplete/rejected trial accounting remains immutable but cannot leak partial economics into ranking.
- [x] Merge PR #119: complete non-rejected candidates must expose the full fixed finite D0 selection-metric schema on every stratum; missing/non-numeric/non-finite metrics and invalid `trade_count` fail closed.
- [x] Confirm exact-current-build D0 production proof for `6024bb069f458ffae4253b493a87cfd15aaaca93` in Actions run `33483175058`, verify job `99777142101`.

## EXACT D0 EVIDENCE

Latest completed exact production D0 proof is build `6024bb069f458ffae4253b493a87cfd15aaaca93`:

- [x] Actions proof run `33483175058`, verify job `99777142101`, completed successfully;
- [x] exact-build wait completed successfully;
- [x] existing-only D0 source inspection completed successfully;
- [x] declaration SHA `88365779d6821c1fb30372148bbcedbfadf11471843f57722723286a43cbc77c`;
- [x] dataset SHA `aa13bcfc111c00f6da19621353a3ca8044f58eca1ab95e837d9490a205aa72eb`;
- [x] candle SHA `6368c9f41ff635d2474860a8d4579fc00e57488871020a9df38222f32d9f4744`;
- [x] order-flow SHA `3398d17c48dd282c86a13a3ccf9daafcd2784e1e64732bb52c29b9b294e82da3`;
- [x] row count 2,880; windows/strata 12/12;
- [x] authority `DISCOVERY_ONLY` and provenance `INSPECTED_REUSABLE_DISCOVERY_DATA`;
- [x] fresh-confirmation evidence false; verification authority false;
- [x] D1/Frozen OOS/live remain closed/closed/locked.

## ACTIVE — SF4 prospective replication

- [x] Freeze exact `s3_vsm_s150` and `s3_cex_s075` parameters without retuning.
- [x] Preregister new BTCUSDT USD-M data from `2026-09-01T00:00:00Z` through `2026-09-13T00:00:00Z`.
- [x] Prohibit pooling SF3 evidence into replication qualification.
- [x] Carry forward the conservative 48-test search budget.
- [x] Lock evaluation before `2026-09-13T00:00:00Z`.
- [ ] After the declared end time, evaluate the two frozen hypotheses on new data only.

## NOW — pre-D1 integrity guard

- [ ] Add a fail-closed Factory v2 survivor-freeze completeness guard before any survivor freeze or D1 authorization.
- [ ] Require every selected survivor to have exactly the declared terminal D0 strata, no rejected stratum, and eligibility under the frozen D0 report before writing immutable survivor selection.
- [ ] Keep D1 sealed until this guard is merged, tested and exact-head green.

## NOW — D0 invocation

- [ ] When an authorized Linode shell path is available, invoke only `scripts/run_sfv2_d0_pilot_production_once.sh`.
- [ ] Do not add an unauthenticated public trigger merely to bypass shell-access limitations.
- [ ] Keep the execution mechanism `DISCOVERY_ONLY`; it must not open D1, lifecycle promotion, Frozen OOS, demo authority or live execution.

## NEXT — bounded D0 pilot

- [ ] Run/resume the exact 406 candidates across all 12 declared D0 strata while the checkout lock is held.
- [ ] Account for every performance-inspected candidate in the immutable trial ledger.
- [x] Mechanism: never place incomplete/rejected candidates into behavioral representative/clustering selection.
- [x] Mechanism: keep raw candidate, unique specification, independent-family and behavioral-cluster counts distinct.
- [x] Mechanism: expose aggregate selection-only economics/activity/cost/drawdown/benchmark metrics only after terminal all-strata coverage and only for non-rejected candidates.
- [x] Mechanism: fail closed if any complete non-rejected stratum lacks a required finite selection metric.
- [ ] Evidence: after production campaign execution, record actual raw/unique/family/eligible/cluster counts from the immutable ledger/report.
- [ ] Apply diversity-aware higher-fidelity D0 racing under the predeclared contract only.
- [ ] Nominate at most 30 discovery survivors; zero survivors is valid.
- [ ] Freeze survivor specifications only after the pre-D1 completeness guard is active.

## THEN — hidden confirmation and strict verification

- [ ] Open D1 only through separately authorized hidden-confirmation workflow after survivor freeze prerequisites pass.
- [ ] Account for broad-search selection/multiple-testing history.
- [ ] Reject failed survivors without post-hoc retuning on D1.
- [ ] Use D2 for candidate-specific robustness only after confirmation survives.
- [ ] Keep robustness before Frozen OOS.
- [ ] Keep D3 Frozen OOS sealed until all prior gates pass.
- [ ] Forward paper and Binance Demo remain later execution stages, not verification authority.
- [ ] Real execution remains separately locked.

## FIXED RESEARCH-INTEGRITY RULES — DO NOT LOWER

- [x] causal/no-lookahead execution;
- [x] fees/slippage included;
- [x] dataset/source provenance and immutable evidence;
- [x] development/confirmation/OOS separation;
- [x] robustness before Frozen OOS;
- [x] post-hoc tuning and multiple-testing protection;
- [x] reused data cannot be relabelled fresh;
- [x] discovery ranking has no promotion authority;
- [x] deterministic risk veto remains independent of AI;
- [x] real-money execution stays locked.

## BLOCKED / GATED

- [ ] Production 406-candidate D0 invocation — operator-only production shell action is not exposed through the currently connected project tools; do not weaken access controls to work around this.
- [ ] Factory v2 survivor freeze/D1 — blocked until the expected-strata completeness guard is merged and the D0 campaign actually yields frozen survivor evidence.
- [ ] SF4 evaluation before `2026-09-13T00:00:00Z` — intentionally fail-closed.
- [ ] M5 Frozen OOS — sealed until strict prerequisites pass.
- [ ] Real-money Binance orders — intentionally locked.

## Handoff rule

At meaningful session end, record exact commits, CI/production proof, risks and next exact action. Never convert execution plumbing, a discovery leaderboard, reused D0 evidence, or an implemented accounting mechanism into a profitability/live-readiness claim.
