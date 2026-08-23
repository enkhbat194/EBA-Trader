# EBA Trader Architecture

## 1. System goal

EBA Trader is a research-first trading system with a persistent 24/7 runtime. The runtime must keep market data, paper positions, trade history and risk state independent of whether the browser/PWA is open.

## 2. Active deployment boundary

```text
GitHub main
   |
   v
Akamai/Linode — Ubuntu 24.04 LTS
   |
   +--> eba-binance-data.service
   |       `--> Binance / NautilusTrader market data
   |
   +--> Trading / risk / paper execution layer
   |       `--> TradeLedger (SQLite)
   |
   +--> eba-runtime-api.service
   |       `--> local API 127.0.0.1:8765
   |
   `--> authenticated HTTPS reverse proxy   [pending]
            |
            `--> PWA/dashboard              [migration pending]
```

GitHub `main` is the code source of truth. Linode is the sole active backend/runtime target. Replit and Render.com are deprecated for EBA Trader backend work.

## 3. Runtime data flow

```text
Binance market data
   |
   v
Data Engine
   |
   +--> Feature / indicator state
   +--> Regime / setup classification
   |
   v
Strategy proposal
   |
   +--> LONG
   +--> SHORT
   `--> NO_TRADE
   |
   v
Deterministic Risk Engine
   |
   v
Paper Execution
   |
   +--> OPEN
   +--> UPDATE mark / P&L / risk state
   `--> CLOSE TP / SL / manual / rule exit
   |
   v
SQLite TradeLedger
   |
   v
Runtime API -> PWA positions / history / trade detail
```

The browser is never the authoritative store for an active trade.

## 4. Core modules

### Data Engine

Responsibilities:
- normalize market data,
- maintain freshness timestamps,
- reject stale or malformed data,
- expose venue-independent models.

### Strategy layer

A strategy must return a structured proposal or `NO_TRADE`. Strategy code cannot bypass risk controls.

The historical Spot Trend research remains a preserved research track. The next separate runtime strategy target is Fast Momentum / Micro Profit paper trading for BTCUSDT perpetual-futures simulation using 1m/5m inputs and both LONG/SHORT eligibility.

### Risk Engine

The Risk Engine is deterministic and has veto authority over every simulated or future live trade.

### Paper Execution

Paper execution must model:
- margin,
- leverage,
- notional exposure,
- entry and exit price,
- fees,
- slippage,
- TP and SL,
- liquidation distance for leveraged simulation,
- realized and unrealized net P&L,
- exit reason.

Every OPEN / UPDATE / CLOSE must be persisted.

### Persistence

SQLite is the current single-node durable store:

`/var/lib/eba-trader/eba_trader.db`

Git pulls, application upgrades, browser refreshes and service restarts must not delete trade state.

### Runtime API

Current local API service: `eba-runtime-api.service` on `127.0.0.1:8765`.

Existing endpoints include health, positions and events. Completed-trade history and richer trade-detail/chart metadata are next.

### PWA/dashboard

The PWA is a client, not a trading engine. It should display server truth: current position, history, entry/exit, TP/SL, leverage, indicators, fees, P&L and trade-specific chart data.

The old Render-backed client is transitional. It will be retired after the frontend is connected to authenticated Linode HTTPS.

## 5. Deployment rules

- Canonical first install: `scripts/install_linode_runtime.sh`
- Canonical update: `scripts/update_linode_runtime.sh`
- Canonical systemd units live in `deploy/systemd/`
- Do not create parallel Replit/Render runtime paths.
- Do not use browser RAM as persistent trade state.

## 6. Safety invariants

1. API keys/secrets are never committed to Git.
2. Withdrawal permission is never required.
3. Stale market data blocks new entries.
4. Position/account mismatch must fail closed before future live execution.
5. Deterministic risk controls have veto authority.
6. Every simulated/executed trade must have an auditable record.
7. Real order submission remains disabled until separately implemented, tested and explicitly promoted.
8. Higher leverage is paper/aggressive-demo scope until evidence supports it.

## 7. Validation path

```text
Hypothesis
  -> Backtest / causal checks
  -> Fee + slippage stress
  -> Forward paper
  -> Restart/recovery test
  -> PWA/server consistency test
  -> Shadow execution
  -> Explicit live gate
```

A profitable-looking backtest alone is not a production promotion criterion.
