# EBA Trader — Changelog

## Unreleased

### Added
- Repository-backed cross-chat/AI continuity system (`AGENTS.md`, decisions, TODO, handoff, continuity protocol, CI guard).
- M5 constrained strategy-hypothesis DSL, approved feature registry and deterministic M4 candidate emission.
- M5 bounded strategy-family templates, similarity guard, cheap screening and survivor ranking.
- Historical Binance aggregate-trade normalization/cache with content hashes, sequence integrity and deterministic footprint-window materialization.
- Deterministic Binance Spot/USD-M aggregate-trade acquisition with time bootstrap, ID pagination, missing-ID repair and immutable request/range provenance.
- Causal closed-footprint to candle alignment that exposes a footprint only at/after its end timestamp.

### Changed
- Repository documentation is reconciled so GitHub `main` + Linode is the single canonical runtime path.
- M5 treats footprint/order-flow as an experimentally validated feature family rather than an assumed trading edge.
- USD-M futures is the default order-flow acquisition venue for the current BTCUSDT perpetual research target; Spot is an explicit alternate dataset.

### Safety / research controls
- Arbitrary AI-generated production code is not an approved M5 strategy-generation path.
- Incomplete/gapped order-flow datasets are not research-ready.
- Cheap-screen/survivor ranking does not open frozen OOS or execution stages.
- Same-candle still-forming footprint data is not injected into candle decisions.
- Real-money Binance order submission remains locked.

---

## 2026-08-26 — M5 order-flow and strategy-factory foundation

### Added
- PR #25: executed-trade order-flow/footprint foundation.
- PR #26: constrained Strategy DSL and approved feature registry.
- PR #27: family templates, near-duplicate guard, cheap screening and ranking.
- PR #28: historical order-flow dataset integrity and footprint windows.
- PR #30: venue-aware aggregate-trade acquisition, gap repair and causal candle alignment.

### Validation
- Relevant PR CI passed full regression, Ruff, deployment/shell checks, continuity guard and Linode runtime checks before merge where applicable.
