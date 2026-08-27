# EBA Trader — TODO

This list is ordered by current project priority and must be reconciled with actual GitHub/runtime state before a session starts.

## NOW — Verified production foundation

- [x] Recover Linode auto-update and persistent deployment diagnostics (#37).
- [x] Fix raw Binance per-tick INFO log growth and reclaim production disk (#38).
- [x] Repository-manage journald limits and persistent M4/M5 research paths (#40).
- [x] Save Binance Demo credentials encrypted on Linode; never return the secret to browser JavaScript (#36 + production proof).
- [x] Verify saved Demo reconnect after deployment restart (#42/#43 external proof).
- [x] Verify public Chart / Positions / Research server truth.
- [x] Retire legacy carry from active production entry authority (#44).
- [x] Obtain passive Fast Momentum restart/recovery production proof.
- [x] Harden terminal M5 production proof (#52).
- [x] Expose sanitized immutable M5 report metrics through production Research proof (#54).
- [x] Verify exact stacked-proof production build `738ed32e557045abb6b738c7f5236962ee3dd516` with production bundle, runtime checks, public smoke, Demo reconnect, Chart, Positions, Fast restart proof, stacked terminal evidence, frozen-OOS lock and real-execution lock.

## NOW — M5 Delta/CVD development evidence

- [x] Historical Binance USD-M `aggTrades` acquisition, sequence/integrity gating and causal alignment.
- [x] Allowlisted candle-only and order-flow adapters on the exact same aligned dataset.
- [x] Deterministic one-control-to-many-treatment order-flow ablation orchestration.
- [x] Venue-matched verified BTCUSDT USD-M feature-dataset workflow.
- [x] Bounded one-command/runtime real-ablation runner and immutable comparison reporting.
- [x] Official Binance public USD-M daily `aggTrades` archive acquisition with `.CHECKSUM` SHA-256 verification.
- [x] Complete fixed `2026-08-01T00:00Z -> 04:00Z` real development batch `abl_6c4a8eeb83a662894a3f2816`.
- [x] Verify `allTerminal=true`, `allExperimentsPassed=true`, `evidenceComplete=true`.
- [x] Verify frozen OOS remained closed and real execution remained locked.
- [x] Inspect and interpret candle-only vs Delta/CVD metrics.
  - Candle baseline total return ~`-0.42445%`, 4 trades, 25% win rate, cost `43.9048`, expectancy `-10.6112`.
  - Best tested Delta arm `delta_ratio_threshold=0.2`: total return ~`-0.12055%`, 2 trades, 50% win rate, cost `21.9992`, expectancy `-6.0277`.
  - Absolute loss reduced about 71.6%, but return/expectancy remain negative.
  - CVD-only did not add improvement in this run.
  - Development evidence only; no edge claim or lifecycle promotion.

## COMPLETE — M5 stacked / diagonal imbalance candidate

- [x] Resume the existing `m5-stacked-imbalance-feature` branch instead of restarting it.
- [x] Inspect existing branch diff against latest `main`.
- [x] Complete deterministic diagonal buy/sell footprint imbalance calculation.
- [x] Require true adjacent price buckets; missing buckets break diagonal comparison/stacks.
- [x] Protect zero/empty diagonal cells against false infinite imbalance.
- [x] Complete consecutive buy/sell stack measurement and signed score.
- [x] Add deterministic directionality, zero-volume, missing-bucket, stack-length/score and replay/input-order tests.
- [x] Preserve prior-closed-footprint causal availability and add no-future-leakage coverage.
- [x] Complete feature CSV/schema v2 compatibility while preserving legacy v1 Delta/CVD replay.
- [x] Enable/allowlist `of_stacked_imbalance` only after feature contract completion.
- [x] Add fail-closed backtest adapter/gate consumption for stacked imbalance.
- [x] Add bounded stacked gate set with thresholds `1/2/3`, keeping baseline/EMA/capital/fees/slippage assumptions identical.
- [x] Run full regression + Ruff + shell/deployment/continuity gates.
- [x] Open PR #56 and require exact PR-head green CI.
- [x] Merge PR #56; implementation main SHA `d15c29895d39ae6db5fabea4895daf7ad5facfa6`.
- [x] Add stacked-specific Linode autorun/immutable proof without overwriting prior Delta/CVD evidence.
- [x] Harden external proof so stale Delta-only evidence cannot satisfy the stacked milestone.
- [x] Open PR #57, pass exact-head required CI and merge to `738ed32e557045abb6b738c7f5236962ee3dd516`.
- [x] Exact-main Linode deploy/proof after merge.
- [x] Run the same fixed-window stacked ablation and persist immutable report `m5-stacked-imbalance-ablation-20260801T000000Z-20260801T040000Z.json`.
- [x] Verify batch `abl_232b7cb262de90363283356d`: terminal, all experiments passed, evidence complete, thresholds exactly `1/2/3`.
- [x] Compare stacked vs baseline and prior Delta evidence.
  - Baseline reproduced exactly: return ~`-0.42445%`, expectancy `-10.6112`, DD ~`-0.42445%`, cost `43.9048`, 4 trades, 25% win rate.
  - Best stacked threshold `1`: return ~`-0.12408%`, expectancy `-6.2041`, DD ~`-0.24164%`, cost `21.9825`, 2 trades, 50% win rate.
  - Threshold `1` reduced absolute baseline loss ~70.77%, but did not beat prior Delta `0.2` on return or expectancy.
  - Thresholds `2/3`: return ~`-0.13709%`, expectancy `-13.7091`, DD ~`-0.13709%`, cost `10.9947`, 1 trade, 0% win rate.
  - Stacked family receives no edge claim, survivor promotion, Frozen-OOS, paper/demo or execution authority.

## NOW — Next candidate: absorption / exhaustion

- [ ] Query actual latest `main`, open PRs and workflows after the continuity-only merge.
- [ ] Create a single fresh absorption/exhaustion branch from actual latest `main`.
- [ ] Define absorption/exhaustion from causal executed-trade footprint data without pretending executed flow reveals resting LOB liquidity.
- [ ] Specify bounded, deterministic candidate fields/parameters and explicit unavailable-data behavior.
- [ ] Add directionality, boundary, zero/low-volume, deterministic replay/input-order and no-future-leakage tests.
- [ ] Extend feature dataset/registry/backtest adapter through allowlisted fields only.
- [ ] Add a bounded controlled gate set while keeping the same candle baseline, EMA, capital, fees, slippage and fixed development window.
- [ ] Run full Python regression + Ruff + shell/deployment/continuity checks and fix every failure.
- [ ] Open one PR and require exact PR-head green CI before merge.
- [ ] Merge, deploy exact main to Linode and obtain exact public/external production proof.
- [ ] Run the same fixed `2026-08-01T00:00Z -> 04:00Z` development comparison.
- [ ] Compare return, expectancy, drawdown, cost, trade count and win rate against candle baseline, prior Delta and stacked results.
- [ ] Interpret as development evidence only; no automatic promotion.

## NEXT

- [ ] Add price/delta divergence candidates after absorption/exhaustion is closed and interpreted.
- [ ] Strengthen near-duplicate detection/orchestration as factory volume grows.
- [ ] Add cheap-screen -> development-screen orchestration over generated candidate families.
- [ ] Persist survivor/ranking evidence without granting lifecycle authority to ranking.
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
  - Lifecycle requires robustness-before-OOS and immutable passing evidence.
  - No manual/AI bypass.

- [ ] LOB/order-book strategy features.
  - Requires a separate approved snapshot/diff sequence-integrity reconstruction contract.
  - Do not infer resting liquidity from executed-trade footprint.

- [ ] Real-money Binance orders.
  - Intentionally locked pending the demo/shadow/micro-live evidence chain.

## CONTINUOUS-WORK HANDOFF RULE

Before a new chat codes anything, it must read the canonical continuity files, verify actual GitHub `main`, active branch, open PRs/workflows, compare any active branch against main, and resume the valid existing task. At session exit, record exact changed files, branch, PR, CI, merge SHA, production proof, unresolved risks and the next exact action.
