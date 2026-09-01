# EBA Trader — TODO

Actual GitHub/runtime state overrides stale prose. Query `main`, open PRs and workflows before
continuing.

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
- [x] Preserve the fixed 30-trade minimum; do not rescue sparse SF3 outcomes.
- [x] Keep every phase development-only and leave Frozen OOS sealed.

## DONE — Strategy Factory v2 foundation

- [x] Separate broad discovery from strict verification authority.
- [x] Merge versioned discovery-only pilot contract.
- [x] Hard-cap raw candidates at 500, per-family candidates at 64, survivors at 30.
- [x] Add deterministic discovery candidate/spec identity.
- [x] Add immutable discovery campaign/candidate/trial ledger.
- [x] Separate raw candidate budget from evaluation-trial count.
- [x] Record dataset SHA and source-code SHA at the correct layers.
- [x] Add behavioral fingerprints, similarity and representative filtering.
- [x] Add behavioral-cluster reporting with raw/unique/cluster/family counts kept distinct.
- [x] Add bounded Strategy Family v2 registry and deterministic quasi-random sampling.
- [x] Add compact in-process batch evaluation with compute-budget stop accounting.
- [x] Add immutable discovery-survivor selection with no lifecycle promotion authority.
- [x] Add D1 hidden-confirmation freeze contract without opening D1.
- [x] Reject D1 dataset hashes already consumed by D0 discovery.
- [x] Reconcile `BACKTEST_PROTOCOL.md` with lifecycle policy v2 and Factory v2 data zones.

## DONE — first executable Factory v2 pilot catalog

- [x] Register 8 economically distinct families using existing causal EBA engines.
- [x] Declare 406 bounded raw candidate slots rather than force the 500 maximum.
- [x] Add deterministic candidate generation and replay tests.
- [x] Merge PR #100 with exact-head checks green.

## DONE — Strategy Factory v2 common D0 evaluator

- [x] Add one discovery-only evaluator/adaptor interface for all 8 registered families.
- [x] Reuse existing causal backtest engines rather than fork strategy semantics.
- [x] Normalize low-fidelity D0 metrics.
- [x] Generate `BehavioralFingerprint` from actual D0 behavior.
- [x] Fail closed on invalid specs, unavailable order-flow data and zero opportunity.
- [x] Wire evaluator into `run_discovery_batch` so every inspected candidate is ledgered.
- [x] Enforce dataset SHA, source-code SHA, fidelity and compute accounting on every trial.
- [x] Merge PR #102 as `4c5a6a9fe30f29b772a5c2fe4d1e99b38b4262b1`.

## DONE — immutable D0 dataset + stratified input contract

- [x] Add versioned D0 dataset manifest with deterministic content hash.
- [x] Explicitly label D0 as `INSPECTED_REUSABLE_DISCOVERY_DATA`.
- [x] Hash candle and executed-order-flow content independently plus composite dataset identity.
- [x] Fail closed on time misalignment or non-causal order-flow availability.
- [x] Partition D0 into declared temporal strata.
- [x] Require low-fidelity policy to cover every declared stratum instead of chronological first-N.
- [x] Add tests proving content changes alter dataset identity and strata cover the full dataset.
- [x] Reconcile project-state and handoff docs.
- [x] Merge PR #103 as `14472dee7224d5caff6819ea142f01ba6729d3a0`.

## ACTIVE — SF4 prospective replication

- [x] Freeze exact `s3_vsm_s150` and `s3_cex_s075` parameters without retuning.
- [x] Preregister prospective BTCUSDT USD-M windows from 2026-09-01 through 2026-09-13.
- [x] Prohibit pooling SF3 trades/p-values into replication qualification.
- [x] Carry forward conservative multiplicity budget 48.
- [x] Lock evaluation before 2026-09-13T00:00:00Z.
- [ ] After the declared end time, evaluate the two frozen hypotheses on new data only.
- [ ] If replication fails, close it without lowering thresholds.
- [ ] If replication passes, preregister candidate-specific robustness before robustness results.

## NOW — stratified low-fidelity D0 pilot orchestration

- [x] Add causal pre-stratum warmup slices while trading starts exactly at declared stratum start.
- [x] Recompute parent D0 manifest before slicing so trusted SHA cannot be paired with changed data.
- [x] Derive immutable per-stratum dataset SHA values.
- [x] Add ledgered one-stratum execution wrapper using the common D0 evaluator.
- [x] Require all expected strata before a candidate is marked low-fidelity complete.
- [x] Exclude rejected/incomplete candidates from behavioral representative selection.
- [x] Combine behavioral fingerprints across all strata before near-duplicate filtering.
- [x] Add unit tests for manifest mismatch, warmup boundaries, completeness, rejection and dedup.
- [ ] Finish PR #104 exact-head CI and merge only when all required checks are green.

## NEXT — bounded production D0 pilot run

Only after PR #104 merges:

- [ ] Materialize/declare the actual production D0 discovery dataset and immutable manifest.
- [ ] Generate the declared 406 pilot candidates deterministically.
- [ ] Evaluate candidates across every declared temporal stratum.
- [ ] Resume safely after compute-budget stops; never rank incomplete candidates.
- [ ] Account for every performance-inspected candidate in the immutable trial ledger.
- [ ] Apply static sanity filters before low-fidelity simulation.
- [ ] Build selection-only aggregate metrics after full stratum coverage.
- [ ] Cluster behavioral near-duplicates and keep raw/unique/cluster/family counts distinct.
- [ ] Keep diverse representatives for higher-fidelity D0 racing.
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

- [ ] M5 Frozen OOS access — blocked because no candidate passed development/robustness gates.
- [ ] Factory v2 D1 hidden confirmation — blocked until D0 survivor freeze + separate authorization.
- [ ] SF4 evaluation before 2026-09-13T00:00:00Z — intentionally fail-closed.
- [ ] Real-money Binance orders — intentionally locked.
- [ ] Resting LOB/order-book claims — require separate reconstruction/integrity contract.

## Handoff rule

At meaningful session end, record exact commits, CI/production proof, risks and next exact action.
Never convert successful execution plumbing, a discovery leaderboard, a sparse backtest, or a
statistically invalid repeated search into a profitability/live-readiness claim.
