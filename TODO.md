# EBA Trader — TODO

This list is ordered by current project priority and must be reconciled with actual code/Git before a session starts.

## NOW — Production hardening / continuity closure

- [x] Recover a stuck Linode auto-update path and add persistent deployment diagnostics (#37, merge `9b265a4a880c380d66943e3964586be12ebfb9da`).
- [x] Production-verify the one-command repair path and restore `eba-auto-update.timer` to active/waiting.
- [x] Identify the ~18 GB `/var/log` growth root cause as per-tick `eba-binance-data` INFO logging, not research/trade data.
- [x] Disable Nautilus `DataTester` per-tick logging while preserving quote/trade/bar subscriptions; add service burst limiting and regression coverage (#38, merge `2ef162bf975b8a1ace1adb86af269976d3c7c578`).
- [x] Production-verify `eba-binance-data.service` remains active while post-deploy `QuoteTick`/`TradeTick` flood is absent.
- [x] Reclaim old oversized logs manually; disk fell from ~90.1% used to 21% (`4.8G` used / `19G` available), `/var/log` to ~`162M`.
- [x] Apply a production-local journald cap (`SystemMaxUse=250M`, `SystemKeepFree=1G`, `MaxRetentionSec=7day`).
- [ ] **Codify the journald retention/free-space drop-in in repo install/update provisioning** so rebuilds/new servers do not depend on manual console state.
- [ ] Verify standalone Chart / Positions / Research screens against server truth.
- [ ] Enter the Binance Demo key/secret once in the PWA and verify encrypted save + subsequent no-paste auto-connect on the real Linode runtime.
- [ ] Perform one real service/server restart and prove Fast Momentum `OPEN -> recovery -> MARK/CLOSE` persistence in production SQLite.
- [ ] Decide whether to persist/recover the older carry paper engine or retire it explicitly.

## NOW — M5 AI Strategy Factory / Order-Flow Ablation

- [x] Add historical Binance `aggTrades` downloader with deterministic paging/range capture.
- [x] Add missing-range detection and repair so sequence gaps are resolved before research-ready promotion.
- [x] Align footprint windows causally with candle windows and prove boundary semantics with tests.
- [x] Add allowlisted candle-only and order-flow backtest adapters that consume the exact same causally aligned feature dataset through the M4 worker path.
- [x] Prove with tests that a permissive order-flow gate matches the candle-only arm and that delta/CVD gates actually suppress candidate entries.
- [x] Add a read-only Research / AI Lab PWA dashboard backed by repo continuity plus optional M4 research-store counts.
- [x] Clarify Home carry metrics and add a read-only Fast Momentum server heartbeat with last/next scan visibility.
- [x] Add a deterministic ablation orchestrator that emits one deduplicated candle baseline plus paired bounded candle+delta/CVD experiments with identical EMA/cost/dataset assumptions.
- [x] Add a venue-verified USD-M CLI/workflow that acquires exact futures candles plus verified order flow and materializes a causal development feature dataset (`eba-build-orderflow-features`); merged in #35 at `178611f535e95d61747a726b73cf7346f94358e4`.
- [ ] Resume `m5-real-ablation-cli` from latest `main`; do not continue from its older pre-#37/#38 base without reconciliation.
- [ ] Move long-running Linode research DB/data/evidence outside the Git checkout, target `/var/lib/eba-trader/research/...`, while keeping runtime `TradeLedger` separate.
- [ ] Add deterministic real-ablation execution CLI/workflow: verified feature manifest/`dataset_ref` -> #34 ablation batch -> M4 research store/queue -> machine-readable experiment IDs.
- [ ] Run the real BTCUSDT USD-M development feature build on Linode for an authorized development-only window outside frozen OOS.
- [ ] Run controlled development ablations on the resulting real dataset under identical fees/slippage/gates.
- [ ] Compare survivors under the same development/robustness policy; do not promote from win rate alone.

## NEXT

- [ ] Add stacked/diagonal footprint imbalance candidate features after raw trade-window integrity is proven by the real development run.
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
- [x] Research / AI Lab PWA dashboard merged (#32).
- [x] Carry label clarification and Fast Momentum heartbeat merged (#33).
- [x] Deterministic one-control-to-many-treatment ablation orchestration merged (#34).
- [x] Venue-matched real USD-M candle + order-flow feature-dataset workflow merged (#35).
- [x] Encrypted one-time Binance Demo credential persistence merged (#36, `06248eb9c901b44ca0a91ccd96bd15d23e156c9a`).
- [x] Linode auto-update recovery/diagnostics merged and production-verified (#37).
- [x] Binance market-data log-flood root-cause fix merged and production-verified (#38).
