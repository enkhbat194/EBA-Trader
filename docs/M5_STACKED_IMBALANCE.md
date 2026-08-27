# M5 Stacked / Diagonal Imbalance Research Contract

## Scope

This milestone adds executed-trade footprint stacked imbalance as a **development-only** M5 feature. It does not infer resting order-book liquidity and it grants no frozen-OOS, lifecycle-promotion, Demo-order or real-order authority.

## Deterministic definition

For an ordered footprint with configured price bucket `step`:

- bullish diagonal imbalance at price `p` compares aggressive buy volume at `p` with aggressive sell volume at exactly `p-step`;
- bearish diagonal imbalance at price `p` compares aggressive sell volume at `p` with aggressive buy volume at exactly `p+step`;
- both compared cells must exceed the configured minimum volume;
- the dominant volume must be at least `ratio_threshold` times the opposite diagonal volume;
- a missing price bucket is **not** treated as adjacent and breaks a stack;
- an empty opposite cell does not create an infinite imbalance.

The feature stores the longest consecutive bullish and bearish runs plus a signed score:

- positive score: bullish run is longer;
- negative score: bearish run is longer;
- zero: equal/no dominant run.

## Causal availability

Stacked values are computed from the same prior closed footprint used by the existing Delta/CVD feature dataset. For a candle opening at `t`, only footprint `[t-step,t)` is available. The still-forming footprint `[t,t+step)` is forbidden from that candle decision.

## Dataset schema

New materializations use `m5_orderflow_feature_dataset_v2` and persist:

- `of_stacked_buy_levels`
- `of_stacked_sell_levels`
- `of_stacked_imbalance`
- `imbalance_ratio`
- `imbalance_min_volume`

Legacy v1 feature CSVs remain readable for historical Delta/CVD replay. They default stacked values to zero, but a stacked-imbalance backtest gate fails closed unless the v2 stacked columns are physically present.

## Backtest gate

`EmaOrderFlowV1Adapter` may consume `stacked_imbalance_threshold` as an additive allowlisted development gate. The threshold is an integer `>= 1` and the treatment still uses the exact same aligned candle dataset, EMA configuration, capital, fees, slippage and exit assumptions as the candle baseline.

## Bounded policy

`config/m5_stacked_imbalance_gate_set_v2.json` contains only three development variants: thresholds `1`, `2`, and `3`. The existing Delta/CVD v1 gate configuration is not rewritten.

## Safety

- Frozen OOS remains locked.
- Development ranking is not edge proof.
- Real exchange order submission remains locked.
- Deterministic risk authority is unchanged.
- LOB/order-book imbalance remains a separate later data plane.
