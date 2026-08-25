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
