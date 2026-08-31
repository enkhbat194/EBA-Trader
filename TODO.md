# EBA Trader — TODO

Actual GitHub/runtime state overrides stale prose. Query `main`, open PRs and workflows before continuing.

## DONE — Repository/runtime foundation

- [x] Canonical GitHub `main` + Linode production path.
- [x] Production HTTPS/PWA/runtime proof and auto-update path.
- [x] Encrypted Binance Demo credential vault and reconnect proof.
- [x] Repository/branch hygiene automation and legacy archive.
- [x] Fast Momentum remains the sole active paper scanner.
- [x] Binance USD-M Futures Demo BUY/SELL round-trip execution plumbing proved without real money.
- [x] Completed one-shot Demo probe disabled while preserving terminal proof.

## DONE — M5 chronological development foundation

- [x] Seal M5 development range `2026-07-01 -> 2026-08-15` UTC.
- [x] Seal M5 Frozen OOS `2026-08-15 -> 2026-08-22` UTC.
- [x] Materialize and verify the original 12-window development corpus.
- [x] Reject `absorption_020`: 4 trades, negative expectancy, not profitable, not sample-sufficient, not robustness-verified.
- [x] Keep Frozen OOS closed and real-money execution locked.

## DONE — SF1 independent-family search

- [x] Evaluate 48/48 preregistered ATR, Donchian, z-score mean-reversion and raw order-flow impulse candidates.
- [x] Use 12 development windows, 4 bps fees, 1.5 bps adverse slippage and causal next-open execution.
- [x] Apply the fixed 48-hypothesis Bonferroni correction.
- [x] Production result: `validationState=NO_VERIFIED_CANDIDATE`, `verifiedCandidateCount=0`.
- [x] Reject `mr_48z15x00` despite 10/12 baseline beats and 30 trades because return/expectancy were negative and adjusted p ~0.246.
- [x] Reject raw order-flow impulse family: 0/12 baseline wins and negative economics.
- [x] Close SF1 without an edge/profitability claim and prohibit further post-hoc retuning on the same evidence.

## DONE — SF2 preregistration and signal freeze

- [x] Preregister 12 fresh non-overlapping four-hour development windows.
- [x] Exclude all SF1 windows and the previously inspected 2026-08-01 smoke day.
- [x] Keep Bonferroni budget at 48 with 24 active candidates.
- [x] Keep fees 4 bps, slippage 1.5 bps, one-bar execution delay, minimum hold 2 bars, maximum hold 12 bars.
- [x] Keep qualification thresholds fixed: positive mean return/expectancy, >=30 trades, >=9/12 baseline wins, adjusted p <=0.05.
- [x] Implement and freeze six candidates each for `divergence_reversal_v1`, `absorption_reversal_v1`, `stacked_delta_continuation_v1`, `flow_price_continuation_v1`.
- [x] Pass causality, no-lookahead, long/short, fee/slippage, hold-time and terminal-close tests.
- [x] Merge signal implementation and verify exact production build `28c6d12f378433395118b024a0a4132c6d4edf5d`.

## NOW — M5 / SF2 fresh development pipeline

- [x] Add custom SF2 corpus/evaluator that consumes only the preregistered fresh corpus.
- [x] Add fixed EMA 12/26 development comparison baseline with identical 4 bps fee / 1.5 bps slippage assumptions.
- [x] Add 24 × 12 development evaluation and immutable evidence output.
- [x] Add exact 4096 sign-flip null-model validation with Bonferroni budget 48.
- [x] Require positive mean delta vs baseline in addition to the preregistered quality gate.
- [x] Add resumable production runtime and reusable terminal status.
- [x] Add sanitized read-only `sf2` dashboard summary; never expose evidence paths, dataset refs or credentials.
- [x] Integrate SF2 into maintenance as an independent development stage, not under legacy `absorption_020` robustness authority.
- [x] Add tests for significance, runtime reuse/failure safety, dashboard sanitization and maintenance independence.
- [ ] Finish exact-head CI for `sf2-fresh-corpus-evaluation-pipeline`; fix every failure before merge.
- [ ] Merge only when full regression, Ruff, runtime, continuity, repository hygiene and deployment-contract checks are green.
- [ ] Verify exact merged production build on Linode.
- [ ] Confirm production maintenance materializes all 12 fresh SF2 windows with archive provenance and SHA-256 integrity.
- [ ] Read sanitized production SF2 evaluation/validation result from `/api/research/status`.

## THEN — Decide from fresh SF2 evidence

- [ ] If `verifiedCandidateCount=0`, close SF2 without promotion; do not touch Frozen OOS.
- [ ] If a candidate becomes robustness-eligible, freeze a candidate-appropriate robustness suite before running it.
- [ ] Require cost stress, parameter-neighborhood stability, center profitability and sample sufficiency in robustness.
- [ ] Open M5 Frozen OOS only after the complete development + robustness gates pass.
- [ ] Keep real-money execution locked throughout this research phase.

## FIXED QUALITY GATE — DO NOT LOWER

A candidate may enter robustness only if all are true:

- [x] mean return > 0;
- [x] mean expectancy > 0;
- [x] total trades >= 30;
- [x] baseline beaten in >=9/12 windows;
- [x] mean return delta vs baseline > 0;
- [x] Bonferroni-adjusted exact sign-flip p-value <= 0.05.

Passing this gate still does not open Frozen OOS. Robustness remains mandatory afterward.

## NEXT — execution architecture hardening

- [ ] Formalize strategy -> risk -> execution -> fill reconciliation -> position -> exit -> terminal evidence lifecycle.
- [ ] Keep exchange-specific connector logic separate from strategy logic.
- [ ] Move toward identical strategy/time semantics across historical simulation, forward paper and later micro-live.
- [ ] Strengthen fill/slippage modeling before any profitability claim.

## LATER

- [ ] Verified Strategy Knowledge Base.
- [ ] Forward-paper strategy factory.
- [ ] Professional trading-dashboard UI/UX pass after core research state is reconciled.
- [ ] Strategy decision trace/chart UI.
- [ ] Separate sequence-validated LOB/order-book data plane if evidence warrants it.
- [ ] Market Brain/regime selector after enough independently verified strategies exist.
- [ ] Strategy/portfolio selector, outcome attribution and drift monitoring.
- [ ] Explicit shadow -> micro-live -> live promotion gates only after required evidence exists.

## BLOCKED / GATED

- [ ] M5 Frozen OOS access — **blocked because no candidate has passed the full development/robustness/statistical gates**.
- [ ] Real-money Binance orders — intentionally locked.
- [ ] Resting LOB/order-book claims — require a separate reconstruction/integrity contract.

## Handoff rule

At meaningful session end, record exact commits, CI/production proof, risks and the next exact action. Never convert successful execution plumbing, a development leaderboard, or a statistically invalid repeated search into a profitability/live-readiness claim.
