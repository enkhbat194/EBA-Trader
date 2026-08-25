# EBA Trader — TODO

This list is ordered by current project priority and must be reconciled with actual code before a session starts.

## NOW — M5 AI Strategy Factory / Order-Flow Ablation

- [x] Add historical Binance `aggTrades` downloader with deterministic paging/range capture.
- [x] Add missing-range detection and repair so sequence gaps are resolved before research-ready promotion.
- [x] Align footprint windows causally with candle windows and prove boundary semantics with tests.
- [x] Add allowlisted candle-only and order-flow backtest adapters that consume the exact same causally aligned feature dataset through the M4 worker path.
- [x] Prove with tests that a permissive order-flow gate matches the candle-only arm and that delta/CVD gates actually suppress candidate entries.
- [x] Add a read-only Research / AI Lab PWA dashboard backed by repo continuity plus optional M4 research-store counts.
- [x] Clarify Home carry metrics and add a read-only Fast Momentum server heartbeat with last/next scan visibility.
- [x] Add a deterministic ablation orchestrator that emits one deduplicated candle baseline plus paired bounded candle+delta/CVD experiments with identical EMA/cost/dataset assumptions.
- [ ] Add a CLI/workflow to materialize a real historical development feature dataset from candle CSV + verified order-flow/acquisition manifests.
- [ ] Run controlled development ablations on real historical BTCUSDT USD-M data under identical fees/slippage/gates.
- [ ] Compare survivors under the same development/robustness policy; do not promote from win rate alone.

## NOW — Production proof (parallel track)

- [x] Confirm Linode consumed GitHub `main` through state commit `050cd9be203a09aca95a152d7102fa280c397ee7` on 2026-08-26.
- [x] Verify public HTTPS PWA from an external iPhone at `https://eba-trader-172-236-150-62.sslip.io/`.
- [ ] Complete smoke-test Home / Chart / Scan / Positions / History / Research / Settings / trade detail against server truth. Home, Scan and Settings were observed working on 2026-08-26.
- [ ] Perform one real service/server restart and prove Fast Momentum `OPEN -> recovery -> MARK/CLOSE` persistence in production SQLite.
- [ ] Decide whether to persist/recover the older carry paper engine or retire it explicitly.

## NEXT

- [ ] Add stacked/diagonal footprint imbalance candidate features after raw trade-window integrity is proven.
- [ ] Add absorption/exhaustion candidates with causal definitions and tests.
- [ ] Add price/delta divergence candidates.
- [ ] Strengthen near-duplicate detection beyond exact/cosmetic threshold similarity if factory volume requires it.
- [ ] Add cheap-screen -> development-screen orchestration over generated candidate families.
- [ ] Persist survivor/ranking evidence without granting lifecycle authority to ranking.
- [ ] Reconcile lifecycle ordering before any automated frozen-OOS opening.

## LATER

- [ ] Reconstruct and validate limit-order-book depth/imbalance as a separate sequence-sensitive dataset.
- [ ] Build Verified Strategy Knowledge Base from strategies that pass the full validation path.
- [ ] Build forward-paper strategy factory.
- [ ] Build Binance Demo execution laboratory.
- [ ] Build market-regime selector / Market Brain only after enough independently verified strategies exist.
- [ ] Add portfolio selection, outcome attribution and drift monitoring.
- [ ] Define explicit shadow -> micro-live -> live promotion gates only after demo evidence exists.

## BLOCKED / GATED

- [ ] Automated frozen-OOS promotion.
  - Blocked by: current lifecycle code orders `OOS_VERIFIED` before `ROBUSTNESS_VERIFIED`, while desired validation policy wants robustness before opening frozen OOS.
  - Required action: deliberate lifecycle/policy redesign with migration/tests; no manual bypass.

- [ ] LOB/order-book strategy features.
  - Blocked by: no approved sequence-integrity reconstruction/cache contract yet.
  - Required action: implement depth snapshot/diff sequence validation separately from executed-trade footprint data.

- [ ] Real-money Binance orders.
  - Blocked by: intentionally locked safety policy and missing demo/shadow/micro-live evidence chain.
  - Required action: later explicit milestone only.

## DONE RECENTLY

- [x] M4 strategy-platform foundation, restart-safe experiment queue, evidence worker, development gates and robustness fan-out merged (#20-#24).
- [x] M5 order-flow/footprint foundation merged (#25).
- [x] Constrained M5 Strategy DSL, approved feature registry, deterministic candidate emission merged (#26).
- [x] Strategy-family templates, near-duplicate guard, cheap screening and survivor ranking merged (#27).
- [x] Historical Binance aggregate-trade normalization/cache, integrity gate and deterministic footprint windows merged (#28).
- [x] Repository continuity system installed with mandatory agent protocol and CI guard (#29).
- [x] Deterministic Binance aggregate-trade acquisition, missing-ID repair and causal candle alignment merged (#30).
- [x] Causal feature-dataset materialization plus allowlisted candle-only/order-flow ablation adapters merged (#31).
- [x] Research / AI Lab PWA dashboard merged (#32) with read-only research status and safety-lock visibility.
- [x] Carry label clarification and Fast Momentum heartbeat merged (#33).
