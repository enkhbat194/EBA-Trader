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

## Production fixed-window evidence

Implementation was completed and merged in PR #56. PR #57 then preserved the earlier Delta/CVD immutable report, moved the Linode one-shot development autorun to the stacked gate set and hardened external production proof so stale Delta-only evidence cannot satisfy this milestone.

Functional stacked-proof main SHA: `738ed32e557045abb6b738c7f5236962ee3dd516`.

Fixed development window:

`2026-08-01T00:00:00Z -> 2026-08-01T04:00:00Z`

Batch:

`abl_232b7cb262de90363283356d`

Dataset workflow:

`m5ds_ca555c0ee588e17847d4c477`

Immutable Linode report:

`/var/lib/eba-trader/research/evidence/m5-stacked-imbalance-ablation-20260801T000000Z-20260801T040000Z.json`

External exact-build proof run `33070015871` completed successfully at `2026-08-27T12:08:54Z`. It verified exact build, HTTPS/public smoke, encrypted Demo reconnect, Chart, Positions, Fast restart proof, terminal/evidence-complete stacked report, thresholds exactly `1/2/3`, Frozen OOS closed and real execution locked.

### Candle-only control

- total return: `-0.004244488397751933` (~`-0.42445%`)
- final equity: `9957.55511602248`
- trade count: `4`
- win rate: `0.25`
- max drawdown: `-0.004244488397751933`
- expectancy: `-10.611220994379892`
- total cost: `43.90484437829747`

The control reproduces the prior Delta/CVD run exactly, which is a useful comparability invariant.

### Stacked threshold 1

- total return: `-0.0012408244799629875` (~`-0.12408%`)
- final equity: `9987.59175520037`
- trade count: `2`
- win rate: `0.5`
- max drawdown: `-0.0024163539692870772` (~`-0.24164%`)
- expectancy: `-6.204122399814878`
- total cost: `21.98249146741619`
- absolute baseline loss reduction: ~`70.77%`

### Stacked thresholds 2 and 3

Both thresholds produced the same result in this fixed window:

- total return: `-0.0013709100484625703` (~`-0.13709%`)
- final equity: `9986.290899515374`
- trade count: `1`
- win rate: `0.0`
- max drawdown: `-0.0013709100484625703`
- expectancy: `-13.709100484626106`
- total cost: `10.994657857876607`

## Interpretation and disposition

Threshold `1` materially improves the candle-only baseline, but it does **not** outperform the earlier best tested Delta treatment (`delta_ratio_threshold=0.2`) on total return or expectancy. Its absolute loss is about 2.93% larger than the Delta treatment's absolute loss. It does have slightly smaller drawdown and marginally lower cost, with the same two trades and 50% win rate.

Thresholds `2/3` reduce exposure and cost, but the single remaining trade loses, producing zero win rate and worse expectancy. This does not constitute stronger signal evidence.

Disposition: retain stacked/diagonal imbalance implementation and immutable evidence as useful M5 development infrastructure, but do not promote this family on the basis of this sample. The next controlled candidate family is absorption/exhaustion; price/delta divergence follows after that.

## Safety

- Frozen OOS remains locked.
- Development ranking is not edge proof.
- The stacked evidence has `developmentComparisonOnly=true`, `edgeClaimAllowed=false`, and `promotionAuthority=false`.
- Real exchange order submission remains locked.
- Deterministic risk authority is unchanged.
- LOB/order-book imbalance remains a separate later data plane.
