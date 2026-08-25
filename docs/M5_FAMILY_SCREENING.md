# M5 Family Templates, Similarity Guard and Cheap Screening

This batch constrains strategy generation before expensive research work is queued.

## Approved templates

Initial bounded templates:

- `ema_momentum` — candle-only baseline family;
- `ema_orderflow_momentum` — otherwise similar family with approved executed order-flow features.

Both ship with finite parameter grids. Templates are research hypotheses, not claims of edge.

## Near-duplicate control

Exact duplicates are already suppressed by structural fingerprints and M4 deterministic experiment IDs. This batch adds a near-duplicate similarity check based on family, direction, timeframe, feature set, and condition/operator structure while intentionally ignoring free-text rationale and numeric threshold-only variation.

This prevents an AI from flooding the queue with hundreds of cosmetically different hypotheses that are structurally the same trade idea.

## Cheap screen

Before expensive backtests, a hypothesis may be rejected for:

- excessive feature count;
- excessive entry/exit condition count;
- excessive parameter fan-out;
- an order-flow-labelled family that contains no approved order-flow feature.

Cheap screening is static. It does not promote lifecycle state and does not substitute for development backtest gates.

## Survivor ranking

A deterministic development ranking helper considers only PASSED experiments with finite:

- profit factor;
- expectancy;
- max drawdown;
- trade count.

Missing, malformed, non-finite or failed experiments are excluded. Ranking is only a triage mechanism for which candidates receive more expensive robustness work. It does not authorize frozen OOS, paper, Demo or live execution.

## Next batch

1. historical executed-trade ingestion/cache with integrity and provenance;
2. materialize footprint windows/features for research datasets;
3. connect order-flow features to an allowlisted backtest adapter;
4. run candle-only versus candle+order-flow ablation families through M4.
