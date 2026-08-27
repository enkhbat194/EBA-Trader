# EBA Trader — TODO

This list is ordered by current project priority and must be reconciled with actual code/Git before a session starts.

## NOW — Production hardening / continuity closure

- [x] Recover a stuck Linode auto-update path and add persistent deployment diagnostics (#37).
- [x] Identify and fix the ~18 GB log-growth root cause: raw Binance ticks were being emitted at INFO (#38).
- [x] Reclaim old oversized logs; production disk fell from ~90.1% used to ~21% and `/var/log` to ~162M.
- [x] Apply the initial production-local journald cap (`SystemMaxUse=250M`, `SystemKeepFree=1G`, `MaxRetentionSec=7day`).
- [x] Codify those journald limits in repository install/update provisioning with regression coverage (#40).
- [x] Provision persistent M4/M5 research DB/dataset/evidence paths under `/var/lib/eba-trader/research/...` without coupling them to runtime `TradeLedger` (#40).
- [x] Add a bounded systemd research worker timer using the persistent research control plane (#40).
- [x] Production PWA reports server build `8876bc2`, proving PR #40 reached the active Linode runtime.
- [ ] Verify the PR #40 server-internal runtime contract directly: journald drop-in values, persistent research paths and `eba-research-worker.timer` active on Linode.
- [ ] Verify standalone Chart / Positions / Research screens against server truth.
- [x] Enter a real Binance Demo key/secret once through the PWA and verify the UI reports it encrypted/saved on Linode; the secret never returns to the browser.
- [ ] Verify the saved Demo credential reconnects without re-paste after a real app/server restart.
- [ ] Perform one real service/server restart and prove Fast Momentum `OPEN -> recovery -> MARK/CLOSE` persistence in production SQLite.
- [ ] Audit the older carry paper engine and either persist/recover it intentionally or retire it explicitly.

## NOW — M5 AI Strategy Factory / Order-Flow Ablation

- [x] Historical Binance `aggTrades` acquisition, sequence repair and integrity gating.
- [x] Causal closed-footprint/candle alignment and feature-dataset materialization.
- [x] Allowlisted candle-only and order-flow adapters on the exact same aligned dataset.
- [x] Deterministic one-control-to-many-treatment order-flow ablation orchestration (#34).
- [x] Venue-matched verified BTCUSDT USD-M feature-dataset workflow (#35).
- [x] Add `eba-m5-real-ablation`: verify workflow/feature hashes, venue, path containment and frozen-OOS separation, then emit deterministic M4 experiment IDs (#40).
- [x] Add versioned initial Delta/CVD ablation gate set and a one-command Linode build -> queue -> worker/evidence runner (#40).
- [x] Keep the real-ablation path development-only; it has no OOS, lifecycle-promotion, Demo-order or real-order authority.
- [x] Implement lifecycle policy v2 so robustness is required before frozen OOS, including legacy SQLite migration/freeze rules and regression tests (#41 candidate).
- [ ] Run the real BTCUSDT USD-M development feature build on Linode for a development-only window outside frozen OOS.
- [ ] Run the resulting candle-only vs Delta/CVD batch through M4 queue/worker/immutable evidence.
- [ ] Apply the same declared development/robustness policy to the arms and compare survivors; do not promote from win rate alone.
- [ ] Persist a machine-readable ablation comparison/verdict artifact if the first real run proves the execution pipeline sound.

## NEXT

- [ ] Add stacked/diagonal footprint imbalance candidates after the first real raw-trade development run is verified.
- [ ] Add absorption/exhaustion candidates with causal definitions and tests.
- [ ] Add price/delta divergence candidates.
- [ ] Strengthen near-duplicate detection if factory volume requires it.
- [ ] Add cheap-screen -> development-screen orchestration over generated candidate families.
- [ ] Persist survivor/ranking evidence without granting lifecycle authority to ranking.

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
  - Remaining gate: a strategy must produce immutable passing robustness evidence under v2 before any frozen-OOS opening is eligible; no manual bypass.

- [ ] LOB/order-book strategy features.
  - Blocked by: no approved snapshot/diff sequence-integrity reconstruction contract yet.
  - Required action: implement depth snapshot/diff validation separately from executed-trade footprint data.

- [ ] Real-money Binance orders.
  - Blocked by: intentionally locked safety policy and missing demo/shadow/micro-live evidence chain.
  - Required action: later explicit milestone only.

## DONE RECENTLY

- [x] M4 strategy-platform foundation, restart-safe experiment queue, evidence worker, development gates and robustness fan-out (#20-#24).
- [x] M5 order-flow/footprint foundation, constrained DSL/factory, real event acquisition and same-dataset adapters (#25-#31).
- [x] Repository continuity system with CI guard (#29).
- [x] Research / AI Lab dashboard and Fast Momentum heartbeat/label clarification (#32-#33).
- [x] Deterministic order-flow ablation orchestration (#34).
- [x] Venue-matched real USD-M feature-dataset workflow (#35).
- [x] Encrypted one-time Binance Demo credential persistence (#36), now with real production save proof from the PWA.
- [x] Linode auto-update recovery/diagnostics (#37).
- [x] Binance market-data log-flood fix and production disk recovery (#38 + manual recovery evidence).
- [x] Continuity reconciliation through production recovery (#39).
- [x] Persistent production research runtime, journald provisioning and real M5 ablation CLI/runner (#40, merge `8876bc22b59f236e8df038440aaa6116c5d1afdf`).
