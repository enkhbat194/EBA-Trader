# EBA Trader — TODO

This list is ordered by current project priority and must be reconciled with actual GitHub/runtime state before a session starts.

## NOW — Verified production foundation

- [x] Recover Linode auto-update and persistent deployment diagnostics (#37).
- [x] Fix raw Binance per-tick INFO log growth and reclaim production disk (#38).
- [x] Repository-manage journald limits and persistent M4/M5 research paths (#40).
- [x] Save Binance Demo credentials encrypted on Linode; never return the secret to browser JavaScript (#36 + production proof).
- [x] Verify saved Demo reconnect after deployment restart.
- [x] Verify public Chart / Positions / Research server truth.
- [x] Retire legacy carry from active production entry authority (#44).
- [x] Obtain passive Fast Momentum restart/recovery production proof.
- [x] Harden terminal M5 production proof (#52).
- [x] Expose sanitized immutable M5 report metrics through production Research proof (#54).
- [x] Verify exact response-proof production build `a49790838064769768fe4ca9fe500f6ed941ba82` with production bundle, runtime checks, public smoke, Demo reconnect, Chart, Positions, Fast restart proof, terminal M5 evidence, Frozen-OOS lock and real-execution lock.

## COMPLETE — M5 Delta/CVD development evidence

- [x] Historical Binance USD-M `aggTrades` acquisition, sequence/integrity gating and causal alignment.
- [x] Allowlisted candle-only and order-flow adapters on the exact same aligned dataset.
- [x] Deterministic one-control-to-many-treatment order-flow ablation orchestration.
- [x] Fixed `2026-08-01T00:00Z -> 04:00Z` development batch.
- [x] Interpret metrics without promotion authority.
  - Baseline: return ~`-0.42445%`, 4 trades, 25% win rate, expectancy `-10.6112`.
  - Best tested Delta `0.2`: return ~`-0.12055%`, 2 trades, 50% win rate, expectancy `-6.0277`.
  - Delta reduced absolute baseline loss ~71.6% but remained negative.

## COMPLETE — M5 stacked / diagonal imbalance candidate

- [x] Deterministic diagonal buy/sell imbalance and true adjacent-price-bucket handling.
- [x] Consecutive stacked measurement, signed score and zero-volume protection.
- [x] Feature-dataset v2 + legacy v1 replay compatibility.
- [x] Allowlisted/fail-closed stacked adapter/gate.
- [x] Bounded thresholds `1/2/3`.
- [x] Exact-head CI, PR #56/#57 merge and Linode exact production proof.
- [x] Same fixed-window comparison.
  - Best stacked threshold `1`: return ~`-0.12408%`, 2 trades, 50% win rate, expectancy `-6.2041`.
  - Improved baseline but did not beat Delta `0.2` on return/expectancy.
  - No edge/promotion authority.

## COMPLETE — M5 absorption / exhaustion candidate

- [x] Query actual latest GitHub/runtime state before implementation.
- [x] Implement causal executed-trade absorption/exhaustion **proxies** without pretending they reveal resting LOB liquidity.
- [x] Add versioned feature-dataset v3 materialization.
- [x] Add allowlisted/fail-closed research feature consumption; legacy files without physical v3 columns cannot silently pass.
- [x] Add deterministic directionality, boundary, zero/low-volume, replay/input-order and no-future-leakage tests.
- [x] Add bounded response gate set: absorption `0.10/0.20`, exhaustion `0.01/0.03`.
- [x] Run full Python regression + Ruff + shell/deployment/runtime/continuity checks; fix failures.
- [x] Merge implementation PR #59: `a48fdb6a7845390cf3dcad9f5e649d4b716a12b1`.
- [x] Preserve prior Delta/stacked immutable reports and add a separate response report.
- [x] Harden external proof so stale stacked evidence cannot satisfy the response milestone.
- [x] Merge production-proof PR #60: `a49790838064769768fe4ca9fe500f6ed941ba82`.
- [x] Exact-main Linode production proof: run `33081041663` PASS.
- [x] Same fixed-window batch `abl_c9bf89e7fb1dd4971345d87d` terminal, all experiments passed, evidence complete.
- [x] Interpret response treatments:
  - Absorption `0.10/0.20`: return ~`-0.16740%`, 1 trade, 0% win rate, expectancy `-16.7400`, cost `10.9930`; baseline absolute loss reduction ~60.56%, but worse than Delta/stacked.
  - Exhaustion `0.01/0.03`: 0 trades, 0 exposure/cost; **not profitable-edge evidence**.
  - No edge claim, survivor promotion, Frozen-OOS, paper/demo or execution authority.

## NOW — Next candidate: price / delta divergence

- [ ] Query actual latest `main`, open PRs and workflows after this continuity merge.
- [ ] Create one fresh divergence branch from actual latest `main`.
- [ ] Define divergence causally: local price high/low versus **already-closed** executed-flow Delta confirmation/failure; do not use future pivot bars.
- [ ] Specify bounded lookback, minimum price excursion, minimum executed-flow activity and confirmation rules.
- [ ] Fail closed on insufficient history, missing versioned fields or malformed/non-finite values.
- [ ] Add bullish/bearish directionality, flat-price, zero/low-volume, boundary, deterministic replay/input-order and no-future-leakage tests.
- [ ] Extend versioned feature materialization/registry/backtest adapter only through bounded allowlisted fields.
- [ ] Add a small controlled divergence gate set while keeping baseline, EMA, capital, fees/slippage and fixed development window identical.
- [ ] Run full regression + Ruff + shell/deployment/runtime/continuity checks and fix every failure.
- [ ] Open one PR and require exact PR-head green CI before merge.
- [ ] Merge, deploy exact main to Linode and obtain exact public/external production proof.
- [ ] Run the same fixed `2026-08-01T00:00Z -> 04:00Z` development comparison.
- [ ] Compare return, expectancy, drawdown, cost, trade count and win rate against candle baseline, Delta, stacked and response results.
- [ ] Interpret as development evidence only; do not open Frozen OOS from a development win.

## NEXT — M5 factory hardening after divergence

- [ ] Strengthen near-duplicate detection/orchestration as factory volume grows.
- [ ] Add cheap-screen -> development-screen orchestration over generated candidate families.
- [ ] Persist survivor/ranking evidence without granting lifecycle authority to ranking.
- [ ] Add candidate-quality rules so zero-trade/near-zero-exposure arms are not ranked as winners.
- [ ] Audit fresh-install provisioning of M5 autorun if still needed.

## LATER

- [ ] Reconstruct/validate LOB depth imbalance as a separate sequence-sensitive data plane.
- [ ] Build Verified Strategy Knowledge Base from full-path survivors.
- [ ] Build forward-paper strategy factory.
- [ ] Build Binance Demo execution laboratory.
- [ ] Build Market Brain / regime selector after enough independently verified strategies exist.
- [ ] Add strategy selector, portfolio selector, outcome attribution and drift monitoring.
- [ ] Define explicit shadow -> micro-live -> live promotion gates only after required evidence exists.

## BLOCKED / GATED

- [ ] Frozen-OOS promotion.
  - Lifecycle policy v2 requires robustness-before-OOS and immutable passing evidence.
  - No manual/AI bypass.

- [ ] LOB/order-book strategy features.
  - Requires a separate approved snapshot/diff sequence-integrity reconstruction contract.
  - Do not infer resting liquidity from executed-trade footprint.

- [ ] Real-money Binance orders.
  - Intentionally locked pending the demo/shadow/micro-live evidence chain.

## CONTINUOUS-WORK HANDOFF RULE

Before a new chat codes anything, it must read the canonical continuity files, verify actual GitHub `main`, active branch, open PRs/workflows, compare any active branch against main, and resume the valid existing task. At session exit, record exact changed files, branch, PR, CI, merge SHA, production proof, unresolved risks and the next exact action.
