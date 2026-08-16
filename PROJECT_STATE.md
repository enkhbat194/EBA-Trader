# EBA Trader — Project State

_Last updated: 2026-08-17 (Asia/Ulaanbaatar)_

This file is the authoritative cross-chat continuation record. Update it whenever architecture, scope, progress, blockers or next tasks change.

## Mission

Create an autonomous professional-grade trading system that can analyze markets, choose among validated strategies, refuse low-quality trades, enforce hard risk limits and eventually execute through exchange APIs after evidence-based validation.

## User constraints / product intent

- The owner does not want to manually master a complex exchange UI before the system becomes useful.
- Front-end UI should remain simple; complexity belongs in the engine.
- The system should learn from historical bot/trading-system failure modes rather than copy a single retail bot strategy.
- The owner wants a real trading engine, not a decorative AI signal generator.
- Cross-chat continuity is mandatory; repo state must preserve decisions and next work.
- Avoid unnecessary paid infrastructure during bootstrap.
- **Bootstrap infrastructure budget is locked to $0 until a strategy edge is demonstrated.**
- BestCode integration is deferred; EBA Trader remains standalone for V1.

## Frozen V1 decisions

- Repository: `enkhbat194/EBA-Trader`
- Market: BTC/USDT
- Product: Spot
- Primary exchange target: Binance
- Backup exchange target: OKX
- Existing KuCoin account: not the V1 backend
- Engine target: `nautilus_trader==1.230.0`
- Python: 3.12-3.14 compatibility target
- Runtime shape: standalone networked Linux/Python process
- Permanent paid 24/7 server: deferred until edge evidence exists
- UI: deferred until paper workflow is validated
- Timeframes: 5m execution, 15m signal, 1h regime
- Strategies: Trend Following, Mean Reversion, Breakout, Momentum, NO_TRADE
- AI role: research / analysis / critique only
- Risk authority: deterministic Risk Engine
- Live funds: disabled during bootstrap/research
- Futures/leverage: out of scope for V1

## Completed

- [x] Repository created as private
- [x] Core architecture, strategy, risk and backtest contracts documented
- [x] Deterministic Risk Engine V1 and position sizing added
- [x] Live/micro-live mode locked by default
- [x] Baseline Regime Detector and first-class `NO_TRADE` added
- [x] Initial unit tests passed on Python 3.13.5
- [x] NautilusTrader pinned to `1.230.0`
- [x] Binance data-only probe for `BTCUSDT.BINANCE` added
- [x] Public live mode requires no API key
- [x] Demo credentials are environment-only
- [x] No execution client exists in M1 data path
- [x] Quote, trade and 1-minute bar subscriptions configured
- [x] Market-data health bridges to deterministic `STALE_MARKET_DATA` hard halt
- [x] Replit imported from GitHub and confirmed Python **3.12.12**
- [x] `eba-trader` + `nautilus-trader==1.230.0` installed successfully in Replit Linux
- [x] Replit test suite completed at **100%** before M2 changes
- [x] Actual Binance public WebSocket connectivity proven in Replit
- [x] Actual `QuoteTick(BTCUSDT.BINANCE, ...)` events observed
- [x] Actual `TradeTick(BTCUSDT.BINANCE, ...)` events observed
- [x] Zero-cost bootstrap policy locked
- [x] M2 historical downloader added using Binance public REST only
- [x] Historical candle integrity validation added: ordering, duplicates, OHLC sanity
- [x] Trend Following V1 research backtest added
- [x] Signal-at-close / next-bar-open execution rule added to reduce look-ahead risk
- [x] Fee + slippage costs included in baseline
- [x] BTC buy-and-hold benchmark included
- [x] Historical/backtest unit tests added
- [x] M2 runbook added at `docs/M2_BACKTEST_LAB.md`

## Current validation status

### M0 — Safe research engine bootstrap

**PASSED.**

### M1 — Binance data-only pipeline

**Runtime connectivity PASSED.**

Evidence captured on 2026-08-17 in Replit Linux/Python 3.12.12:
- NautilusTrader 1.230.0 installed;
- public Binance WebSocket connected;
- live BTC/USDT QuoteTick events received;
- live BTC/USDT TradeTick events received;
- no exchange account key or execution client used.

Note: the screenshot evidence captured quote/trade events within seconds. A 1-minute bar event was subscribed but was not separately captured in the screenshot; this does not block historical M2 work.

### M2 — Historical Data & Backtest Laboratory

**M2A code path implemented; Replit runtime validation pending.**

Implemented:
- `eba-download-history` public REST downloader;
- CSV persistence under ignored `data/raw/`;
- timestamp/duplicate/OHLC validation;
- `eba-backtest-trend` long-only EMA crossover baseline;
- next-bar-open execution;
- fee/slippage model;
- buy-and-hold benchmark;
- return, drawdown, trades, win rate, profit factor, expectancy, approximate Sharpe, exposure and cost output;
- deterministic tests for data integrity and cost behavior.

## In progress

- [ ] Pull latest GitHub changes into Replit.
- [ ] Reinstall editable package so the two new CLI commands are registered.
- [ ] Run full test suite after M2 changes.
- [ ] Download the first historical BTC/USDT 15m dataset.
- [ ] Run Trend Following V1 baseline and capture metrics.

## Next tasks — strict order

1. Validate M2A on Replit (`pytest`).
2. Download a bounded 15m BTC/USDT research window from Binance public REST.
3. Run Trend Following V1 baseline with explicit fee/slippage assumptions.
4. Inspect result versus BTC buy-and-hold and reject obvious failures.
5. Add explicit in-sample / out-of-sample split.
6. Add repeated walk-forward windows across bull, bear and range regimes.
7. Add base/adverse/severe cost scenarios.
8. Add parameter-neighborhood robustness tests.
9. Only after credible positive expectancy after costs: introduce forward paper/shadow execution.
10. Futures/crowding/liquidation remains V2+.

## Explicitly not allowed yet

- permanent paid VPS/server during unproven bootstrap,
- real-money order placement,
- futures,
- leverage,
- copy trading,
- martingale,
- AI-controlled order submission,
- strategy self-deployment,
- API withdrawal permission.
