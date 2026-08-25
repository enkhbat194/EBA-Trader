# EBA Trader Architecture

## 1. System goal

EBA Trader is a research-first trading system with a persistent 24/7 runtime. The runtime must keep market data, paper positions, trade history and risk state independent of whether the browser/PWA is open.

M4 adds a separate research control plane for immutable strategy versions, experiments and lifecycle evidence. Research metadata is not runtime position state and cannot bypass execution/risk gates.

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
   `--> HTTPS reverse proxy / public PWA
            `--> automatic bootstrap implemented;
                 final external smoke-test proof remains required
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

## 4. Research control plane

```text
Strategy specification
   |
   v
Immutable Strategy Version
   |
   v
Experiment metadata / evidence
   |
   v
Lifecycle gates
   |
   +--> REJECT / QUARANTINE / RETEST
   `--> eligible next validation stage
```

The M4 research store is separate from `TradeLedger`. Later AI strategy generation and experiment workers must write through this control plane rather than generating untracked backtest artifacts.

## 5. Core modules

### Data Engine

Responsibilities:
- normalize market data,
- maintain freshness timestamps,
- reject stale or malformed data,
- expose venue-independent models.

### Strategy layer

A strategy must return a structured proposal or `NO_TRADE`. Strategy code cannot bypass risk controls.

The generic strategy decision contract is `LONG`, `SHORT`, `EXIT`, `NO_TRADE`. Historical `BUY` callers are temporarily mapped to `LONG` during migration.

The historical Spot Trend research remains a preserved research track. The current runtime strategy target is Fast Momentum / Micro Profit paper trading for BTCUSDT perpetual-futures simulation using 1m/5m inputs and both LONG/SHORT eligibility.

### Strategy lifecycle

New M4+ strategy versions follow the machine-enforced path documented in `BACKTEST_PROTOCOL.md` and `docs/M4_STRATEGY_PLATFORM_FOUNDATION.md`. Promotion requires an evidence reference and gates cannot be skipped.

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

### Runtime persistence

SQLite is the current single-node durable runtime store:

`/var/lib/eba-trader/eba_trader.db`

Git pulls, application upgrades, browser refreshes and service restarts must not delete trade state.

### Research persistence

M4 introduces a separate research metadata SQLite store. Development defaults to `artifacts/research/eba_research.db`; deployment of a long-running research worker may later move it to durable server state after that worker architecture is explicitly approved.

### Runtime API

Current local API service: `eba-runtime-api.service` on `127.0.0.1:8765`.

### PWA/dashboard

The PWA is a client, not a trading engine. It displays server truth: current position, history, entry/exit, TP/SL, leverage, indicators, fees, P&L and trade-specific chart data.

The active PWA source lives under `web/` in GitHub `main` and is served from the Linode runtime. Public HTTPS bootstrap is implemented; external phone/browser verification remains a production-proof gate.

## 6. Deployment rules

- Canonical first install: `scripts/install_linode_runtime.sh`
- Canonical update: `scripts/update_linode_runtime.sh`
- Canonical systemd units live in `deploy/systemd/`
- Do not create parallel Replit/Render runtime paths.
- Do not use browser RAM as persistent trade state.
- Do not couple research experiment metadata to runtime position persistence.

## 7. Safety invariants

1. API keys/secrets are never committed to Git.
2. Withdrawal permission is never required.
3. Stale market data blocks new entries.
4. Position/account mismatch must fail closed before future live execution.
5. Deterministic risk controls have veto authority.
6. Every simulated/executed trade must have an auditable record.
7. Real order submission remains disabled until separately implemented, tested and explicitly promoted.
8. Higher leverage is paper/aggressive-demo scope until evidence supports it.
9. Strategy lifecycle eligibility never bypasses deterministic risk authority.
10. Strategy version evidence is immutable; changed specs require new versions.

## 8. Validation path

```text
Hypothesis
  -> Backtest / causal checks
  -> Frozen OOS
  -> Robustness / walk-forward / cost stress
  -> Forward paper
  -> Restart/recovery test
  -> Exchange Demo execution validation
  -> Shadow execution
  -> Explicit micro-live eligibility gate
```

A profitable-looking backtest alone is not a production promotion criterion.
