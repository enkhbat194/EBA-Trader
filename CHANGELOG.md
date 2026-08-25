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
- Read-only Research / AI Lab PWA tab and `/api/research/status` endpoint showing the active M5 frontier, optional M4 research-store counts, ablation readiness and safety locks.

### Changed
- Repository documentation is reconciled so GitHub `main` + Linode is the single canonical runtime path.
- M5 treats footprint/order-flow as an experimentally validated feature family rather than an assumed trading edge.
- USD-M futures is the default order-flow acquisition venue for the current BTCUSDT perpetual research target; Spot is an explicit alternate dataset.
- EMA baseline backtesting now supports an optional causal entry filter while preserving historical behavior when no filter is supplied.
- Annualized return calculation is overflow-safe for very short/high-return synthetic windows; non-finite annualized/profit-factor values are serialized as `null` plus explicit flags in evidence metrics.
- PWA cache advances to `eba-trader-ui-v13` for the Research / AI Lab assets.

### Safety / research controls
- Arbitrary AI-generated production code is not an approved M5 strategy-generation path.
- Incomplete/gapped order-flow datasets are not research-ready.
- Cheap-screen/survivor ranking does not open frozen OOS or execution stages.
- Same-candle still-forming footprint data is not injected into candle decisions.
- Order-flow ablation arms use the same aligned dataset and identical EMA exit/cost assumptions.
- An order-flow adapter without an actual delta/CVD gate fails closed.
- Research / AI Lab is observational only and has no lifecycle/risk/execution authority.
- Real-money Binance order submission remains locked.

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

### Validation
- Relevant PR CI passed full regression, Ruff, deployment/shell checks, continuity guard and Linode runtime checks before merge where applicable.
