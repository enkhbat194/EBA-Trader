# EBA Trader — TODO

This list is ordered by current project priority and must be reconciled with actual code before a session starts.

## NOW — M5 AI Strategy Factory / Order-Flow Ablation

- [ ] Add historical Binance `aggTrades` downloader with deterministic paging/range capture.
- [ ] Add missing-range detection and repair so sequence gaps are resolved before research-ready promotion.
- [ ] Align footprint windows causally with candle windows and prove boundary semantics with tests.
- [ ] Add an allowlisted order-flow backtest adapter that consumes approved footprint features through the M4 worker path.
- [ ] Define and run controlled ablation families:
  - candle-only baseline;
  - baseline + delta/CVD;
  - later approved footprint imbalance/absorption/exhaustion variants.
- [ ] Compare survivors under the same fees/slippage/development gates; do not promote from win rate alone.

## NOW — Production proof (parallel track)

- [ ] Confirm the Linode runtime has consumed the latest GitHub `main` after current merges.
- [ ] Verify the public HTTPS PWA from an external phone/browser.
- [ ] Smoke-test Home / Chart / Scan / Positions / History / Settings / trade detail against server truth.
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
- [x] Repository continuity system installed with mandatory agent protocol and CI guard (current continuity milestone).
