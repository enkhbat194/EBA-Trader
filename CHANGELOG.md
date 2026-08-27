# EBA Trader — Changelog

## Unreleased

### Added
- Repository-backed cross-chat/AI continuity system and CI guard.
- M5 constrained strategy-hypothesis DSL, approved feature registry, bounded family generation, similarity guard, cheap screening and survivor ranking.
- Historical Binance aggregate-trade acquisition/cache with venue provenance, missing-ID repair, sequence integrity and deterministic footprint windows.
- Causal candle + prior-closed-footprint feature-dataset materialization.
- Allowlisted `ema_feature_baseline_v1` and `ema_orderflow_v1` adapters for controlled same-dataset ablations.
- Deterministic M5 one-control-to-many-treatment order-flow ablation orchestration.
- Venue-aware one-command `eba-build-orderflow-features` workflow for verified BTCUSDT USD-M development datasets.
- Encrypted Binance Demo credential vault for one-time in-app entry, masked status, automatic reconnect and explicit replace/delete.
- Read-only Research / AI Lab dashboard and Fast Momentum server heartbeat.
- Fail-closed Linode auto-update repair plus persistent deployment diagnostics (#37).
- Binance data-service raw-tick logging regression protection and systemd burst limiting (#38).
- PR #40: versioned journald host protection; persistent research DB/dataset/evidence paths; bounded research worker/timer; `eba-m5-real-ablation`; initial Delta/CVD gate set; one-command real development runner.
- PR #41 candidate: lifecycle policy v2 with explicit policy-version persistence, robustness-before-OOS transition order, legacy SQLite migration/freeze rules and passing-robustness promotion helper.

### Changed
- GitHub `main` + Linode is the canonical runtime path; Replit/Render backend paths are deprecated.
- Footprint/order-flow is treated as an experimental feature family, not assumed edge.
- Real BTCUSDT perpetual comparisons require USD-M futures candles and USD-M executed order flow end-to-end.
- M5 ablation arms share the exact aligned dataset and identical EMA/capital/fees/slippage/trade-start/exit assumptions; only allowlisted Delta/CVD entry filters differ.
- Binance Demo credentials validate before encrypted write and never return the saved secret to browser JavaScript.
- `eba-binance-data` no longer emits every market tick at INFO while subscriptions remain active.
- Long-running production research state lives under `/var/lib/eba-trader/research/...`, outside the Git checkout.
- Existing Linode environment files gain missing research defaults without replacing explicit operator values.
- Production journald limits are repository-provisioned rather than manual-only state.
- Lifecycle policy v2 changes current research promotion order from historical `BACKTESTED -> OOS_VERIFIED -> ROBUSTNESS_VERIFIED` to `BACKTESTED -> ROBUSTNESS_VERIFIED -> OOS_VERIFIED` without silently reinterpreting persisted legacy rows.

### Operations
- Public HTTPS PWA access from external iPhone was manually verified on 2026-08-26.
- Home / Scan / Settings, persisted Fast Paper History and trade detail/chart were observed against server truth.
- PR #37 recovery restored a stuck Linode auto-update path and active timer.
- Production investigation found `/var/log` near 18 GB because raw Binance ticks were logged at INFO; PR #38 removed the flood.
- Old logs were reclaimed manually; root filesystem usage fell from ~90.1% to ~21%, `/var/log` to ~162M.
- PR #40 merged at `8876bc22b59f236e8df038440aaa6116c5d1afdf`; the PWA now reports server build `8876bc2`, confirming deployment reached the active Linode runtime.
- A real Binance Demo credential has been entered through the PWA and the UI reports it encrypted/saved securely on Linode.
- Remaining production proof: direct #40 server-internal journald/research-worker verification, standalone Chart / Positions / Research smoke, Demo no-paste reconnect after restart, active Fast Momentum restart/recovery, and carry-engine disposition.

### Safety / research controls
- Arbitrary AI-generated production code is not an approved M5 strategy-generation path.
- Incomplete/gapped/tampered order-flow data is not research-ready.
- Same-candle still-forming footprint data is not injected into candle decisions.
- Development screening/ranking/ablation results do not open frozen OOS or execution.
- PR #40 real-ablation queueing re-verifies USD-M venue, dataset containment, feature SHA-256 and frozen first-cycle OOS non-overlap.
- The persistent research worker is resource-bounded and has no exchange-order authority.
- Policy v2 forbids `BACKTESTED -> OOS_VERIFIED`; a strategy must first pass robustness evidence and reach `ROBUSTNESS_VERIFIED`.
- Legacy post-OOS policy-v1 strategies are promotion-frozen and require `RETEST_REQUIRED` plus explicit v2 re-entry before fresh robustness/OOS validation.
- API secrets are not committed to Git, browser persistent storage or chat.
- Real-money Binance order submission remains locked.

---

## 2026-08-27 — Lifecycle policy v2 / robustness before frozen OOS

### Implementation
- Introduced lifecycle policy versioning in strategy persistence and lifecycle history.
- New/current path is `GENERATED -> BACKTESTED -> ROBUSTNESS_VERIFIED -> OOS_VERIFIED -> ...`.
- Existing pre-OOS legacy rows can migrate safely to v2.
- Existing legacy rows that already reached OOS or later stay policy v1 and promotion-frozen until `RETEST_REQUIRED` and explicit v2 re-entry.
- Robustness fan-out requires exact v2 `BACKTESTED` state.
- A passing immutable robustness verdict can promote only to `ROBUSTNESS_VERIFIED`; OOS remains a separate evidence-bearing transition.

### Validation
- Added legacy SQLite migration tests plus direct-OOS-skip, failed-verdict and idempotent robustness-promotion regression coverage.
- PR #41 pre-continuity head passed full Python regression, Ruff, shell syntax, deployment contract, Linode runtime checks and continuity guard.

---

## 2026-08-27 — Persistent M5 research runtime / real-ablation package

### Implementation
- PR #40 adds reproducible journald protection, persistent research storage, bounded research worker automation and the verified real development ablation execution surface.
- `scripts/run_m5_real_ablation.sh` composes verified USD-M feature build, deterministic queue emission and exact emitted job count through the immutable M4 evidence worker.

### Validation
- PR #40 passed the full Python regression suite, Ruff, shell syntax, deployment contract, Linode runtime checks and continuity guard before squash merge.
- No real BTCUSDT Delta/CVD edge claim exists until the first production development run completes and evidence is compared.

---

## 2026-08-27 — Linode recovery and logging hardening

- PR #37: fail-closed auto-update repair and persistent deployment diagnostics; merge `9b265a4a880c380d66943e3964586be12ebfb9da`.
- PR #38: disable per-tick Binance probe logging while preserving market-data subscriptions, add service log burst cap and regression coverage; merge `2ef162bf975b8a1ace1adb86af269976d3c7c578`.
- PR #39: reconcile canonical continuity through production recovery; merge `b37d43b450fa55f094cbe04d7d4066b58f15252a`.

---

## 2026-08-26 — M5 order-flow and strategy-factory foundation

- PR #25: executed-trade order-flow/footprint foundation.
- PR #26: constrained Strategy DSL and approved feature registry.
- PR #27: family templates, near-duplicate guard, cheap screening and ranking.
- PR #28: historical order-flow dataset integrity and footprint windows.
- PR #30: venue-aware aggregate-trade acquisition, gap repair and causal candle alignment.
- PR #31: same-dataset candle-only/order-flow adapters and ablation invariants.
- PR #32: phone-first Research / AI Lab dashboard.
- PR #33: carry-label clarification and Fast Momentum heartbeat.
- PR #34: deterministic one-control-to-many-treatment ablation orchestration.
- PR #35: verified USD-M candle + order-flow feature-dataset workflow; merge `178611f535e95d61747a726b73cf7346f94358e4`.
- PR #36: encrypted one-time Binance Demo credential persistence; merge `06248eb9c901b44ca0a91ccd96bd15d23e156c9a`.
