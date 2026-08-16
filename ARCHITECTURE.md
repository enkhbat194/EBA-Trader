# EBA Trader Architecture

## 1. System goal

EBA Trader is designed as a research-first autonomous trading system, not a signal toy and not an LLM that guesses price direction.

The V1 production target is BTC/USDT spot trading with deterministic risk control and explicit validation gates.

## 2. High-level flow

```text
Market Data
   |
   v
Data Engine
   |
   +--> Regime Detector
   |
   +--> Feature Engine
   |
   +--> Strategy Library
   |       |- Trend Following
   |       |- Mean Reversion
   |       |- Breakout
   |       |- Momentum
   |       `- NO_TRADE
   |
   v
Meta Trader
   |
   +--> AI Analyst / Critic (advisory only)
   |
   v
Deterministic Risk Engine
   |
   v
Execution Gateway
   |
   +--> Paper
   +--> Shadow
   `--> Live (locked in V1)
```

## 3. Core modules

### Data Engine
Responsibilities:
- normalize candles, trades and order-book events,
- maintain freshness timestamps,
- reject stale or malformed market data,
- expose venue-independent domain models.

### Regime Detector
Classifies the market into one of:
- `BULL_TREND`
- `BEAR_TREND`
- `RANGE`
- `BREAKOUT`
- `HIGH_VOLATILITY`
- `CHAOS`
- `UNKNOWN`

The regime detector does not place trades. It changes which strategies are eligible.

### Strategy Library
Each strategy must:
- consume normalized data,
- declare compatible regimes,
- return a structured proposal,
- never bypass the risk engine,
- return `NO_TRADE` when evidence is insufficient.

### Meta Trader
The Meta Trader ranks eligible strategy proposals and can reject all of them. It must not invent a position if no strategy passes confidence and risk gates.

### AI layer
AI is allowed to:
- summarize news and macro context,
- generate research hypotheses,
- critique strategy proposals,
- explain performance drift,
- propose experiments.

AI is not allowed to:
- modify hard risk limits at runtime,
- send orders directly,
- enable leverage,
- switch the system into live mode,
- deploy an unvalidated strategy.

### Risk Engine
The Risk Engine is deterministic and has veto authority over every trade proposal.

### Execution Gateway
Execution is adapter-based. Strategy code must not depend on Binance-specific request/response structures.

Initial modes:
1. `BACKTEST`
2. `PAPER`
3. `SHADOW`
4. `MICRO_LIVE` (future gated)
5. `LIVE` (future gated)

## 4. Technology decisions

### Python
Strategy/research layer uses Python 3.12+.

### NautilusTrader
Target event-driven trading engine. Current official support includes Python 3.12-3.14 and Binance Spot integration. Stable releases only are allowed for any future real-capital stage.

### Exchange abstraction
V1 target adapter: Binance Spot.
Future adapters: OKX, then traditional-market access for gold research.

## 5. Safety invariants

The following must always hold:

1. `LIVE` cannot be enabled by an AI model.
2. Futures and leverage are disabled in V1.
3. Withdrawal permission is never required.
4. Stale data causes trading halt.
5. Position/account mismatch causes trading halt.
6. Daily-loss and drawdown limits have hard veto authority.
7. A new strategy cannot self-promote to production.
8. Every executed or simulated decision is logged with rationale and inputs.

## 6. Validation pipeline

```text
Hypothesis
  -> Backtest
  -> Bias checks
  -> Out-of-sample
  -> Walk-forward
  -> Fee/slippage stress
  -> Paper
  -> Shadow
  -> Human approval gate
  -> Micro-live
```

Failure at any gate returns the strategy to research or retires it.

## 7. V1 excluded scope

- futures,
- leverage,
- martingale,
- copy trading,
- random altcoin trading,
- exchange arbitrage,
- autonomous parameter mutation in production,
- direct LLM order placement.
