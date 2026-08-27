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
- [x] Verify exact production build `93e684794cd692bf1534ec46a5c9186bb974bbb9` with public smoke, Demo reconnect, Chart, Positions, M5 terminal evidence, Fast restart proof, frozen-OOS lock and real-execution lock.
- [x] Expose sanitized immutable M5 report metrics through production Research proof (#54 / exact main `93e684794cd...`).

## NOW — M5 first real development evidence

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
  - Interpretation remains development evidence only; no edge claim or lifecycle promotion.

## NOW — Active branch: stacked / diagonal imbalance

Current active branch at handoff: `m5-stacked-imbalance-feature` head `ec015d6b54e72d8906cd1e80d299f4d2ed213de1`.

Already started on that branch:

- [x] Deterministic diagonal buy/sell footprint imbalance calculation.
- [x] Adjacent price-level comparison and configurable imbalance ratio contract.
- [x] Empty-diagonal / zero-volume protection against false infinite imbalance.
- [x] Consecutive price-level stack measurement.
- [x] Buy stack / sell stack / signed stacked score plumbing.
- [x] Causal closed-footprint feature propagation into footprint/feature dataset source.

Still required before this candidate is complete:

- [ ] Inspect branch diff against latest `main`; do not duplicate/restart the branch.
- [ ] Add deterministic tests for buy/sell diagonal directionality.
- [ ] Add zero-volume/empty-diagonal regression tests.
- [ ] Add consecutive-stack length/score regression tests.
- [ ] Add deterministic replay/input-order tests.
- [ ] Add causal availability/no-future-leakage tests.
- [ ] Finish feature CSV/schema compatibility and loader tests.
- [ ] Enable/allowlist `of_stacked_imbalance` only after feature contract is fully implemented.
- [ ] Add backtest adapter/gate consumption for stacked imbalance.
- [ ] Add a bounded controlled stacked gate set while keeping baseline, EMA, fee and slippage assumptions identical.
- [ ] Run full Python regression + Ruff + shell/deployment/continuity gates.
- [ ] Open PR and require exact PR-head green CI before merge.
- [ ] Merge only after required workflows pass.
- [ ] Exact-main Linode deploy/proof after merge.
- [ ] Run same fixed-window controlled stacked-imbalance ablation and persist immutable metrics.
- [ ] Compare return, expectancy, drawdown, cost, trade count and win rate vs candle baseline and prior Delta result.

## NEXT

- [ ] Add absorption/exhaustion candidates with causal definitions and tests.
- [ ] Add price/delta divergence candidates.
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

Before a new chat codes anything, it must read the canonical continuity files, verify actual GitHub `main`, active branch, open PRs/workflows, compare the active branch against main, and resume the valid existing branch/task. At session exit, record exact changed files, branch, PR, CI, merge SHA, production proof, unresolved risks and the next exact action.
