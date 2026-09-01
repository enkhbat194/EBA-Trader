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
- [x] Merge foundation with exact-head CI green.

## DONE — first executable Factory v2 pilot catalog

- [x] Register 8 economically distinct families using existing causal EBA engines.
- [x] Declare 406 bounded raw candidate slots rather than force the 500 maximum.
- [x] ATR trailing: 30.
- [x] Donchian breakout: 16.
- [x] z-score mean reversion: 64.
- [x] order-flow delta impulse: 40.
- [x] rolling flow trend: 64.
- [x] volume-shock momentum: 64.
- [x] VWAP reversion + flow: 64.
- [x] compression/expansion: 64.
- [x] Add deterministic candidate generation and replay tests.
- [x] Merge PR #100 with exact-head regression/Ruff/runtime/production checks green.

## DONE — Strategy Factory v2 common D0 evaluator

- [x] Add one discovery-only evaluator/adaptor interface for all 8 registered families.
- [x] Reuse existing causal backtest engines rather than fork strategy semantics.
- [x] Normalize low-fidelity D0 metrics: net return/expectancy, trades, drawdown, costs, benchmark
      delta, exposure and turnover.
- [x] Generate `BehavioralFingerprint` from actual D0 signals/trades/exposure/turnover.
- [x] Fail closed on invalid specs, unavailable order-flow data and zero-opportunity candidates.
- [x] Wire evaluator into `run_discovery_batch` so every inspected candidate is ledgered.
- [x] Enforce dataset SHA, source-code SHA, fidelity and compute accounting on every trial.
- [x] Merge PR #102 as `4c5a6a9fe30f29b772a5c2fe4d1e99b38b4262b1` with exact-head checks green.

## ACTIVE — SF4 prospective replication

- [x] Freeze exact `s3_vsm_s150` and `s3_cex_s075` parameters without retuning.
- [x] Preregister prospective BTCUSDT USD-M replication windows from 2026-09-01 through 2026-09-13.
- [x] Prohibit pooling SF3 trades/p-values into replication qualification.
- [x] Carry forward conservative multiplicity budget 48.
- [x] Lock evaluation before 2026-09-13T00:00:00Z.
- [ ] After the declared end time, evaluate the two frozen hypotheses on new data only.
- [ ] If replication fails, close it without lowering thresholds.
- [ ] If replication passes, preregister candidate-specific robustness before observing robustness
      results; passing still does not open Frozen OOS.

## NOW — immutable D0 dataset + stratified pilot input

- [ ] Add a versioned D0 dataset manifest with deterministic content hash.
- [ ] Explicitly label D0 as inspected/reusable discovery data, never fresh confirmation evidence.
- [ ] Hash candle content and executed-order-flow feature content independently plus composite
      dataset identity.
- [ ] Fail closed on time misalignment or non-causal order-flow availability.
- [ ] Partition D0 into declared temporal strata for low-fidelity racing.
- [ ] Require low-fidelity evaluation to cover every declared stratum instead of chronological
      first-N racing.
- [ ] Add tests proving content changes alter dataset identity and strata cover the full dataset.
- [ ] Reconcile `PROJECT_STATE.md` and `SESSION_HANDOFF.md` after merge.
- [ ] Merge only when exact-head regression, Ruff, runtime, production-bundle, continuity and hygiene
      checks are green.

## NEXT — bounded D0 pilot run

Only after the D0 manifest/stratification layer is merged:

- [ ] Materialize/declare the actual D0 discovery dataset and immutable dataset hash in production.
- [ ] Generate the declared 406 pilot candidates deterministically.
- [ ] Evaluate each low-fidelity candidate across all declared temporal strata.
- [ ] Stop early if compute or behavioral-novelty rules trigger; do not fill unused budget merely to
      reach a number.
- [ ] Account for every performance-inspected candidate in the trial ledger.
- [ ] Apply static sanity filters before low-fidelity simulation.
- [ ] Cluster behavioral near-duplicates and keep raw/unique/cluster/family counts distinct.
- [ ] Keep diverse representatives for higher-fidelity D0 racing.
- [ ] Nominate at most 30 discovery survivors.
- [ ] Treat zero survivors as a valid result.
- [ ] Freeze survivor specifications before any D1 hidden confirmation is opened.

## THEN — hidden confirmation and strict verification

- [ ] Open D1 only through a separately authorized hidden-confirmation workflow.
- [ ] Account for broad-search selection/multiple-testing history.
- [ ] Reject failed survivors without post-hoc retuning on D1.
- [ ] Use D2 for candidate-specific robustness only after confirmation survives.
- [ ] Keep robustness before Frozen OOS.
- [ ] Keep D3 Frozen OOS sealed until all prior gates pass.
- [ ] Forward paper only after strict research verification.
- [ ] Binance Demo only after paper and execution criteria; Demo is not a verification shortcut.
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

## EXECUTION ARCHITECTURE HARDENING — AFTER FACTORY D0

- [ ] Formalize strategy -> risk -> execution -> fill reconciliation -> position -> exit -> terminal
      evidence lifecycle.
- [ ] Keep exchange connector logic separate from strategy logic.
- [ ] Move toward identical strategy/time semantics across historical simulation, forward paper and
      later micro-live.
- [ ] Strengthen fill/slippage/funding/impact modeling before any profitability claim.

## LATER

- [ ] Verified Strategy Knowledge Base.
- [ ] Multi-symbol liquid Binance universe with predeclared universe-selection rule.
- [ ] Forward-paper strategy factory.
- [ ] Professional trading-dashboard UI/UX pass after core research engine stabilizes.
- [ ] Strategy decision trace/chart UI.
- [ ] Separate sequence-validated LOB/order-book data plane if evidence warrants it.
- [ ] Market Brain/regime selector after enough independently verified strategies exist.
- [ ] Portfolio selector, outcome attribution and drift monitoring.
- [ ] Explicit shadow -> micro-live -> live promotion gates only after required evidence exists.

## BLOCKED / GATED

- [ ] M5 Frozen OOS access — blocked because no candidate has passed full development/robustness
      gates.
- [ ] Factory v2 D1 hidden confirmation — blocked until D0 survivor freeze + separate confirmation
      authorization.
- [ ] SF4 evaluation before 2026-09-13T00:00:00Z — intentionally fail-closed.
- [ ] Real-money Binance orders — intentionally locked.
- [ ] Resting LOB/order-book claims — require a separate reconstruction/integrity contract.

## Handoff rule

At meaningful session end, record exact commits, CI/production proof, risks and next exact action.
Never convert successful execution plumbing, a discovery leaderboard, a sparse backtest, or a
statistically invalid repeated search into a profitability/live-readiness claim.
