# EBA Trader — Decisions

This file records current architectural and research-policy decisions. Historical chat statements do not override accepted decisions unless code and this record are deliberately changed together.

## 2026-08-26 — Repository continuity is mandatory

### Decision
GitHub repository state is the shared continuity bridge between ChatGPT branches and AI sessions. Every session reads continuity files and actual code before work, then writes state/handoff back after meaningful work.

### Reason
Sibling chats do not exchange post-branch messages automatically. Git provides durable, inspectable, versioned shared memory.

### Consequences
- `AGENTS.md`, `PROJECT_STATE.md`, `ARCHITECTURE.md`, `DECISIONS.md`, `TODO.md`, `CHANGELOG.md`, and `SESSION_HANDOFF.md` are maintained as a set.
- CI checks that the continuity contract exists and contains no bootstrap-template placeholders.
- Code changes without a current handoff are considered incomplete session hygiene.

### Status
Accepted.

## 2026-08-26 — GitHub main + Linode is the canonical runtime path

### Decision
GitHub `main` is the code source of truth. Akamai/Linode Nanode (Singapore 2, Ubuntu 24.04 LTS) is the sole active backend/runtime target. Replit and Render are deprecated for EBA Trader backend work.

### Reason
The project already has systemd services, persistent SQLite state, update/rollback scripts, and runtime health checks on the Linode path. Parallel backends create divergence and continuity failures.

### Consequences
New backend/runtime work targets Linode. Replit/Render notes are historical only.

### Status
Accepted.

## 2026-08-26 — Runtime state and research state remain separate

### Decision
Runtime position/trade state remains in `TradeLedger` / `/var/lib/eba-trader/eba_trader.db`. Research strategy versions, experiments, evidence and lifecycle metadata remain in the M4 research control plane and must not mutate runtime position state.

### Reason
Mass research and experimental lifecycle operations must not corrupt persistent paper/live runtime state.

### Status
Accepted.

## 2026-08-26 — Real-money execution remains locked

### Decision
No current M5 work enables real Binance order submission. Deterministic risk has veto authority and future execution promotion requires explicit evidence and a separately validated milestone.

### Reason
Backtest/research success is not execution safety proof.

### Status
Accepted.

## 2026-08-26 — Strategy lifecycle evidence is immutable

### Decision
Strategy specifications are immutable per version, experiment evidence is content-addressed/verified, and lifecycle promotion requires evidence. Generic research workers cannot silently skip gates.

### Reason
The research platform must prevent retrospective mutation, data leakage and untracked promotion.

### Status
Accepted.

## 2026-08-26 — M5 AI Strategy Factory uses constrained DSL, not arbitrary code

### Decision
AI-generated hypotheses are constrained structured data validated against an approved feature registry and bounded parameter families. Arbitrary generated production Python/expression execution is not an accepted generation path.

### Reason
This preserves determinism, auditability, deduplication and control over the M4 experiment surface.

### Related implementation
- `src/eba_trader/m5_hypothesis.py`
- `src/eba_trader/m5_features.py`
- `src/eba_trader/m5_factory.py`
- `src/eba_trader/m5_emitter.py`

### Status
Accepted.

## 2026-08-26 — Footprint/order flow is a research feature family, not assumed edge

### Decision
Executed-trade footprint features (buy/sell volume, delta, delta ratio, CVD, POC) are candidate features that must prove incremental value against candle-only baselines. They are derived from raw executed events, never chart-image interpretation. Resting LOB liquidity is a separate future dataset.

### Reason
Footprint can add microstructure information but does not automatically identify institutional/hidden orders or guarantee improved win rate.

### Related implementation
- `src/eba_trader/orderflow.py`
- `src/eba_trader/orderflow_dataset.py`
- `src/eba_trader/footprint_dataset.py`
- `docs/M5_ORDER_FLOW_FOUNDATION.md`
- `docs/M5_ORDER_FLOW_DATASET.md`

### Status
Experimental feature family; architecture decision accepted.

## 2026-08-26 — Gapped historical order-flow data fails closed

### Decision
Historical Binance aggregate-trade datasets with duplicate/conflicting IDs, backward timestamps, integrity hash mismatch, or unresolved sequence gaps are not research/backtest-ready.

### Reason
Missing microstructure events can materially distort delta/footprint features and invalidate comparisons.

### Status
Accepted.

## 2026-08-26 — Development ranking cannot unlock frozen OOS

### Decision
Cheap screening and survivor ranking are triage only. A development win-rate/profitability improvement is insufficient to open frozen OOS, paper, demo, shadow or live stages.

### Reason
Selection bias and overfitting must remain separated from final validation.

### Status
Accepted.

## 2026-08-26 — Lifecycle ordering mismatch must be reconciled before automated frozen OOS

