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
- Local runtime API: `127.0.0.1:8765`

Replit and Render.com are not active backend/runtime targets. The old Render-backed PWA/dashboard is transitional only until its frontend is migrated to Linode.

## What works now

- Binance public live market-data connection on Linode
- restartable systemd market-data service
- persistent SQLite trade ledger implementation
- local runtime API for health, positions and events
- historical research/backtest/evidence tooling
- deterministic risk and `NO_TRADE` foundations

## What is not complete yet

- paper OPEN / UPDATE / CLOSE events are not yet fully connected to the persistent ledger
- startup recovery of active paper positions is not complete
- PWA is not yet connected to the Linode API through authenticated HTTPS
- completed trade/history/detail API still needs expansion
- real Binance order execution is not enabled

## Next runtime direction

The next separate strategy target is Fast Momentum / Micro Profit paper trading for BTCUSDT perpetual futures simulation using 1m/5m inputs, both LONG and SHORT setups, visible TP/SL/indicators, and leverage tiers tested only in paper mode first.

Historical Spot Trend research remains preserved under `docs/` as evidence. It should not be confused with the active runtime migration plan.

## Safety rules

- API secrets never go into Git.
- Withdrawal permission is never required.
- Real orders remain locked until the execution path is separately validated.
- Deterministic risk controls can veto every trade.
- Runtime state belongs on Linode/SQLite, not in browser RAM.

See `PROJECT_STATE.md` for the authoritative continuation state and `docs/LINODE_RUNTIME.md` for deployment details.
