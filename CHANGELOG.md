# EBA Trader — Changelog

## Unreleased

### Added
- Repository-backed cross-chat/AI continuity system and CI guard.
- M5 constrained strategy-hypothesis DSL, approved feature registry, bounded family generation, similarity guard, cheap screening and survivor ranking.
- Historical Binance aggregate-trade acquisition/cache with venue provenance, missing-ID repair, sequence integrity and deterministic footprint windows.
- Causal candle + prior-closed-footprint feature-dataset materialization.
- Allowlisted candle-only and order-flow adapters for controlled same-dataset ablations.
- Deterministic M5 one-control-to-many-treatment order-flow ablation orchestration.
- Venue-aware verified BTCUSDT USD-M feature-dataset workflow.
- Encrypted Binance Demo credential vault, masked status, automatic reconnect and explicit replace/delete.
- Read-only Research / AI Lab dashboard and Fast Momentum server heartbeat.
- Persistent Linode deployment diagnostics, journald host protection and persistent M4/M5 research storage/worker automation (#37-#40).
- Lifecycle policy v2 with robustness-before-OOS transition order and legacy SQLite migration/freeze rules (#41).
- External exact-build public production smoke automation (#42).
- Sanitized production proof and passive natural Fast OPEN restart watcher (#43).
- Legacy carry active-entry retirement; Fast Momentum is the sole active production paper engine (#44).
- PR #45 candidate: bounded/idempotent first real BTCUSDT M5 development autorun, immutable candle-baseline vs Delta/CVD comparison report and sanitized autorun production-proof state.

### Changed
- GitHub `main` + Linode is canonical; Replit/Render backend paths are deprecated.
- Footprint/order-flow remains an experimental feature family, not assumed edge.
- BTCUSDT perpetual comparisons require USD-M candles and USD-M executed order flow end-to-end.
- Ablation arms share the same aligned dataset and execution assumptions; only allowlisted order-flow filters differ.
- Binance Demo credentials validate before encrypted write and never return the saved secret to browser JavaScript.
- Long-running research state lives under `/var/lib/eba-trader/research/...`, outside the Git checkout.
- Current lifecycle path is `GENERATED -> BACKTESTED -> ROBUSTNESS_VERIFIED -> OOS_VERIFIED -> ...`; direct current-policy `BACKTESTED -> OOS_VERIFIED` is forbidden.
- Legacy carry cannot open new production paper positions by default; compatibility/history code remains read-only/close-compatible.
- PR #45 development comparison output explicitly has no edge-claim or lifecycle-promotion authority.

### Operations
- Public HTTPS PWA access is production-active.
- PR #40 production recovery reduced runaway log usage and made journald/research runtime state repository-managed.
- A real Binance Demo credential is encrypted/saved on Linode.
- External runner proof for `a1425c5...` confirmed saved Demo no-paste autoconnect, Chart, Positions and Research after deployment restart.
- PR #44 merge `0df5f4d9a7ce054b1a2b65002b9329ba0c8143aa` reached production and passed exact-build production smoke, Demo reconnect, Chart, Positions, frozen-OOS lock and real-execution lock.
- Passive Fast restart watcher is installed but its market-dependent `OPEN -> restart -> same-position recovery -> MARK -> CLOSE` proof is not complete until a natural qualifying position occurs.
- PR #45 candidate schedules a small 2026-08-01 00:00Z-04:00Z USD-M development batch after deploy, bounded by 40% CPU, 700 MB memory and 45 minutes.

### Safety / research controls
- Arbitrary AI-generated production code is not an approved M5 strategy-generation path.
- Incomplete/gapped/tampered order-flow data is not research-ready.
- Same-candle still-forming footprint data is not injected into candle decisions.
- Development screening/ranking/ablation results do not open frozen OOS or execution.
- Persistent research workers are resource-bounded and have no exchange-order authority.
- Legacy post-OOS policy-v1 strategies are promotion-frozen until explicit retest/v2 re-entry.
- PR #45 comparison report records `developmentComparisonOnly=true`, `edgeClaimAllowed=false`, `promotionAuthority=false`, `frozenOosOpened=false`, and `liveExecutionAllowed=false`.
- API secrets are not committed to Git, browser persistent storage or chat.
- Real-money Binance order submission remains locked.

---

## 2026-08-27 — Production proof / carry retirement / real M5 autorun

### Implementation
- #42 added exact-build public HTTPS smoke verification.
- #43 added sanitized server production proof plus a passive Fast OPEN restart watcher that never manufactures a trade.
- #44 retired the browser/in-memory carry strategy from active production entry authority while preserving compatibility/history surfaces.
- #45 candidate adds an idempotent systemd-driven real BTCUSDT M5 development batch and immutable comparison artifact.

### Validation
- #44 passed full regression, Ruff, shell syntax, deployment contract, active Linode runtime and continuity checks before merge.
- Exact production build `0df5f4d9...` later passed external production smoke, Demo reconnect, Chart, Positions and both OOS/live locks.
- #45 pre-continuity head passed full regression, Ruff, shell syntax, deployment contract, active Linode runtime and continuity checks.
- No Delta/CVD edge claim exists until actual development evidence is produced and even then development comparison alone has no promotion authority.

---

## 2026-08-27 — Lifecycle policy v2 / robustness before frozen OOS

### Implementation
- PR #41 merged at `32a39c57cb9c86bd2b956ea670fa3031229d0efc`.
- Introduced lifecycle policy versioning in strategy persistence and lifecycle history.
- Current path is `GENERATED -> BACKTESTED -> ROBUSTNESS_VERIFIED -> OOS_VERIFIED -> ...`.
- Existing pre-OOS legacy rows can migrate safely to v2.
- Existing legacy rows already at OOS or later stay policy v1 and promotion-frozen until `RETEST_REQUIRED` plus explicit v2 re-entry.
- A passing immutable robustness verdict can promote only to `ROBUSTNESS_VERIFIED`; OOS is a separate evidence-bearing transition.

### Validation
- Legacy SQLite migration, direct-OOS-skip, failed-verdict and idempotent robustness-promotion regressions passed required CI before merge.

---

## 2026-08-27 — Persistent M5 research runtime / real-ablation package

- PR #40 merged at `8876bc22b59f236e8df038440aaa6116c5d1afdf`.
- Added reproducible journald protection, persistent research storage, bounded worker automation and verified real development ablation CLI/runner.
- `scripts/run_m5_real_ablation.sh` composes verified USD-M feature build, deterministic queue emission and immutable M4 evidence worker execution.

---

## 2026-08-27 — Linode recovery and logging hardening

- PR #37: fail-closed auto-update repair and persistent deployment diagnostics; merge `9b265a4a880c380d66943e3964586be12ebfb9da`.
- PR #38: disable per-tick Binance probe logging while preserving subscriptions, add service log burst cap and regression coverage; merge `2ef162bf975b8a1ace1adb86af269976d3c7c578`.
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
- PR #33: Fast Momentum heartbeat and carry-label clarification.
- PR #34: deterministic one-control-to-many-treatment ablation orchestration.
- PR #35: verified USD-M candle + order-flow feature-dataset workflow; merge `178611f535e95d61747a726b73cf7346f94358e4`.
- PR #36: encrypted one-time Binance Demo credential persistence; merge `06248eb9c901b44ca0a91ccd96bd15d23e156c9a`.
