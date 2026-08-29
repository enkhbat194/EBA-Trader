# EBA Trader — Open-source trading-system pattern audit

Date: 2026-08-30
Scope: development/research architecture only. Frozen OOS and real-money execution remain locked.

## Why this audit exists

EBA Trader should not re-invent mature infrastructure where well-tested open-source projects already expose useful design patterns. At the same time, popularity is not evidence of profitability, and code must not be copied blindly. Every adopted pattern must be reimplemented or imported only under a compatible license, covered by EBA tests, and validated against EBA's own data/evidence contracts.

## Reference projects

### Freqtrade — freqtrade/freqtrade
- Role: mature Python crypto bot with backtesting, dry-run, hyperopt/FreqAI, WebUI and analysis tooling.
- License: GPL-3.0.
- Adoption rule: ideas/architecture only; do not copy GPL implementation into EBA Trader unless the project intentionally adopts compatible GPL obligations.
- High-value patterns:
  - explicit look-ahead-bias analysis;
  - recursive-indicator analysis;
  - dry-run/paper mode separation;
  - backtest analysis and strategy optimization workflow;
  - persistent trade state and operator-facing status.
- EBA decision:
  - ADD an explicit causality/look-ahead audit gate before any strategy can qualify for OOS;
  - KEEP current EBA Demo/live hard lock instead of replacing it with Freqtrade runtime.

### NautilusTrader — nautechsystems/nautilus_trader
- Role: deterministic event-driven trading engine with shared research/live semantics and normalized venue adapters.
- License: LGPL-3.0.
- High-value patterns:
  - same event/time semantics across backtest and live;
  - normalized adapters around exchange-specific APIs;
  - deterministic execution model;
  - strong supply-chain/security controls.
- EBA decision:
  - DESIGN toward one strategy/execution contract shared by historical simulation, forward paper and later micro-live;
  - ADD deterministic event/evidence IDs and stronger dependency/security provenance incrementally;
  - DO NOT migrate the project to Rust merely to imitate Nautilus.

### Hummingbot — hummingbot/hummingbot
- Role: crypto execution/market-making framework with standardized exchange connectors and reusable executors.
- License: Apache-2.0.
- High-value patterns:
  - connectors separate exchange API details from strategy logic;
  - reusable executors manage position/order lifecycle;
  - position executor uses bounded risk controls rather than letting strategy code manually own every order transition;
  - strategy/controller/executor separation.
- EBA decision:
  - ADD a formal execution lifecycle layer before real-money unlock: intent -> risk approval -> order -> fill reconciliation -> position -> exit -> terminal evidence;
  - KEEP strategy research independent from exchange connector implementation;
  - future Binance/other-venue adapters must satisfy one EBA execution interface.

### Jesse — jesse-ai/jesse
- Role: Python quantitative crypto framework with backtest, paper/live, benchmarking, MCP, significance tests, Monte Carlo and ML workflow.
- License: MIT.
- High-value patterns:
  - rule significance test against random-entry/bootstrap null distributions;
  - Monte Carlo stress analysis;
  - batch benchmark across strategies/timeframes/symbols;
  - strategy decisions visible on synchronized charts;
  - MCP/AI tooling operating on real project state rather than free-form guesses.
- EBA decision:
  - HIGHEST PRIORITY: add a statistical significance/null-model gate for candidate entry rules;
  - ADD Monte Carlo stress only after a candidate has sufficient real trade samples;
  - ADD benchmark-style batch evaluation when independent strategy families exist;
  - later expose traceable trade-decision evidence to the PWA/AI Lab.

### QuantConnect LEAN — QuantConnect/Lean
- Role: general-purpose algorithmic trading engine with multi-asset brokerage/execution modeling.
- License: Apache-2.0.
- High-value patterns:
  - explicit brokerage/fill/slippage modeling;
  - separation between signal generation, portfolio construction, risk and execution;
  - realistic order/event lifecycle.
- EBA decision:
  - strengthen EBA fill/slippage model before any profitability claim;
  - keep fee/slippage stress mandatory;
  - later introduce portfolio/risk layer only after multiple independently validated strategies exist.

## Priority adoption plan

### P0 — before Frozen OOS can ever open
1. Independent strategy families, not only EMA-entry filters.
2. Minimum-activity and positive-expectancy qualification gate. (Already added.)
3. Candidate activity diagnostics. (Already added.)
4. Explicit look-ahead/causality audit inspired by Freqtrade.
5. Rule-significance/null-model test inspired by Jesse.
6. Cost/fill stress with fees and slippage kept mandatory.
7. Robustness across parameter neighborhood and market windows.

### P1 — after a candidate has adequate samples
1. Trade/candle Monte Carlo stress inspired by Jesse.
2. Execution lifecycle abstraction inspired by Hummingbot/LEAN.
3. Shared historical/paper/live strategy semantics inspired by NautilusTrader.
4. Batch benchmark across independent families and regimes.

### P2 — later product advantages
1. Strategy decision trace/chart UI.
2. AI/MCP research tools operating on immutable experiment evidence.
3. Multi-venue adapter contract.
4. Portfolio selector and drift monitoring after several verified strategies exist.

## What EBA Trader will not copy

- Public "profitable strategies" merely because a repository has many stars.
- Unverified parameter sets or claimed win rates.
- GPL code into the current codebase without an explicit licensing decision.
- Exchange credentials, secret-handling patterns, or live-order code without an independent security review.
- Backtest engines that cannot prove causal data alignment and realistic costs.

## Immediate next implementation

The next research architecture step is to add a development-only statistical validation layer before robustness promotion:

1. expose deterministic candidate entry/trade samples from the existing backtest execution without opening Frozen OOS;
2. build a null-model/significance test for candidate signals;
3. require adequate sample size before computing significance;
4. record immutable significance evidence;
5. then expand independent families such as ATR trailing-stop, breakout, mean-reversion and order-flow impulse through the same 12-window pipeline.

No result from this audit authorizes real-money execution or Frozen OOS access.
