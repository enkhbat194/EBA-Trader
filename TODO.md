# EBA Trader — TODO

Actual GitHub/runtime state overrides stale prose. Query `main`, open PRs and workflows before continuing.

## DONE — Repository/runtime foundation

- [x] Canonical GitHub `main` + Linode production path.
- [x] Production HTTPS/PWA/runtime proof and auto-update path.
- [x] Encrypted Binance Demo credential vault and reconnect proof.
- [x] Fast Momentum remains the sole active paper scanner.
- [x] Binance USD-M Futures Demo BUY/SELL round-trip execution plumbing proved without real money.
- [x] Keep real-money execution locked.

## DONE — M5 / SF1

- [x] Seal M5 development `2026-07-01 -> 2026-08-15` UTC and Frozen OOS `2026-08-15 -> 2026-08-22` UTC.
- [x] Reject historical `absorption_020`: sparse, negative expectancy, not robustness-verified.
- [x] Evaluate all 48 SF1 ATR, Donchian, z-score mean-reversion and raw order-flow candidates.
- [x] SF1 production result: zero verified candidates.
- [x] Close SF1 without post-hoc retuning on its inspected evidence.

## DONE — SF2 fresh development

- [x] Preregister 24 candidates across four independent order-flow families before fresh data inspection.
- [x] Use 12 fresh four-hour windows with no SF1 reuse and no 2026-08-01 smoke-day reuse.
- [x] Keep 48-hypothesis Bonferroni correction, 4 bps fees, 1.5 bps slippage and the fixed quality gate.
- [x] Implement causal next-open execution with no Frozen-OOS or live authority.
- [x] Build and production-run the fresh corpus -> 24 × 12 evaluator -> exact 4096 sign-flip -> validation pipeline.
- [x] Add sanitized production evidence proof and verify exact deployed result.
- [x] SF2 production result: `NO_VERIFIED_CANDIDATE`, `0/24` verified.
- [x] Reject top `s2_fpc_s030`: mean return about `-0.5505%`, mean expectancy about `-8.39`, 72 trades, only `5/12` baseline wins, adjusted p-value `1.0`.
- [x] Record the negative result in `docs/SF2_CLOSEOUT_2026-08-31.md`.
- [x] Close SF2 without promotion and without touching Frozen OOS.
- [x] Prohibit further SF2 threshold tuning on the inspected 12-window evidence.

## NOW — SF3 preregistration before fresh data

- [x] Create `config/sf3_research_protocol_v1.json` with 24 candidates and 12 new four-hour windows.
- [x] Exclude all SF1 and SF2 windows plus the original 2026-08-01 smoke day.
- [x] Keep the statistical correction budget at 48 even though SF3 has 24 active candidates.
- [x] Keep the quality gate unchanged: positive mean return, positive mean expectancy, >=30 trades, >=9/12 baseline wins, positive mean delta vs baseline, adjusted p <=0.05.
- [x] Keep fees at 4 bps and adverse slippage at 1.5 bps.
- [x] Preregister four new families, six candidates each: `rolling_flow_trend_v1`, `volume_shock_momentum_v1`, `vwap_reversion_flow_v1`, `compression_expansion_v1`.
- [x] Preregister slower anti-churn execution for this new phase: one-bar delay, minimum hold 4 bars, maximum hold 30 bars.
- [x] Add `sf3_protocol.py` validation that fails closed on prior-window reuse, smoke-day reuse, Frozen-OOS access, lowered search budget or weakened quality gates.
- [x] Add protocol regression tests.
- [ ] Finish exact-head CI for PR #95 and fix every failure.
- [ ] Merge only when regression, Ruff, runtime, continuity, hygiene and deployment checks are green.

## NEXT — Implement SF3 strategies before touching SF3 data

- [ ] Implement rolling multi-bar price + executed-flow trend confirmation.
- [ ] Implement relative-volume shock momentum.
- [ ] Implement rolling VWAP reversion with executed-flow reversal confirmation.
- [ ] Implement volatility-compression -> directional-expansion entries.
- [ ] Add causal/no-lookahead, long/short, fee/slippage, minimum/maximum hold and deterministic-repeat tests.
- [ ] Freeze SF3 implementation/configuration with green CI before materializing any SF3 fresh window.

## THEN — Fresh SF3 evidence

- [ ] Materialize only the 12 preregistered SF3 windows from Binance USD-M archives under a new immutable namespace.
- [ ] Verify acquisition provenance, hashes and non-overlap with Frozen OOS.
- [ ] Run all 24 SF3 candidates across all 12 fresh windows.
- [ ] Apply exact 4096 sign-flip tests and the fixed Bonferroni budget of 48.
- [ ] Reject every candidate that misses any quality criterion; do not lower thresholds.
- [ ] If zero pass, close SF3 and design a new fresh phase rather than retuning these windows.
- [ ] If one passes, build a candidate-specific fixed robustness suite before any Frozen-OOS consideration.

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
