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
- Replit is not the development center. Use it only when a networked runtime is actually required; code/test work should be handled from the repo/assistant side whenever possible.

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
- [x] Historical candle integrity validation: ordering, duplicates and OHLC sanity
- [x] Historical interval-gap detector added
- [x] Historical download end timestamp made exclusive to prevent split-boundary leakage
- [x] Trend Following V1 long-only EMA 20/50 baseline added
- [x] Signal-at-close / next-bar-open execution rule added to reduce look-ahead risk
- [x] Fee + slippage costs included
- [x] BTC buy-and-hold benchmark included
- [x] Annualized return, benchmark-relative return, average win/loss and Sortino added
- [x] Sharpe/Sortino scaling made interval-aware instead of hard-coded to 15m
- [x] Frozen baseline evidence windows defined: 2021-2023 research, 2024 validation, 2025 out-of-sample
- [x] 2026+ left outside first baseline study for fresher later evidence
- [x] Base/adverse/severe cost scenarios defined
- [x] `eba-baseline-study` one-command M2 study added
- [x] Baseline study fails closed on missing interval data
- [x] JSON benchmark report output added at `artifacts/m2_trend_baseline.json`
- [x] New isolated M2 history/backtest/research logic tests executed locally: **10/10 passed**
- [x] M2 runbook updated at `docs/M2_BACKTEST_LAB.md`

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

A 1-minute bar event was subscribed but was not separately captured in the screenshot. This does not block M2 historical work.

### M2 — Historical Data & Backtest Laboratory

**M2A code path implemented and isolated deterministic logic validated. M2B needs public historical data.**

Frozen windows:
- research: `2021-01-01` → `2024-01-01` exclusive;
- validation: `2024-01-01` → `2025-01-01` exclusive;
- out-of-sample: `2025-01-01` → `2026-01-01` exclusive.

Cost scenarios:
- base: 10 bps fee + 5 bps slippage per side;
- adverse: 10 bps fee + 10 bps slippage per side;
- severe: 15 bps fee + 20 bps slippage per side.

Current caveat:
- the entire post-M2 repository suite has not been rerun in one Nautilus-enabled environment after the latest M2 changes;
- the new M2 modules were independently exercised with deterministic synthetic data and **10 tests passed**;
- the next network-required action is historical Binance REST acquisition, not interactive coding/debugging.

## In progress

- [ ] Obtain the three frozen BTC/USDT 15m windows from Binance public REST.
- [ ] Produce the first `m2_trend_baseline.json` evidence report.
- [ ] Review Trend Following V1 against BTC buy-and-hold, drawdown, expectancy and cost stress.

## Next tasks — strict order

1. Run the one-command `eba-baseline-study` in a free networked runtime after syncing/installing the latest package.
2. Capture the report, not screenshots of dozens of shell steps.
3. Reject or retain Trend Following V1 based on benchmark-relative return, drawdown, expectancy, trade count and severe-cost behavior.
4. Add parameter-neighborhood robustness around any retained baseline.
5. Add repeated walk-forward windows and regime-specific diagnostics.
6. Only after credible positive expectancy after costs: introduce forward PAPER/SHADOW execution.
7. Only after forward evidence: consider any 24/7 runtime or server cost.
8. Futures/crowding/liquidation remains V2+.

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
