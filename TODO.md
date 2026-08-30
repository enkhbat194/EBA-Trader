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
- [x] Run multi-window order-flow development research.
- [x] Diagnose `absorption_020` as a sparse EMA-crossover entry filter rather than an independent signal generator.
- [x] Reject `absorption_020`: only 4 trades, negative expectancy, not profitable, not sample-sufficient, not robustness-verified.
- [x] Keep Frozen OOS closed and real-money execution locked.

## DONE — SF1 independent-family search

- [x] Add 12 ATR trailing-stop candidates.
- [x] Add 12 Donchian breakout candidates.
- [x] Add 12 z-score mean-reversion candidates.
- [x] Add 12 independent long/short raw footprint-delta impulse candidates.
- [x] Fill the entire preregistered SF1 search budget: `48/48` candidates.
- [x] Use the same 12 development windows, 4 bps fees, 1.5 bps adverse slippage and causal next-open execution.
- [x] Apply the fixed 48-hypothesis Bonferroni correction.
- [x] Production-run all 48 candidates on exact build `0f6d0c1d7c74f8a42ae16921d24dfe446d805380`.
- [x] Production proof passed structurally with `validationState=NO_VERIFIED_CANDIDATE` and `verifiedCandidateCount=0`.
- [x] Reject top development candidate `mr_48z15x00`: 10/12 baseline beats and 30 trades, but negative mean return, negative mean expectancy and adjusted p-value ~0.246.
- [x] Reject all 12 raw order-flow impulse candidates: adequate sample but 0/12 baseline beats, negative return/expectancy and adjusted p-value 1.0.
- [x] Close SF1 without an edge/profitability claim.

## FIXED QUALITY GATE — DO NOT LOWER

A candidate may enter robustness only if all are true:

- [x] mean return > 0;
- [x] mean expectancy > 0;
- [x] total trades >= 30;
- [x] baseline beaten in >=9/12 windows;
- [x] Bonferroni-adjusted p-value <= 0.05.

Passing this gate still does not open Frozen OOS. Robustness remains mandatory afterward.

## NOW — SF2 fresh-development preregistration

- [x] Stop adding candidates to SF1 after its 48/48 budget is consumed.
- [x] Explicitly prohibit pretending another pass over the same 12 SF1 windows is fresh verification.
- [x] Select 12 new non-overlapping 4-hour windows inside the sealed M5 development period.
- [x] Exclude every SF1 window and the previously inspected 2026-08-01 smoke day.
- [x] Keep the statistical correction budget at 48 even though SF2 has only 24 active candidates.
- [x] Keep fees at 4 bps and slippage at 1.5 bps.
- [x] Keep the quality gate unchanged.
- [x] Preregister four SF2 families with six candidates each in `config/sf2_research_protocol_v1.json`.
- [x] Add code validation that rejects SF1-window reuse, smoke-day reuse, changed execution assumptions, lowered statistical budget or weakened qualification gates.
- [x] Add regression tests for the protocol.
- [ ] Finish CI for `sf1-closeout-sf2-preregistration` and merge only if all checks pass.

## NEXT — Implement SF2 candidates before touching fresh data

- [ ] Implement `divergence_reversal_v1` as an independent entry generator from already-closed price/Delta divergence.
- [ ] Implement `absorption_reversal_v1` as an independent executed-flow response signal, not an EMA filter.
- [ ] Implement `stacked_delta_continuation_v1` with stacked imbalance + Delta confirmation.
- [ ] Implement `flow_price_continuation_v1` using only already-closed price response plus already-available executed flow.
- [ ] Enforce fixed `minimum_hold_bars=2` and `max_hold_bars=12` to reduce the raw-delta churn failure mode.
- [ ] Add long/short, no-lookahead, causality, cost, hold-time and terminal-close tests.
- [ ] Freeze candidate implementation/configuration before any fresh SF2 dataset is materialized or evaluated.

## THEN — Fresh SF2 evidence

- [ ] Materialize the preregistered 12-window SF2 corpus from Binance USD-M daily aggregate-trade archives using a distinct immutable corpus/materialization ID.
- [ ] Verify archive checksum, acquisition provenance, feature hashes and non-overlap with M5 Frozen OOS.
- [ ] Run all 24 SF2 candidates across all 12 fresh development windows.
- [ ] Use 4096 sign-flip permutations and the conservative 48-hypothesis Bonferroni budget.
- [ ] Reject every candidate that misses any fixed quality-gate condition.
- [ ] Run robustness only for a candidate that passes the entire development gate.
- [ ] Keep M5 Frozen OOS sealed unless development + robustness both pass.

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
