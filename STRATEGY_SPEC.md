# EBA Trader Strategy Specification

## V1 strategy contract

Every strategy must return a structured proposal with:

- strategy name,
- decision: `BUY`, `EXIT`, or `NO_TRADE`,
- confidence score in `[0, 1]`,
- entry reference price,
- stop/invalidation price,
- optional target/reference exit logic,
- compatible market regime,
- machine-readable reason codes,
- human-readable explanation.

A strategy may not submit orders directly.

## Initial strategy library

### 1. Trend Following
Purpose: participate when directional structure is persistent.

Candidate features:
- EMA alignment,
- ADX/trend strength,
- higher-high / higher-low structure,
- volume confirmation,
- ATR-normalized distance.

Eligible regimes:
- `BULL_TREND`
- future V2: `BEAR_TREND` with short-capable products.

### 2. Mean Reversion
Purpose: trade reversion inside a validated range.

Candidate features:
- distance from rolling mean,
- Bollinger/z-score style deviation,
- range boundary proximity,
- volatility contraction,
- failed breakout evidence.

Eligible regime:
- `RANGE`

Must disable when trend/breakout evidence exceeds threshold.

### 3. Breakout
Purpose: participate when price exits a well-defined compression/range with confirmation.

Candidate features:
- range duration,
- volatility compression,
- breakout distance,
- volume expansion,
- retest/hold confirmation.

Eligible regimes:
- `BREAKOUT`
- transition from `RANGE`.

### 4. Momentum
Purpose: participate in accelerating price/volume continuation when the move is not already excessively extended.

Candidate features:
- rate of change,
- volume acceleration,
- short/medium horizon alignment,
- ATR-normalized extension,
- exhaustion filter.

Eligible regimes:
- `BULL_TREND`
- `BREAKOUT`

### 5. NO_TRADE
`NO_TRADE` is not a fallback bug. It is a first-class strategy decision.

Mandatory examples:
- conflicting regime evidence,
- insufficient signal quality,
- abnormal volatility,
- stale data,
- risk veto,
- expected edge <= estimated cost,
- strategy disagreement without a clear winner.

## Meta Trader selection

The Meta Trader:

1. filters strategies by regime compatibility,
2. rejects invalid proposals,
3. applies risk/cost pre-checks,
4. ranks remaining proposals,
5. may choose `NO_TRADE` even if one or more strategies suggest an entry.

No ensemble vote automatically creates a trade.

## Future research, not V1

- funding crowding,
- open-interest divergence,
- liquidation rebound,
- order-book crowding fingerprints,
- grid-breaker logic,
- cross-exchange arbitrage,
- gold/macro strategies.
