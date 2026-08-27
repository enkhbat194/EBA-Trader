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
- [x] Install passive Fast Momentum OPEN restart proof watcher (#43).
- [x] Obtain Fast restart/recovery production proof; latest exact-build external proof reports `fastRestartPhase=PASS` and `fastRestartPassed=true`.
- [x] Harden exact-build external proof so stale M5 FAILED/RUNNING markers cannot be accepted as successful terminal research proof (#52).
- [x] Verify exact build `7e24df486839c92f9c324cbd910efc00dfe7bc4d` with public production smoke, Demo reconnect, Chart, Positions, M5 terminal proof, frozen-OOS lock and real-execution lock.

## NOW — M5 real development ablation

- [x] Historical Binance USD-M `aggTrades` acquisition, sequence/integrity gating and causal alignment.
- [x] Allowlisted candle-only and order-flow adapters on the exact same aligned dataset.
- [x] Deterministic one-control-to-many-treatment order-flow ablation orchestration (#34).
- [x] Venue-matched verified BTCUSDT USD-M feature-dataset workflow (#35).
- [x] `eba-m5-real-ablation` verified queue emitter + initial Delta/CVD gate set + bounded one-command/runtime runner (#40/#45).
- [x] Lifecycle policy v2 requiring robustness before frozen OOS (#41).
- [x] Immutable baseline-vs-treatment comparison report with no edge/promotion authority (#45).
- [x] Bounded idempotent Linode autorun for the fixed `2026-08-01T00:00Z -> 04:00Z` development window (#45).
- [x] Diagnose historical REST HTTP 400 without moving the fixed study window.
- [x] Add official Binance public USD-M daily `aggTrades` archive acquisition with `.CHECKSUM` SHA-256 verification, exact-window filtering and archive provenance (#51).
- [x] Deploy archive acquisition to production and let the fixed real batch reach terminal `COMPLETE`.
- [x] Verify batch `abl_6c4a8eeb83a662894a3f2816`: `allTerminal=true`, `allExperimentsPassed=true`, `evidenceComplete=true`.
- [x] Verify frozen OOS remained closed and real execution remained locked throughout the run.
- [ ] Inspect immutable candle-only vs Delta/CVD per-treatment metrics in `/var/lib/eba-trader/research/evidence/m5-real-ablation-20260801T000000Z-20260801T040000Z.json`. Treat any improvement as development evidence only; no edge claim or lifecycle promotion.

## NEXT

- [ ] Add stacked/diagonal footprint imbalance candidates after interpreting the first real raw-trade development report.
- [ ] Add absorption/exhaustion candidates with causal definitions and tests.
- [ ] Add price/delta divergence candidates.
- [ ] Strengthen near-duplicate detection if factory volume requires it.
- [ ] Add cheap-screen -> development-screen orchestration over generated candidate families.
- [ ] Persist survivor/ranking evidence without granting lifecycle authority to ranking.
- [ ] Audit fresh-install provisioning of the M5 autorun timer; add it through a small audited change if the fresh-install path still omits it.

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
  - Remaining gate: immutable passing robustness evidence under v2 and explicit later lifecycle work. No manual bypass.

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
- [x] Lifecycle policy v2 robustness-before-OOS (#41).
- [x] External public production smoke and exact-build proof automation (#42).
- [x] Natural Fast restart proof watcher and eventual PASS proof (#43 + current production proof).
- [x] Legacy carry active-entry retirement (#44).
- [x] Verified historical Binance USD-M public archive path for fixed-window M5 research (#51, merge `1c1b683b7bfc9dd62cff9d96fcb3160213cd2595`).
- [x] Hardened M5 terminal production proof (#52, merge `7e24df486839c92f9c324cbd910efc00dfe7bc4d`).
- [x] First real fixed-window M5 development ablation completed with immutable evidence; batch `abl_6c4a8eeb83a662894a3f2816`.