### Decision
Do not manually bypass the current code path `GENERATED -> BACKTESTED -> OOS_VERIFIED -> ROBUSTNESS_VERIFIED` even though the desired research process conceptually wants robustness before opening frozen OOS. M5/M6 must resolve the model explicitly before frozen-OOS orchestration.

### Related implementation
`src/eba_trader/lifecycle.py`

### Status
Open architectural issue; current lifecycle remains authoritative until changed deliberately.

## 2026-08-26 — Linode auto-deploy can self-heal HTTPS without making CA/DNS part of rollback

### Decision
Runtime deploy success is gated by local systemd/API health. Public HTTPS bootstrap may retry independently; temporary DNS/CA failure does not roll back an otherwise healthy runtime deployment.

### Related implementation
`scripts/update_linode_runtime.sh`

### Status
Accepted.

## 2026-08-26 — Order-flow acquisition is venue-specific and causal

### Decision
Historical order-flow acquisition records the exact Binance venue and request/range provenance. USD-M futures is the default acquisition venue for the current BTCUSDT perpetual research target; Spot remains an explicit alternative dataset rather than being silently mixed with futures flow.

Closed footprint features are aligned causally: a footprint covering `[t-step, t)` may be used by the candle opening at `t`. The current candle's still-forming `[t,t+step)` footprint is not injected into that same candle.

### Reason
Spot and perpetual futures have different executed order flow, so mixing them would contaminate the experiment. Explicit feature-availability time prevents future-event leakage in candle-vs-footprint ablations.

### Related implementation
- `src/eba_trader/orderflow_acquisition.py`
- `src/eba_trader/orderflow_alignment.py`

### Status
Accepted in PR #30.

## 2026-08-26 — Order-flow ablations must use the same aligned dataset and execution assumptions

### Decision
The candle-only arm and candle+order-flow arm of an M5 ablation must consume the exact same causally aligned feature dataset. The candle-only arm ignores the order-flow columns; the order-flow arm may only reject an otherwise valid EMA crossover entry using allowlisted, already-available footprint gates. EMA exits, next-bar execution, fees and slippage remain identical between arms.

The order-flow adapter must name at least one actual order-flow threshold (`delta_ratio_threshold` and/or `cvd_threshold`) or fail closed. A permissive threshold must reproduce the candle-only metrics exactly on the same dataset.

### Reason
Using different time ranges, candle files, execution logic or cost assumptions would confound the comparison. Requiring a real feature gate prevents an adapter labelled “order flow” from silently behaving as the candle baseline.

### Related implementation
- `src/eba_trader/orderflow_feature_dataset.py`
- `src/eba_trader/backtest.py`
- `src/eba_trader/backtest_adapter.py`
- `tests/test_orderflow_backtest_adapter.py`

### Status
Accepted in PR #31.

## 2026-08-26 — Research / AI Lab is read-only observability

### Decision
The PWA Research / AI Lab may display repository-continuity state and read-only M4 research-store summaries, but it has no mutation, lifecycle-promotion, risk, OOS-unlock or execution authority.

The web runtime may operate without a local M4 research database. In that case the UI must explicitly report that the local research DB is absent while still showing the repo-backed M5 frontier and safety locks.

### Reason
The user needs phone-first visibility into ongoing research without turning the dashboard into an unsafe control plane or coupling the Linode paper runtime to research-worker persistence.

### Related implementation
- `src/eba_trader/research_dashboard.py`
- `src/eba_trader/web_server_v2.py`
- `web/research_ui.js`
- `web/research_ui.css`

### Status
Accepted in PR #32.

## 2026-08-26 — M5 ablation orchestration uses one deterministic control plus bounded treatments

### Decision
A development order-flow ablation emits one deduplicated candle-only baseline experiment and a bounded set of deterministic order-flow treatment experiments. Every treatment maps to the same control and shares the exact dataset identity, symbol/time window, EMA parameters, initial capital, fees, slippage and trade-start semantics. Only allowlisted delta-ratio/CVD gate parameters differ.

Treatment fan-out is capped at 64, duplicate/empty/non-finite gates fail closed, and gate input order cannot change batch identity. The orchestration stage is fixed to `m5_orderflow_ablation_dev`; there is no frozen-OOS switch or lifecycle-promotion authority in this component.

### Reason
Re-running an identical baseline for every threshold wastes research capacity, while allowing uncontrolled configuration differences would invalidate causal comparison. A deterministic one-control-to-many-treatment mapping preserves comparability, deduplication and auditability.

### Related implementation
- `src/eba_trader/m5_ablation.py`
- `tests/test_m5_ablation.py`
- `src/eba_trader/research_queue.py`
- `src/eba_trader/research_worker.py`

### Status
Accepted and merged in PR #34.

## 2026-08-26 — Real M5 BTCUSDT ablations require venue-matched USD-M candles and order flow

