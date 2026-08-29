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

## IMPORTANT RESULT — robustness did not pass

`absorption_020` robustness proof completed safely but returned:

- `robustnessVerified=false`
- `centerProfitable=false`
- `sampleSufficient=false`
- cost-stress stable: true
- EMA stable: true
- parameter-neighborhood stable: true

Therefore:

- [x] Keep M5 Frozen OOS closed.
- [x] Keep real-money execution locked.
- [x] Do not promote `absorption_020`.
- [ ] Return Strategy Factory work to development-only candidate discovery/evaluation.

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

## NOW — Close the one-shot Demo probe safely

- [x] Change probe config to `enabled=false` on closeout branch.
- [x] Preserve an existing terminal Demo proof when the probe is disabled.
- [x] Add regression coverage proving disabled state cannot submit another order.
- [ ] Run exact-head full CI for `closeout-binance-demo-v4`.
- [ ] Merge only if every required check is green.
- [ ] Verify exact merged production build on Linode.
- [ ] Verify the preserved v4 proof remains `COMPLETE` after disabled deployment.
- [ ] Clean temporary proof branches when branch-delete authority is available.

## NEXT — Strategy Factory development, not Frozen OOS

- [ ] Inspect the 12-window 17-candidate aggregate evidence and identify why sample sufficiency/center profitability failed.
- [ ] Expand independent **development-only** evidence without touching the sealed M5 Frozen OOS.
- [ ] Improve candidate generation/selection with minimum activity and anti-duplicate constraints.
- [ ] Keep fees/slippage and cost-stress mandatory.
- [ ] Require a candidate to pass center profitability, sample sufficiency, cost stress, EMA stability and parameter-neighborhood stability.
- [ ] Only after a true robustness pass may Frozen OOS be considered.

## LATER

- [ ] Verified Strategy Knowledge Base.
- [ ] Forward-paper strategy factory.
- [ ] Professional trading-dashboard UI/UX pass after core research state is reconciled.
- [ ] Separate sequence-validated LOB/order-book data plane if evidence warrants it.
- [ ] Market Brain/regime selector after enough independently verified strategies exist.
- [ ] Strategy/portfolio selector, outcome attribution and drift monitoring.
- [ ] Explicit shadow -> micro-live -> live promotion gates only after required evidence exists.

## BLOCKED / GATED

- [ ] M5 Frozen OOS access — **blocked because robustness is not verified**.
- [ ] Real-money Binance orders — intentionally locked.
- [ ] Resting LOB/order-book claims — require a separate reconstruction/integrity contract.

## Handoff rule

At meaningful session end, record exact commits, CI/production proof, risks and the next exact action. Never convert a successful execution-plumbing proof into a profitability or live-readiness claim.
