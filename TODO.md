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
- [x] Preserve the fixed 30-trade minimum; do not rescue sparse outcomes.
- [x] Keep every phase development-only and leave Frozen OOS sealed.

## DONE — Strategy Factory v2 foundation and executable catalog

- [x] Separate broad discovery from strict verification authority.
- [x] Hard-cap raw candidates at 500, per-family candidates at 64, survivors at 30.
- [x] Add deterministic discovery candidate/spec identity and immutable trial ledger.
- [x] Add behavioral fingerprints, similarity and representative filtering.
- [x] Add bounded Strategy Family v2 registry and deterministic quasi-random sampling.
- [x] Register 8 executable causal families with 406 declared raw candidate slots.
- [x] Add common D0 evaluator/adaptor using existing causal EBA engines.
- [x] Normalize D0 metrics as selection-only evidence.
- [x] Add immutable D0 dataset manifest and temporal strata.
- [x] Explicitly label D0 `INSPECTED_REUSABLE_DISCOVERY_DATA`.
- [x] Add D1 hidden-confirmation freeze contract without opening D1.
- [x] Reject D1 hashes already consumed by D0.

## DONE — PR #104 / #105 / #106 production-D0 preparation

- [x] PR #104: stratified low-fidelity orchestration, per-stratum identities and all-strata
  completeness accounting.
- [x] PR #104: exclude rejected/incomplete candidates from behavioral representative selection.
- [x] PR #105: bind D0 only to the already-inspected default M5 development corpus.
- [x] PR #105: validate exact 12 source windows, feature-file SHA values and dataset-root containment.
- [x] PR #106: add existing-only production loader that cannot fetch/rebuild missing evidence.
- [x] PR #104, #105 and #106 exact-head CI verified green before merge.
- [x] Exact `main` `78fcb3d8ad4bc7eef559932bb836a4eedf251630` production bundle/runtime checks verified green.
- [x] Audit repository for accidental `PLACEHOLDER` content after #106 branch recovery: none on main.

## ACTIVE — audit hardening PR #107

The post-merge audit found two pre-pilot defects. Do not run the production pilot until both are
fixed and exact-head CI is green.

- [x] Prevent D0 warmup from crossing temporal discontinuities between independently sampled source
  windows.
- [x] Add regression coverage for a multi-day source gap.
- [x] Make discovery batches reuse already-terminal immutable trials during resume instead of
  evaluating them again.
- [x] Keep resumed terminal trials out of new compute accounting.
- [x] Add resume/idempotent replay tests.
- [ ] Complete PR #107 exact-head CI and merge only if regression, Ruff, runtime,
  production-bundle, continuity and hygiene checks are all green.

## ACTIVE — SF4 prospective replication

- [x] Freeze exact `s3_vsm_s150` and `s3_cex_s075` parameters without retuning.
- [x] Preregister prospective BTCUSDT USD-M data from `2026-09-01T00:00:00Z` through
  `2026-09-13T00:00:00Z`.
- [x] Prohibit pooling SF3 evidence into replication qualification.
- [x] Carry forward conservative multiplicity budget 48.
- [x] Lock evaluation before `2026-09-13T00:00:00Z`.
- [ ] After the declared end time, evaluate the two frozen hypotheses on new data only.
- [ ] If replication fails, close it without lowering thresholds.
- [ ] If replication passes, preregister candidate-specific robustness before robustness results.

## NEXT — bounded production D0 pilot run

Only after PR #107 merges:

- [ ] Load/declare D0 from the complete pre-existing inspected M5 development materialization only.
- [ ] If production evidence is absent/incomplete/hash-mismatched, fail closed; do not acquire a
  replacement corpus under this workflow.
- [ ] Persist/report immutable D0 source declaration and dataset SHA.
- [ ] Generate the declared 406 pilot candidates deterministically.
- [ ] Evaluate every candidate across every declared temporal stratum.
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

- [ ] Production 406-candidate D0 execution — blocked until PR #107 exact-head green + merge.
- [ ] M5 Frozen OOS access — blocked because no candidate passed prior strict gates.
- [ ] Factory v2 D1 hidden confirmation — blocked until D0 survivor freeze + separate authorization.
- [ ] SF4 evaluation before `2026-09-13T00:00:00Z` — intentionally fail-closed.
- [ ] Real-money Binance orders — intentionally locked.
- [ ] Resting LOB/order-book claims — require separate reconstruction/integrity contract.

## Handoff rule

At meaningful session end, record exact commits, CI/production proof, risks and next exact action.
Never convert successful execution plumbing, a discovery leaderboard, a sparse backtest, or a
statistically invalid repeated search into a profitability/live-readiness claim.
