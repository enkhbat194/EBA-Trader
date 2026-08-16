# EBA Trader

EBA Trader is a research-first autonomous trading system project.

## Mission

Build a professional-grade trading engine that can:

1. read live market data,
2. classify the current market regime,
3. select among validated strategies,
4. reject low-quality setups with `NO_TRADE`,
5. enforce deterministic risk limits,
6. measure every decision against benchmarks,
7. learn through research and validation without allowing unvalidated AI output to control real capital.

## V1 scope (frozen)

- Market: `BTC/USDT`
- Venue target: Binance
- Product: Spot only
- Core engine target: NautilusTrader
- Timeframes: 5m execution, 15m signal, 1h regime
- Strategies: Trend Following, Mean Reversion, Breakout, Momentum, NO_TRADE
- Modes: Backtest -> Paper -> Shadow -> Micro-Live (future gated stage)
- Futures/leverage: disabled in V1
- Live-money execution: disabled until validation gates are passed

## Non-negotiable design rules

- AI is an analyst/researcher/critic, not the final risk authority.
- The Risk Engine is deterministic code.
- A strategy is not promoted because a backtest looks profitable.
- Fees, slippage, latency assumptions, out-of-sample tests and walk-forward tests are required.
- `NO_TRADE` is a first-class decision.
- Exchange adapters must not leak venue-specific logic into strategy code.
- API keys must never be committed to Git.
- Withdrawal permission must never be required by the bot.

## Current status

**Phase 0 — Bootstrap**

The repository is being initialized with architecture, risk policy, validation protocol and the first pure-Python domain core. Exchange execution remains disabled.

See `PROJECT_STATE.md` for the authoritative project continuation state.
