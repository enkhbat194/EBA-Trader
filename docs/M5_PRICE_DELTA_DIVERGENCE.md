# M5 Price / Delta Divergence Candidate

Status: implementation candidate. No edge or promotion claim is permitted until the fixed development run is complete and interpreted.

## Research question

Does a causal mismatch between a completed price extreme and executed-trade Delta improve the existing EMA entry filter versus the exact same candle-only baseline?

This candidate uses executed Binance USD-M aggregate trades. It does **not** observe resting order-book liquidity, hidden orders, iceberg intent, OTC flow, or other venues.

## Causal alignment

The order-flow feature row available at candle open `t` contains the completed executed-flow window `[t-step, t)`. Therefore:

- the current completed price bar for that feature row is the previous candle `[t-step, t)`;
- the candle that opens at `t` is still forming and its high/low/close are forbidden inputs;
- every reference price/Delta pair must also be already closed before `t`.

The materializer enforces this mapping. Tests deliberately mutate the just-opening candle's future OHLC and require the divergence score available at `t` to remain unchanged.

## Versioned feature definition

Feature dataset schema: `m5_orderflow_feature_dataset_v4`.

Default research configuration:

- divergence lookback: `3` completed reference bars;
- minimum executed volume: `0.0`, with a strict `volume > minimum` activity requirement;
- signed feature: `of_price_delta_divergence`;
- positive score: bullish divergence;
- negative score: bearish divergence;
- score range: `[-1, 1]`.

Bullish divergence requires:

1. the current completed price bar makes a strict new low versus eligible reference bars; and
2. its Delta ratio is higher than the Delta ratio at the prior lowest-price reference, meaning selling pressure did not confirm the lower price.

Bearish divergence mirrors the rule:

1. the current completed price bar makes a strict new high; and
2. its Delta ratio is lower than the Delta ratio at the prior highest-price reference, meaning buying pressure did not confirm the higher price.

Directional strength is the Delta-ratio gap divided by the full possible Delta-ratio range of two. If one outside bar simultaneously produces both bullish and bearish divergence, the observation is ambiguous and the signed score is forced to zero. Insufficient history, zero activity, malformed inputs, or unsupported data fail closed.

## Controlled development treatments

The first bounded treatment set is intentionally small:

- `price_delta_divergence_threshold = 0.01`
- `price_delta_divergence_threshold = 0.05`
- `price_delta_divergence_threshold = 0.10`

The current `ema_orderflow_v1` research adapter only gates long EMA entries, so these treatments require positive/bullish divergence at the candidate entry. Bearish divergence is retained in the versioned feature dataset for future direction-aware strategy families; it is not silently converted into a short trade here.

## Fixed comparison contract

The development window remains unchanged:

`2026-08-01T00:00:00Z -> 2026-08-01T04:00:00Z`

The candle-only control and all divergence treatments must share:

- identical USD-M data acquisition and feature dataset;
- EMA parameters;
- initial capital;
- fees and slippage;
- trade-start semantics;
- development stage and evidence pipeline.

Interpretation must compare at least total return, expectancy, max drawdown, trade count, win rate, exposure, and total cost against the candle baseline and the earlier Delta, stacked-imbalance, and absorption/exhaustion candidates. A zero-trade arm is inactivity, not profitable-edge evidence.

## Safety locks

- Frozen OOS remains closed.
- Development ranking has no promotion authority.
- Real-money execution remains disabled.
- No generated Python from an AI hypothesis is executed.
- LOB/order-book reconstruction remains a separate future data plane.
