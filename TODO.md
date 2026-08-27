# EBA Trader — TODO

This list is ordered by current project priority and must be reconciled with actual code/Git before a session starts.

## NOW — Production proof closure

- [x] Recover Linode auto-update and persistent deployment diagnostics (#37).
- [x] Fix raw Binance per-tick INFO log growth and reclaim production disk (#38).
- [x] Repository-manage journald limits and persistent M4/M5 research paths (#40).
- [x] Save a real Binance Demo key encrypted on Linode; never return the secret to browser JavaScript (#36 + production proof).
- [x] Verify saved Demo credentials reconnect without re-paste after application/service deployment restart (#42/#43 external proof).
- [x] Verify standalone Chart / Positions / Research server truth on public production (#42/#43).
- [x] Retire the older carry paper engine from active production entry authority (#44).
- [x] Verify exact #44 production build with Demo reconnect, Chart, Positions, frozen-OOS lock and real-execution lock.
- [x] Install passive Fast Momentum OPEN restart proof watcher (#43).
- [ ] Wait for a **natural** qualifying Fast Momentum paper OPEN and obtain full `OPEN -> service restart -> same-position recovery -> MARK -> CLOSE` production proof. Do not manufacture a trade.

## NOW — M5 real development ablation

- [x] Historical Binance USD-M `aggTrades` acquisition, sequence repair and integrity gating.
- [x] Causal closed-footprint/candle alignment and feature-dataset materialization.
- [x] Allowlisted candle-only and order-flow adapters on the exact same aligned dataset.
- [x] Deterministic one-control-to-many-treatment order-flow ablation orchestration (#34).
- [x] Venue-matched verified BTCUSDT USD-M feature-dataset workflow (#35).
- [x] `eba-m5-real-ablation` verified queue emitter + initial Delta/CVD gate set + one-command runner (#40).
- [x] Lifecycle policy v2 requiring robustness before frozen OOS (#41).
- [x] Add immutable baseline-vs-treatment comparison report with no edge/promotion authority (#45 candidate).
- [x] Add bounded idempotent Linode autorun for a 2026 development-only BTCUSDT window (#45 candidate).
- [x] Add sanitized autorun state to production proof without making M5 completion a deploy rollback gate (#45 candidate).
- [ ] Merge/deploy PR #45 after final reconciled CI remains green.
- [ ] Confirm `eba-m5-real-ablation.timer` is active on the exact #45 production build.
- [ ] Let the real `2026-08-01T00:00Z -> 04:00Z` USD-M dataset/experiment batch reach terminal COMPLETE or expose a real failure.
- [ ] Inspect immutable candle-only vs Delta/CVD metrics/evidence. Treat any improvement as development evidence only; no edge claim or lifecycle promotion.

## NEXT

- [ ] Add stacked/diagonal footprint imbalance candidates after the first real raw-trade development run is verified.
- [ ] Add absorption/exhaustion candidates with causal definitions and tests.
- [ ] Add price/delta divergence candidates.
- [ ] Strengthen near-duplicate detection if factory volume requires it.
- [ ] Add cheap-screen -> development-screen orchestration over generated candidate families.
- [ ] Persist survivor/ranking evidence without granting lifecycle authority to ranking.
- [ ] Bring the new M5 autorun timer into the fresh-install script through a separately audited small change; current production upgrade path is already provisioned.

## LATER

- [ ] Reconstruct and validate limit-order-book depth/imbalance as a separate sequence-sensitive dataset; do not infer LOB from executed-trade footprint.
- [ ] Build Verified Strategy Knowledge Base from strategies that pass the full validation path.
- [ ] Build forward-paper strategy factory.
- [ ] Build Binance Demo execution laboratory.
- [ ] Build market-regime selector / Market Brain only after enough independently verified strategies exist.
- [ ] Add portfolio selection, outcome attribution and drift monitoring.
- [ ] Define explicit shadow -> micro-live -> live promotion gates only after demo evidence exists.

## BLOCKED / GATED

- [ ] Automated frozen-OOS promotion.
  - Architecture blocker is resolved by lifecycle policy v2: `BACKTESTED -> ROBUSTNESS_VERIFIED -> OOS_VERIFIED`.
  - Remaining gate: immutable passing robustness evidence under v2. No manual bypass.

- [ ] LOB/order-book strategy features.
  - Blocked by: no approved snapshot/diff sequence-integrity reconstruction contract yet.
  - Required action: implement depth snapshot/diff validation separately from executed-trade footprint data.

- [ ] Real-money Binance orders.
  - Blocked by: intentional safety lock and missing demo/shadow/micro-live evidence chain.
  - Required action: later explicit milestone only.

## DONE RECENTLY

- [x] M4 strategy-platform foundation, restart-safe experiment queue, immutable evidence, development gates and robustness fan-out (#20-#24).
- [x] M5 executed-trade order-flow foundation, constrained DSL/factory, acquisition and same-dataset adapters (#25-#31).
- [x] Repository continuity system with CI guard (#29).
- [x] Research / AI Lab dashboard and Fast Momentum heartbeat (#32-#33).
- [x] Deterministic order-flow ablation orchestration (#34).
- [x] Venue-matched real USD-M feature-dataset workflow (#35).
- [x] Encrypted Binance Demo credential persistence (#36).
- [x] Production recovery/logging hardening (#37-#40).
- [x] Lifecycle policy v2 robustness-before-OOS (#41, merge `32a39c57cb9c86bd2b956ea670fa3031229d0efc`).
- [x] External public production smoke and exact-build proof automation (#42).
- [x] Natural Fast OPEN restart proof watcher (#43, merge `4a46a0fbec7d20007bda9061572756841de190c6`).
- [x] Legacy carry active-entry retirement (#44, merge `0df5f4d9a7ce054b1a2b65002b9329ba0c8143aa`, production-verified).
