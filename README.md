# EBA Trader

EBA Trader is a research-first autonomous trading system with deterministic risk control, persistent paper/runtime state, and an evidence-gated AI Strategy Factory.

## Source of truth

- Code: GitHub `main`
- Runtime target: Akamai/Linode Nanode 1 GB, Singapore 2, Ubuntu 24.04 LTS
- Runtime state: SQLite at `/var/lib/eba-trader/eba_trader.db`
- Research state/evidence: separate M4/M5 research control plane
- Replit and Render: deprecated backend/runtime paths

For cross-chat/AI continuity, every coding session must start with `AGENTS.md` and the repository continuity files. See `docs/CONTINUITY_PROTOCOL.md`.

## Active runtime architecture

Canonical services:

- `eba-binance-data.service` — Binance/NautilusTrader market data
- `eba-runtime-api.service` — local API at `127.0.0.1:8765`
- `eba-web.service` — PWA/web at `127.0.0.1:8000`
- `eba-auto-update.timer` — checks/deploys GitHub `main`

`scripts/update_linode_runtime.sh` deploys exact `origin/main`, refuses a dirty runtime checkout, checks service/API health and rolls back runtime failures. Public HTTPS bootstrap is implemented and retried independently from the runtime rollback boundary.

## Research platform status

### M4 — complete

M4 provides:

- immutable strategy versions;
- deterministic experiment IDs;
- restart-safe experiment queue/worker leases;
- immutable evidence/provenance;
- declarative development gates;
- bounded robustness fan-out and aggregate verdicts;
- evidence-required lifecycle transitions.

### M5 — in progress

Current M5 foundation includes:

- constrained strategy-hypothesis DSL;
- approved feature registry;
- bounded deterministic parameter families;
- duplicate/near-duplicate filtering;
- cheap screening and survivor ranking;
- M5 candidate emission into the M4 research platform;
- executed-trade order-flow/footprint features;
- historical Binance aggregate-trade normalization/cache and integrity checks;
- deterministic causal footprint windows.

Enabled footprint features currently include buy/sell volume, delta, delta ratio, CVD and POC. Stacked imbalance, absorption, exhaustion and LOB depth imbalance remain future/disabled features.

## Current direction

The immediate M5 task is to build historical Binance aggregate-trade acquisition/range repair, align footprint and candles causally, connect approved order-flow features to an allowlisted M4 backtest adapter, then run controlled candle-only vs candle+order-flow ablations under identical fees/slippage and gates.

Footprint is treated as an experimental feature family, not an assumed edge.

## What still needs proof

Repository code/CI does **not** by itself prove:

- latest `main` is currently deployed on Linode;
- public HTTPS works from an external phone/browser at this moment;
- a real service/server restart preserved an active Fast Momentum paper position through recovery and later MARK/CLOSE;
- the older carry paper engine is restart-safe or explicitly retired.

These remain external production-proof tasks.

## Safety rules

- API secrets never go into Git.
- Withdrawal permission is never required.
- Real Binance orders remain locked.
- Deterministic risk controls can veto every trade.
- Runtime state belongs on Linode/SQLite, not browser RAM.
- Strategy versions/evidence are immutable.
- Generic research workers cannot silently open frozen OOS or execution.
- Gapped/incomplete order-flow datasets are not backtest-ready.
- Development ranking/win rate is not promotion authority.

## Start here

For implementation continuity:

1. `AGENTS.md`
2. `PROJECT_STATE.md`
3. `ARCHITECTURE.md`
4. `DECISIONS.md`
5. `TODO.md`
6. `SESSION_HANDOFF.md`

For deployment: `docs/LINODE_RUNTIME.md` and `docs/DEPLOYMENT_CHECKLIST.md`.

For research policy: `BACKTEST_PROTOCOL.md`, `STRATEGY_SPEC.md`, and current M4/M5 documents under `docs/`.
