# EBA Trader — TODO

Actual merged code, exact production evidence and latest explicit decisions override stale prose. Query `main`, open PRs and workflows before continuing.

## DONE — Repository/runtime foundation

- [x] Canonical GitHub `main` + Linode production path.
- [x] Production HTTPS/PWA/runtime proof and auto-update path.
- [x] Encrypted Binance Demo credential vault and reconnect proof.
- [x] Fast Momentum paper/runtime scanner.
- [x] Binance USD-M Futures Demo BUY/SELL round-trip execution plumbing proved without real money.
- [x] Keep real-money execution locked.

## DONE — M5 / SF1 / SF2 / SF3 research history

- [x] Seal M5 development and Frozen OOS boundaries.
- [x] Reject historical `absorption_020` without promotion.
- [x] Run and close SF1: 48 candidates, zero verified.
- [x] Run and close SF2: 24 candidates, zero verified.
- [x] Run and close SF3: 24 candidates, zero verified.
- [x] Preserve the fixed 30-trade minimum; do not rescue sparse outcomes.
- [x] Keep every phase development-only and leave Frozen OOS sealed.

## DONE — Strategy Factory v2 foundation

- [x] Separate broad discovery from strict verification authority.
- [x] Hard-cap raw candidates at 500, per-family candidates at 64, survivors at 30.
- [x] Add deterministic discovery candidate/spec identity and immutable trial ledger.
- [x] Add behavioral fingerprints, similarity and representative filtering.
- [x] Register 8 executable causal families with exact deterministic 406-candidate pilot catalog.
- [x] Add common causal D0 evaluator/adaptor with fees/slippage through existing engines.
- [x] Normalize D0 metrics as selection-only evidence.
- [x] Add immutable D0 dataset manifest and 12 temporal strata.
- [x] Explicitly label D0 `INSPECTED_REUSABLE_DISCOVERY_DATA`.
- [x] Add D1 hidden-confirmation freeze contract without opening D1.
- [x] Reject D1 hashes already consumed by D0.
- [x] Bind D0 only to the already-inspected default M5 development corpus.
- [x] Add existing-only loader that cannot fetch/rebuild missing evidence.
- [x] Prevent D0 warmup from crossing temporal gaps.
- [x] Reuse terminal immutable trials on compute-budget resume.

## DONE — exact production D0 source proof

Exact production build `ff849e25c741ff0170ab90db03e22fda18082fde` proves:

- [x] source kind `INSPECTED_M5_DEVELOPMENT_CORPUS`;
- [x] 2,880 rows across 12 windows / 12 strata;
- [x] declaration SHA `88365779d6821c1fb30372148bbcedbfadf11471843f57722723286a43cbc77c`;
- [x] dataset SHA `aa13bcfc111c00f6da19621353a3ca8044f58eca1ab95e837d9490a205aa72eb`;
- [x] candle SHA `6368c9f41ff635d2474860a8d4579fc00e57488871020a9df38222f32d9f4744`;
- [x] order-flow SHA `3398d17c48dd282c86a13a3ccf9daafcd2784e1e64732bb52c29b9b294e82da3`;
- [x] authority remains `DISCOVERY_ONLY`;
- [x] fresh-confirmation/verification authority remain false;
- [x] D1, Frozen OOS and live execution remain closed.

## NOW — PR #109 D0 campaign orchestration

Do not run the production campaign until exact-head CI is green and #109 is merged.

- [x] Add campaign-level runner for the exact frozen pilot catalog.
- [x] Bind campaign immutably to D0 declaration/dataset hashes, catalog seed/count, warmup, behavioral threshold and source-code SHA.
- [x] Reuse existing immutable trial-ledger resume semantics across every D0 stratum.
- [x] Add explicit one-shot existing-only production D0 entrypoint.
- [x] Keep D1/survivor freeze/lifecycle/Frozen OOS/live authority out of the runner.
- [x] Add safety and campaign-immutability tests.
- [ ] Complete PR #109 exact-head regression, Ruff, runtime and production-bundle checks.
- [ ] Merge #109 only on exact-head green.

## ACTIVE — SF4 prospective replication

- [x] Freeze exact `s3_vsm_s150` and `s3_cex_s075` parameters without retuning.
- [x] Preregister prospective BTCUSDT USD-M data from `2026-09-01T00:00:00Z` through `2026-09-13T00:00:00Z`.
- [x] Prohibit pooling SF3 evidence into replication qualification.
- [x] Carry forward conservative multiplicity budget 48.
- [x] Lock evaluation before `2026-09-13T00:00:00Z`.
- [ ] After the declared end time, evaluate the two frozen hypotheses on new data only.
- [ ] If replication fails, close it without lowering thresholds.
- [ ] If replication passes, preregister candidate-specific robustness before robustness results.

## NEXT — bounded production D0 pilot execution

Only after #109 merges:

- [ ] Run/resume the exact 406 candidates across all 12 declared D0 strata using the proven inspected production source.
- [ ] Account for every performance-inspected candidate in the immutable trial ledger.
- [ ] Never rank incomplete candidates.
- [ ] Build selection-only aggregate metrics after terminal required-stratum coverage.
- [ ] Cluster behavioral near-duplicates and keep raw/unique/cluster/family counts distinct.
- [ ] Apply diversity-aware higher-fidelity D0 racing under the predeclared contract only.
- [ ] Nominate at most 30 discovery survivors; zero survivors is valid.
- [ ] Freeze survivor specifications before any D1 hidden confirmation is opened.

## THEN — hidden confirmation and strict verification

- [ ] Open D1 only through separately authorized hidden-confirmation workflow.
- [ ] Account for broad-search selection/multiple-testing history.
- [ ] Reject failed survivors without post-hoc retuning on D1.
- [ ] Use D2 for candidate-specific robustness only after confirmation survives.
- [ ] Keep robustness before Frozen OOS.
- [ ] Keep D3 Frozen OOS sealed until all prior gates pass.
- [ ] Forward paper only after strict research verification.
- [ ] Binance Demo only after paper/execution criteria; Demo is not verification.
- [ ] Real execution remains separately locked.

## FIXED RESEARCH-INTEGRITY RULES — DO NOT LOWER

- [x] causal/no-lookahead execution;
- [x] fees/slippage included;
- [x] dataset provenance/integrity;
- [x] immutable evidence where authority is required;
- [x] development/confirmation/OOS separation;
- [x] robustness before Frozen OOS;
- [x] post-hoc tuning protection;
- [x] reused data cannot be relabelled fresh;
- [x] development/discovery ranking has no promotion authority;
- [x] deterministic risk veto remains independent of AI;
- [x] real-money execution stays locked.

## BLOCKED / GATED

- [ ] Production 406-candidate D0 execution — blocked only until PR #109 exact-head green + merge.
- [ ] M5 Frozen OOS access — blocked because no candidate passed prior strict gates.
- [ ] Factory v2 D1 hidden confirmation — blocked until D0 survivor freeze + separate authorization.
- [ ] SF4 evaluation before `2026-09-13T00:00:00Z` — intentionally fail-closed.
- [ ] Real-money Binance orders — intentionally locked.
- [ ] Resting LOB/order-book claims — require separate reconstruction/integrity contract.

## Handoff rule

At meaningful session end, record exact commits, CI/production proof, risks and next exact action. Never convert successful execution plumbing, a discovery leaderboard, a sparse backtest, or a statistically invalid repeated search into a profitability/live-readiness claim.