### Decision
The real BTCUSDT perpetual development workflow must use Binance USD-M futures candles together with Binance USD-M futures aggregate trades. A Spot candle dataset must not be paired with futures order flow. Candle acquisition must record endpoint/request provenance, exact interval coverage, immutable CSV hash and venue; the resulting feature workflow must emit an immutable content-linked manifest and an M4-safe dataset reference.

### Reason
Spot and perpetual futures prices/order flow can diverge. Mixing venues creates an uncontrolled confounder that could make the order-flow arm appear better or worse for reasons unrelated to the tested feature. A venue-matched, content-addressed pipeline keeps the ablation auditable and reproducible.

### Related implementation
- `src/eba_trader/candle_acquisition.py`
- `src/eba_trader/m5_dataset_workflow.py`
- `src/eba_trader/orderflow_acquisition.py`
- `src/eba_trader/orderflow_feature_dataset.py`
- `tests/test_m5_dataset_workflow.py`

### Status
Accepted and merged in PR #35.

## 2026-08-26 — Binance Demo credentials persist only in an encrypted server vault

### Decision
The phone PWA may accept a Binance **Demo** API key/secret once and send it to the Linode backend for test-before-save encrypted persistence. The secret is never returned to browser JavaScript, never written to browser persistent storage, never committed to Git, and never accepted for live/non-Binance use in this milestone.

The Fernet master key is stored separately at `/etc/eba-trader/demo-credential.key` and must not be implicitly rotated during deploys. The encrypted credential blob lives under `/var/lib/eba-trader/credentials/`.

### Reason
The user needs no-paste reconnect across app/server restarts without weakening secret handling or coupling credentials to the Git checkout.

### Related implementation
- `src/eba_trader/credential_vault.py`
- web/server Demo connection handlers
- `scripts/install_linode_runtime.sh`
- `scripts/update_linode_runtime.sh`

### Status
Accepted and merged in PR #36. Real production save/reconnect verification remains pending.

## 2026-08-27 — Linode deployment recovery is fail-closed and stays outside PWA authority

### Decision
A stuck Linode deployment is repaired with a root-side helper that refuses dirty checkouts, downloads the latest canonical deployment script, records deployment diagnostics, and restores the timer. The PWA/web API does **not** receive systemd or deployment authority.

Automatic deployments leave persistent diagnostics under `/var/lib/eba-trader/deploy-state` and continue to enforce exact `origin/main`, health checks and rollback.

### Reason
The old server could become stranded on a stale build while the phone PWA could only refresh its cache. Giving the browser system-level deployment authority would create an unnecessary security boundary violation.

### Related implementation
- `scripts/repair_linode_auto_update.sh`
- `scripts/update_linode_runtime.sh`
- auto-update systemd units/wrapper

### Status
Accepted in PR #37 and production-verified.

## 2026-08-27 — High-frequency market events are data, not normal INFO diagnostics

### Decision
`eba-binance-data` must keep its Binance instrument/quote/trade/bar subscriptions active, but it must not emit every raw `QuoteTick`/`TradeTick` into INFO service logs. Per-tick `DataTester` logging stays disabled and the systemd unit carries a burst limit as defense in depth.

Operational logs are for lifecycle/health/errors and bounded diagnostics. Canonical research datasets must be produced by the explicit acquisition/materialization pipelines, not reconstructed from syslog/journal output.

### Reason
On the production Nanode, per-tick INFO logging grew `/var/log/syslog` to roughly 15 GB and journald to roughly 2.5 GB, consuming about 90% of the 25 GB disk without adding valid research evidence. Disabling diagnostic spam does not remove market-data subscriptions.

### Related implementation
- `src/eba_trader/binance_probe.py`
- `deploy/systemd/eba-binance-data.service`
- log-flood regression tests

### Status
Accepted in PR #38 and production-verified. Old oversized logs were reclaimed manually.

## 2026-08-27 — Production log retention must be bounded and reproducible

### Decision
The production server currently uses a journald policy equivalent to `SystemMaxUse=250M`, `SystemKeepFree=1G`, and `MaxRetentionSec=7day`. This manual production fix is **not yet sufficient**: repository install/update provisioning must create the bounded policy so rebuilds/new servers inherit it.

### Reason
A manual-only server setting is a continuity/deployment gap even if the current server is healthy.

### Status
Accepted operational policy; repository provisioning is the immediate pending task.

## 2026-08-27 — Long-running Linode research state belongs outside the Git checkout

### Decision
Before real M5 ablation runs, long-running research DB/data/evidence on Linode should move to a persistent namespace under `/var/lib/eba-trader/research/...`. It must remain logically and physically separate from runtime `TradeLedger` state.

Development defaults under `artifacts/` may remain useful locally, but production research state must not dirty `/opt/Eba-Trader` and block fail-closed auto-deploy.

### Reason
The deployment script correctly refuses a dirty runtime checkout. Writing research artifacts inside the repository would eventually turn valid research work into an auto-update blocker.

### Status
Accepted direction; implementation pending in the `m5-real-ablation-cli` track.
