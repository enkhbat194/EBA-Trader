# EBA Trader Strategy Specification

## Active strategy contract

Every runtime strategy must return a structured proposal with:

- strategy name,
- decision: `LONG`, `SHORT`, `EXIT`, or `NO_TRADE`,
- confidence/score inputs,
- entry reference price,
- stop/invalidation price,
- target/exit logic,
- compatible market regime,
- leverage tier requested for paper simulation,
- indicator/feature snapshot used for the decision,
- machine-readable reason codes,
- human-readable explanation.

A strategy may not submit exchange orders directly.

## Historical research library

Trend Following, Mean Reversion, Breakout, Momentum and `NO_TRADE` remain valid research categories. Existing M1/M2/M3 evidence files are preserved and should be treated as historical research records.

The rejected Spot Trend evidence does not block development of a separate, independently validated short-horizon strategy.

## Fast Momentum / Micro Profit — next runtime target

Purpose: test whether short-horizon directional BTCUSDT moves can produce positive **net** expectancy after fees/slippage using small paper margin and controlled leverage.

### Inputs

Primary target inputs:

- 1m execution context,
- 5m confirmation context,
- price momentum / rate of change,
- trend alignment,
- volume expansion/relative volume,
- RSI,
- ADX/trend strength,
- spread/cost filter,
- volatility/exhaustion filter.

Additional indicators may be added only when they have a defined role and can be persisted/displayed in trade detail.

### Direction

Both directions must be supported:

- `LONG` when qualified bullish momentum/structure passes risk and cost gates;
- `SHORT` when qualified bearish momentum/structure passes risk and cost gates;
- `NO_TRADE` when neither side has adequate edge.

A rising market is not the only valid opportunity source. Bearish momentum must be evaluated symmetrically rather than forcing LONG-only behavior.

### Paper leverage tiers

Normal paper evaluation starts with:

- 5x,
- 10x,
- 20x.

50x/100x remain aggressive-demo tiers and must not silently become normal or live defaults.

### Required trade record

Each opened paper trade must persist:

- unique trade/position id,
- symbol,
- side,
- entry time/price,
- margin,
- leverage,
- notional,
- TP,
- SL,
- current/exit price,
- fees/slippage,
- gross/net P&L,
- strategy and reason codes,
- indicator snapshot,
- exit time/reason,
- chart metadata sufficient for a dedicated trade-detail view.

### UI visibility requirement

For every open or completed trade the PWA must be able to show:

- where the trade entered,
- current/exit point,
- TP and SL lines,
- LONG/SHORT and leverage,
- indicators/values used at entry,
- realized/unrealized net P&L,
- exit reason,
- a dedicated zoomable trade chart.

## NO_TRADE

`NO_TRADE` is a first-class decision, not a bug. It is mandatory when:

- signal quality is insufficient,
- LONG/SHORT evidence conflicts,
- spread/fees/slippage erase expected edge,
- data is stale,
- runtime persistence/health is degraded,
- volatility is outside the tested envelope,
- risk engine vetoes the setup.

## Selection and risk authority

The strategy layer proposes; the deterministic Risk Engine decides whether the proposal may become a paper position. No score, ensemble vote, or AI recommendation can bypass a veto.

## Later research

- funding/open-interest crowding,
- liquidation data,
- order-book imbalance/crowding,
- gold/MT5 strategies,
- cross-exchange logic.

These are separate research tracks and should not be mixed into Fast Momentum without explicit testing.
