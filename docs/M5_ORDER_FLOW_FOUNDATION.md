# M5 Order-Flow / Footprint Research Foundation

## Decision

EBA Trader will add order-flow and footprint information as a **research feature family**, not as a trusted trading signal and not as a direct execution trigger.

The purpose is empirical: compare existing candle/indicator strategies against otherwise equivalent strategies augmented with microstructure features. Promotion remains controlled by M4 evidence, screening, robustness, OOS, paper and later execution gates.

## Data semantics

A footprint is derived from market events; the system must not infer it from chart pixels.

Initial inputs:

- executed aggregate/raw trades with timestamp, price, quantity and aggressor side when the exchange feed supports it;
- best bid/ask and depth snapshots/deltas where historical and live collection can be made reproducible;
- candle boundaries only for aggregation/window alignment.

Executed trade flow and resting order-book liquidity are separate datasets and must never be silently mixed.

## Initial feature families

### Trade-flow / footprint

- buy volume
- sell volume
- delta = buy volume - sell volume
- delta ratio
- cumulative volume delta (CVD)
- price-level bid/ask volume buckets
- point of control / maximum traded-volume price bucket
- diagonal/stacked imbalance candidates
- concentration / cluster statistics

### Derived behavioural candidates

- absorption candidate: high aggressive flow with limited price progress
- exhaustion candidate: declining aggressive flow near an extreme
- price/delta divergence

These are numerical research labels/features, not assertions that a hidden institutional order has been identified.

### Limit-order-book family

Kept separate from footprint features:

- top-of-book spread
- bid/ask depth
- normalized depth imbalance
- multi-level depth imbalance
- liquidity concentration
- depth change / replenishment candidates

## Research comparisons

At minimum M5 must support controlled ablation families:

- A: candle + existing indicators (baseline)
- B: A + delta/CVD
- C: A + footprint imbalance
- D: A + absorption/exhaustion candidates
- E: A + order-book imbalance
- F: A + combined approved order-flow features

Order flow is considered useful only when it improves out-of-sample/forward evidence after fees, slippage and robustness. A higher development win rate alone is insufficient.

## Anti-leakage requirements

1. A feature for decision time T may use only events observable at or before T.
2. Candle/footprint bucket final values cannot be used before the bucket closes unless the strategy explicitly models an in-progress bucket.
3. Historical book reconstruction must preserve exchange event ordering and sequence integrity.
4. Missing depth/trade events must be detectable; corrupted windows fail closed.
5. Dataset source, interval, symbol, feature configuration and hashes become research provenance.
6. Frozen OOS remains inaccessible to generic M5 generation/tuning.

## Architecture

```text
Binance market events
    |
    +-- executed trades --------> Trade Flow Aggregator
    |                                  |
    |                                  +--> footprint/delta/CVD features
    |
    +-- book snapshot/deltas ---> LOB Reconstructor
                                       |
                                       +--> depth/imbalance features

features + candles
        |
        v
constrained M5 strategy hypothesis/schema
        |
        v
M4 deterministic experiments -> screening -> robustness -> later OOS/paper
```

## Implementation batches

1. Define typed order-flow event and feature contracts with deterministic aggregation tests.
2. Add reproducible historical trade-flow ingestion/cache and integrity/provenance checks.
3. Implement delta/CVD and price-level footprint aggregation first.
4. Add imbalance/POC/absorption candidate features with explicit definitions and tests.
5. Add order-book reconstruction only after event-sequence integrity is proven.
6. Extend M5 hypothesis DSL so strategy families can opt into approved feature names; arbitrary formulas/code remain prohibited.
7. Run ablation experiments against candle-only baselines through M4.
8. Promote no feature merely because it looks persuasive on a chart.

## Safety boundary

This milestone does not unlock frozen OOS, Binance Demo orders, shadow/live orders, or real-money execution. Deterministic risk authority remains unchanged.
