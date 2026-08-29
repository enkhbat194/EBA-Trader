# EBA Trader — Session Handoff

_Last handoff prepared: 2026-08-29 (Asia/Ulaanbaatar)_

## Exact continuation point

Repository: `enkhbat194/EBA-Trader`

Production `main` before this closeout PR:

`9ab6e70a4d5cbef7854facd48b13607ea3356b4b`

Current working branch:

`closeout-binance-demo-v4`

No open PR existed when this branch was created.

## What was completed

### M5 development corpus and evaluator

- `8f7d27922c60caf92e3f23fc988f0dbbba2b7e84` — resumable 12-window development corpus materializer.
- `d0de5fbfe33ecfaff50693637ec6ff38829ad81c` — production Linode corpus materialization.
- `40ec7761e27616621b563665697cbe0ff783336f` — deterministic 17-candidate multi-window evaluator.
- `e7d398903ebb635b3645b5ceca36112a07f0f4a7` — evaluator run across all 12 development windows on Linode.

### Robustness

`3dcfe48995b3662899105b710aa82c6a68ad093c` added and ran a fixed 9-scenario development-only robustness stage for `absorption_020`.

Exact production robustness proof run `33215478581`:

- robustness ID `m5rob_0ddaad97c4954b46ff7e9bcb`
- candidate `absorption_020`
- scenario count 9
- `robustnessVerified=false`
- `centerProfitable=false`
- `sampleSufficient=false`
- `costStressStable=true`
- `emaStable=true`
- `parameterNeighborhoodStable=true`
- Frozen OOS closed
- real execution locked

This means **do not open M5 Frozen OOS**. The candidate did not pass the required robustness gate.

### Binance USD-M Futures Demo execution plumbing

The one-shot execution runtime was implemented and iteratively fixed through production observations. PR #77 merged as:

`9ab6e70a4d5cbef7854facd48b13607ea3356b4b`

The final probe is:

`usdm-btcusdt-roundtrip-20260829-v4`

Exact production v4 proof workflow run `33243896565`, job `99077873835`: **SUCCESS**.

Measured result:

- phase `COMPLETE`, passed true
- environment Binance USD-M Futures Demo
- endpoint `demo-fapi.binance.com`
- BTCUSDT one-way position mode
- quantity `0.0007 BTC`
- effective notional `54.30901 USDT`
- available balance before `4999.89709561 USDT`
- BUY average fill `77584.6`
- SELL average fill `77584.1`
- both fill prices resolved from exact order query
- BUY slippage `+0.0386676170 bps`
- SELL slippage `+0.0322229934 bps`
- BUY order acknowledgement `212.033707 ms`
- SELL order acknowledgement `221.393951 ms`
- BUY fill lookup `216.710555 ms`
- SELL fill lookup `270.355526 ms`
- latest market-data age `618.613281 ms`
- full probe round-trip `3987.621519 ms`
- pre-position zero true
- post-position zero true
- real money false
- Frozen OOS locked
- real execution locked

This proves **execution plumbing/measurement only**. It is not strategy-profitability evidence and has no promotion authority.

## Current closeout changes

On branch `closeout-binance-demo-v4`:

1. `config/binance_demo_execution_probe_v1.json` is changed to `enabled=false`.
2. Disabled runtime now preserves an existing terminal Demo proof instead of overwriting it with `DISABLED`.
3. A regression test guarantees disabled state cannot invoke a new exchange-order probe.
4. `PROJECT_STATE.md`, `TODO.md` and this handoff are reconciled to actual current state.

Why this matters: leaving the same probe enabled was already idempotent while its persistent COMPLETE proof existed, but disabling it removes the remaining accidental re-execution path if state handling changes later. Preserving terminal proof keeps the successful production evidence visible after shutdown.

## Next exact task

1. Inspect PR #78 for `closeout-binance-demo-v4`.
2. Run exact-head full regression, Ruff, runtime, continuity and production-bundle checks.
3. Fix every failure; do not merge red CI.
4. Merge only when green.
5. Verify exact merged `main` deploys to Linode.
6. Confirm `/api/research/status` still exposes the v4 Demo proof as `COMPLETE` after the config is disabled.
7. Confirm no new order is submitted after disabled deployment.
8. Clean temporary proof branches when deletion authority is available.
9. Return to development-only Strategy Factory work: analyze the failed robustness reasons (`centerProfitable=false`, `sampleSufficient=false`) and build stronger independent development evidence without touching Frozen OOS.

## Hard locks

- Legacy 2025 Frozen OOS remains locked.
- M5 Frozen OOS (`2026-08-15 -> 2026-08-22` UTC) remains sealed/not opened.
- Real Binance execution remains locked.
- Demo execution has no strategy-promotion authority.
- Development/ranking results have no promotion authority.
- Fast Momentum remains paper-only and deterministic risk keeps final veto authority.

## Repository hygiene note

Temporary proof branches currently exist for corpus/multi-window/robustness/Demo verification. They are not canonical work. Keep `main` authoritative and prune the temporary proof refs once branch-delete authority is available; preserve `archive/legacy-experiments-20260828`.

## Startup rule

Read `AGENTS.md`, `PROJECT_STATE.md`, `ARCHITECTURE.md`, `DECISIONS.md`, `TODO.md`, `CHANGELOG.md`, this file and `docs/CONTINUITY_PROTOCOL.md`; then query actual GitHub and Linode proof state before editing.
