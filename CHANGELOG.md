# EBA Trader — Changelog

## Unreleased

### Added
- Repository-backed cross-chat/AI continuity system (`AGENTS.md`, decisions, TODO, handoff, continuity protocol, CI guard).
- M5 constrained strategy-hypothesis DSL, approved feature registry and deterministic M4 candidate emission.
- M5 bounded strategy-family templates, similarity guard, cheap screening and survivor ranking.
- Historical Binance aggregate-trade normalization/cache with content hashes, sequence integrity and deterministic footprint-window materialization.
- Deterministic Binance Spot/USD-M aggregate-trade acquisition with time bootstrap, ID pagination, missing-ID repair and immutable request/range provenance.
- Causal closed-footprint to candle alignment that exposes a footprint only at/after its end timestamp.
- Provenance-linked candle + prior-closed-footprint feature dataset materialization.
- Allowlisted `ema_feature_baseline_v1` and `ema_orderflow_v1` M4 backtest adapters for controlled same-dataset ablations.
- Deterministic M5 order-flow ablation orchestrator: one deduplicated candle control plus bounded delta/CVD treatment variants with a deterministic pair/batch map.
- Venue-aware Binance candle acquisition with explicit Spot/USD-M endpoints, request provenance, immutable CSV/manifest integrity and exact interval-window validation.
- One-command `eba-build-orderflow-features` workflow for verified BTCUSDT USD-M development datasets, including prior-window aggregate trades, repair, causal alignment and an M4-safe relative `dataset_ref`.
- Encrypted Binance Demo credential vault for one-time in-app key/secret entry, masked status, automatic reconnect, explicit replace/delete and restart persistence.
- Read-only Research / AI Lab PWA tab and `/api/research/status` endpoint showing the active M5 frontier, optional M4 research-store counts, ablation readiness and safety locks.
- Read-only Fast Momentum server heartbeat on Home using `/api/runner/status`, with LIVE/STALE/OFF state, last scan, next expected scan and interval.
- Fail-closed Linode auto-update repair helper and persistent deployment diagnostics under `/var/lib/eba-trader/deploy-state` (#37).
- Binance data-service logging regression protection and systemd burst limiting (#38).

### Changed
- Repository documentation is reconciled so GitHub `main` + Linode is the single canonical runtime path.
- M5 treats footprint/order-flow as an experimentally validated feature family rather than an assumed trading edge.
- The real M5 BTCUSDT perpetual workflow requires USD-M futures candles and USD-M futures executed order flow end to end; Spot candles are not accepted for that comparison.
- EMA baseline backtesting supports an optional causal entry filter while preserving historical behavior when no filter is supplied.
- Annualized return calculation is overflow-safe for very short/high-return synthetic windows; non-finite annualized/profit-factor values are serialized as `null` plus explicit flags in evidence metrics.
- M5 ablation treatment fan-out is capped at 64; duplicate/empty/non-finite gates fail closed and gate input order cannot change batch identity.
- Binance Demo credential persistence validates credentials before disk write, stores only authenticated ciphertext at rest and never returns the saved secret to browser JavaScript.
- Linode install and auto-update provision the Demo credential encryption key once and do not rotate it implicitly across deployments.
- Ambiguous Home labels are clarified: `Current opportunity` is carry-only and becomes `Carry opportunity`; expected net is likewise carry-specific.
- Credential-vault release advances to `0.12.2 / LINODE-M7` and PWA cache `eba-trader-ui-v15`.
- `eba-binance-data` no longer emits every quote/trade tick at INFO; subscriptions remain active while `DataTesterConfig(log_data=False)` prevents runaway diagnostic volume.
- Linode auto-update timer recovery is hardened and failures leave persistent diagnostics instead of silently disappearing.

### Operations
- Manual production evidence on 2026-08-26 confirmed public HTTPS PWA access from an external iPhone.
- Home, Scan and Settings were observed against server truth.
- Additional iPhone screenshots confirmed persisted Fast Paper History rows and trade-detail/chart rendering, including entry/exit, fees, exit reasons, strategy evidence and chart annotations.
- PR #37 recovery was exercised on the real Linode and restored a stuck server checkout from build `050cd9b` to current main; `eba-auto-update.timer` returned to active/waiting.
- Production disk investigation found `/var/log` near 18 GB because `/var/log/syslog` was about 15 GB and journald about 2.5 GB. The source was per-tick `eba-binance-data` INFO logging, not research/trade datasets.
- PR #38 merge `2ef162bf975b8a1ace1adb86af269976d3c7c578` was deployed and verified: the data service remained active and no post-deploy raw `QuoteTick`/`TradeTick` flood appeared.
- Old log volume was reclaimed manually; root filesystem usage fell from about 90.1% to 21% (`4.8G` used, `19G` free), and `/var/log` fell to about `162M`.
- Production journald currently has a manually-installed `SystemMaxUse=250M`, `SystemKeepFree=1G`, `MaxRetentionSec=7day` drop-in. Repository provisioning of this guard remains pending.
- Remaining production proof: standalone Chart / Positions / Research smoke, one real encrypted-key no-paste reconnect, plus an active-position restart/recovery sequence.

### Safety / research controls
- Arbitrary AI-generated production code is not an approved M5 strategy-generation path.
- Incomplete/gapped order-flow datasets are not research-ready.
- Cheap-screen/survivor ranking does not open frozen OOS or execution stages.
- Same-candle still-forming footprint data is not injected into candle decisions.
- Order-flow ablation arms use the same aligned dataset and identical EMA/capital/fee/slippage/trade-start assumptions.
- M5 ablation orchestration is fixed to development stage and has no OOS/lifecycle-promotion authority.
- The real M5 feature workflow is hard-gated to USD-M futures and still passes through the first-cycle frozen-OOS guard.
- The credential vault accepts Binance Demo only; live/non-Binance credentials are rejected.
- API secrets are not committed to Git and are not persisted in browser localStorage/sessionStorage.
- An order-flow adapter without an actual delta/CVD gate fails closed.
- Research / AI Lab and scanner heartbeat are observational only and have no lifecycle/risk/execution authority.
- High-frequency raw market ticks are not normal INFO diagnostic logs.
- Real-money Binance order submission remains locked.

---

## 2026-08-27 — Linode recovery and logging hardening

### Added / fixed
- PR #37: fail-closed auto-update repair and persistent deployment diagnostics; squash merge `9b265a4a880c380d66943e3964586be12ebfb9da`.
- PR #38: disable per-tick Binance probe logging while preserving market-data subscriptions, add service log burst cap and regression coverage; squash merge `2ef162bf975b8a1ace1adb86af269976d3c7c578`.

### Production verification
- Auto-update recovery helper succeeded on real Linode.
- Current PR #38 build deployed successfully.
- `eba-binance-data.service` remained active with no raw-tick flood after deployment.
- Disk/log cleanup recovered roughly 17 GB of space and restored healthy free capacity.

---

## 2026-08-26 — M5 order-flow and strategy-factory foundation

### Added
- PR #25: executed-trade order-flow/footprint foundation.
- PR #26: constrained Strategy DSL and approved feature registry.
- PR #27: family templates, near-duplicate guard, cheap screening and ranking.
- PR #28: historical order-flow dataset integrity and footprint windows.
- PR #30: venue-aware aggregate-trade acquisition, gap repair and causal candle alignment.
- PR #31: same-dataset candle-only/order-flow feature backtest adapters and ablation invariants.
- PR #32: phone-first Research / AI Lab status dashboard.
- PR #33: carry-label clarification and Fast Momentum server heartbeat observability; squash merge `2b62f056f438c38865694d2f0aa130480926e7b2`.
- PR #34: deterministic one-control-to-many-treatment order-flow ablation orchestration; squash merge `ee5fd3f16ed5ad88ca928ced0efdb5790cbf568d`.
- PR #35: verified USD-M candle + order-flow feature-dataset workflow; squash merge `178611f535e95d61747a726b73cf7346f94358e4`.
- PR #36: encrypted one-time Binance Demo credential persistence; squash merge `06248eb9c901b44ca0a91ccd96bd15d23e156c9a`.

### Validation
- PRs #29-#36 passed full regression, Ruff, deployment/shell checks, continuity guard and Linode runtime checks before merge.
- PR #37 recovery path was patch/shell validated and then production-exercised successfully.
- PR #38 passed its regression/runtime/continuity validation before merge and was subsequently production-verified.
