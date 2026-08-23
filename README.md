# EBA Trader

EBA Trader is a research-first trading system with deterministic risk control and a persistent 24/7 Linux runtime.

## Active architecture

- Source of truth: GitHub `main`
- Runtime server: Akamai/Linode Nanode 1 GB, Singapore 2
- OS: Ubuntu 24.04 LTS
- Market data: Binance via NautilusTrader
- Persistent state: SQLite at `/var/lib/eba-trader/eba_trader.db`
- Services:
  - `eba-binance-data.service`
  - `eba-runtime-api.service`
  - `eba-web.service`
- Local runtime API: `127.0.0.1:8765`
- Local PWA/web service: `127.0.0.1:8000` until authenticated HTTPS is added

Replit and Render.com are not active backend/runtime targets. The active PWA/dashboard source now lives in `main` under `web/` and is served by the Linode web runtime.

## What works now

- Binance public live market-data connection on Linode
- restartable systemd market-data/runtime/web service definitions
- persistent SQLite trade ledger implementation
- local runtime API for health, positions and events
- mobile PWA/dashboard source in `main`
- Fast Momentum LONG/SHORT paper scanner
- SQLite persistence and restart recovery for Fast Momentum paper positions/history
- trade-detail chart UI with entry/current-or-exit/TP/SL and indicators
- historical research/backtest/evidence tooling
- deterministic risk and `NO_TRADE` foundations

## What is not complete yet

- authenticated HTTPS reverse proxy/public PWA endpoint on Linode
- final phone smoke test against the Linode-served PWA
- the older carry paper engine is still not fully restart-safe/persisted like Fast Momentum
- GitHub `main` -> Linode automatic deployment with health-check/rollback is not complete
- real Binance order execution is not enabled

## Current runtime direction

Fast Momentum / Micro Profit paper trading targets BTCUSDT perpetual futures simulation using 1m/5m inputs, both LONG and SHORT setups, visible TP/SL/indicators, and risk-selected leverage tiers tested only in paper mode first.

Historical Spot Trend research remains preserved under `docs/` as evidence. It is not an active deployment path.

## Safety rules

- API secrets never go into Git.
- Withdrawal permission is never required.
- Real orders remain locked until the execution path is separately validated.
- Deterministic risk controls can veto every trade.
- Runtime state belongs on Linode/SQLite, not in browser RAM.

See `PROJECT_STATE.md` for the authoritative continuation state and `docs/LINODE_RUNTIME.md` for deployment details.
