# EBA Trader — TODO

Actual GitHub/runtime state overrides stale prose. Query `main`, open PRs and workflows before continuing.

## DONE — Repository/runtime foundation

- [x] Canonical GitHub `main` + Linode production path.
- [x] Production HTTPS/PWA/runtime proof and auto-update path.
- [x] Encrypted Binance Demo credential vault and reconnect proof.
- [x] Repository/branch hygiene automation and legacy archive.
- [x] Scanner-status UI hotfix; Fast Momentum remains the sole active paper scanner.

## DONE — M5 chronological development pipeline

- [x] Close the repeated single-window Delta/stacked/absorption-exhaustion/price-delta-divergence cycle without edge promotion.
- [x] Seal dedicated M5 development and Frozen-OOS chronology.
- [x] Pre-register 12 fresh non-overlapping development windows.
- [x] Materialize the 12-window corpus deterministically and resumably on Linode.
- [x] Verify per-window integrity/provenance and final manifest.
- [x] Implement the deterministic 17-candidate multi-window evaluator.
- [x] Run all 17 candidates across all 12 development windows on Linode.
- [x] Add/run a fixed 9-scenario robustness stage for `absorption_020`.
- [x] Diagnose the sparse top candidate by development window.
- [x] Add a qualification gate before robustness: positive mean return/expectancy, >=30 trades, and >=9 baseline-beating windows.

## IMPORTANT RESULT — current order-flow candidate did not pass

`absorption_020` remains development-only evidence:

- `robustnessVerified=false`
- `centerProfitable=false`
- `sampleSufficient=false`
- only 4 development trades in the prior aggregate result
- structurally it is an EMA-crossover entry filter, not an independent signal generator

Therefore:

- [x] Keep M5 Frozen OOS closed.
- [x] Keep real-money execution locked.
- [x] Do not promote `absorption_020`.
- [x] Return Strategy Factory work to development-only candidate discovery/evaluation.

## DONE — Binance USD-M Futures Demo execution plumbing

- [x] Add hard-locked one-shot BTCUSDT Demo BUY/SELL round-trip runtime.
- [x] Require flat pre-position and flat post-position.
- [x] Measure market-data age, request latency, fill lookup latency and slippage.
- [x] Fix flat-position lookup for a valid zero position.
- [x] Handle FILLED responses whose `avgPrice`/`price` are zero.
- [x] Resolve exact fill price through order query / account trade history.
- [x] Production v4 proof `usdm-btcusdt-roundtrip-20260829-v4` passed.
- [x] BUY fill `77584.6`, SELL fill `77584.1`, quantity `0.0007 BTC`.
- [x] BUY ack `212.03 ms`, SELL ack `221.39 ms`, full probe round-trip `3987.62 ms`.
- [x] Pre/post position zero, Demo only, real execution locked.
- [x] Disable the completed one-shot probe without losing terminal proof.
- [x] Merge disabled-probe closeout with green CI and verify production.

## DONE — external open-source architecture audit

- [x] Audit Freqtrade, NautilusTrader, Hummingbot, Jesse and QuantConnect LEAN for reusable patterns.
- [x] Record license constraints and adoption decisions in `docs/OSS_TRADING_PATTERN_AUDIT_2026-08-30.md`.
- [x] Do not copy GPL implementations into EBA Trader; use architecture ideas only unless licensing is explicitly changed.

## NOW — Strategy Factory: independent signals + stronger statistical gates

- [ ] Add independent strategy families rather than more filters on the EMA crossover baseline.
- [ ] First families: ATR trailing-stop, breakout, mean-reversion, order-flow impulse/divergence.
- [ ] Add an explicit look-ahead/causality audit inspired by mature trading frameworks.
- [ ] Expose deterministic candidate entry/trade samples from development backtests.
- [ ] Add a null-model/rule-significance gate before robustness promotion.
- [ ] Keep minimum activity, positive expectancy, fees/slippage and baseline coverage mandatory.
- [ ] Add Monte Carlo stress only after a candidate has adequate trade samples.
- [ ] Require center profitability, sample sufficiency, cost stress, parameter-neighborhood stability and statistical evidence before Frozen OOS can be considered.

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

At meaningful session end, record exact commits, CI/production proof, risks and the next exact action. Never convert a successful execution-plumbing proof into a profitability or live-readiness claim.
