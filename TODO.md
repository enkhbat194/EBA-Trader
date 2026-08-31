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
- [x] Preserve the fixed 30-trade minimum; do not rescue sparse SF3 compression/expansion outcomes.
- [x] Keep every phase development-only and leave Frozen OOS sealed.

## NOW — Strategy Factory v2 discovery foundation

- [x] Decide that broad discovery and strict verification remain separate authorities.
- [x] Create `docs/STRATEGY_FACTORY_V2_DESIGN.md`.
- [x] Record the architecture decision in `docs/DECISION_STRATEGY_FACTORY_V2_2026-09-01.md`.
- [x] Create versioned pilot contract `config/strategy_factory_v2_pilot_v1.json`.
- [x] Hard-cap pilot raw candidates at 500.
- [x] Hard-cap candidates per family at 64.
- [x] Hard-cap discovery survivors at 30.
- [x] Add deterministic discovery candidate/spec identity.
- [x] Separate candidate budget from evaluation-trial count.
- [x] Add discovery-only immutable candidate/trial ledger.
- [x] Record dataset SHA and source-code SHA in the correct candidate/trial layers.
- [x] Add behavioral fingerprints and near-duplicate similarity filtering.
- [x] Add behavioral cluster report with raw/unique/cluster/family counts kept separate.
- [x] Add economic-first discovery-priority selection contract with no promotion/statistical authority.
- [x] Add bounded Strategy Family v2 registry.
- [x] Add deterministic quasi-random parameter sampling with replay seed/identity.
- [x] Add structural candidate identity/deduplication before evaluation.
- [x] Add compact in-process batch-evaluation interface for one loaded D0 dataset context.
- [x] Add compute-budget stop accounting at the batch boundary.
- [x] Add immutable discovery-survivor selection separate from evaluation results.
- [x] Test that a discovery survivor cannot promote durable StrategyLifecycle.
- [x] Add D1 hidden-confirmation freeze contract without opening D1.
- [x] Reject D1 dataset hashes already consumed by D0 discovery.
- [x] Reconcile `PROJECT_STATE.md` through completed SF3 production evidence.
- [x] Reconcile `BACKTEST_PROTOCOL.md` with lifecycle policy v2 and Strategy Factory v2 data zones.
- [x] Add pilot-contract parser/validator that fails closed on weakened authority, caps or data locks.
- [ ] Run full tests/Ruff on exact branch head.
- [ ] Open one coherent Strategy Factory v2 foundation PR.
- [ ] Fix every CI failure; merge only with all required checks green.

## NEXT — Strategy Factory v2 500-cap pilot

Only after the foundation PR is merged and production/runtime regression proof is clean:

- [ ] Register 8–12 economically distinct families compatible with available causal data.
- [ ] Generate up to 500 bounded raw candidates; stop early if novelty/compute rules trigger.
- [ ] Use only declared D0 discovery data.
- [ ] Account for every performance-inspected candidate in the trial ledger.
- [ ] Apply static sanity filters before performance simulation.
- [ ] Use stratified low-fidelity evaluation rather than chronological first-N racing.
- [ ] Cluster behavioral near-duplicates and keep representative candidates.
- [ ] Nominate at most 30 discovery survivors.
- [ ] Freeze survivor specs before any D1 hidden confirmation is opened.
- [ ] Treat zero survivors as a valid research result; do not expand the budget just to force a
      winner.

## THEN — Hidden confirmation and current strict EBA verification

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

## EXECUTION ARCHITECTURE HARDENING — AFTER FACTORY FOUNDATION

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
- [ ] Factory v2 D1 hidden confirmation — blocked until foundation + survivor freeze + separate
      confirmation authorization.
- [ ] Real-money Binance orders — intentionally locked.
- [ ] Resting LOB/order-book claims — require a separate reconstruction/integrity contract.

## Handoff rule

At meaningful session end, record exact commits, CI/production proof, risks and next exact action.
Never convert successful execution plumbing, a discovery leaderboard, a sparse backtest, or a
statistically invalid repeated search into a profitability/live-readiness claim.
