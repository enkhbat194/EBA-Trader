# M5 Absorption / Exhaustion — Development Evidence

## Status

Closed as **development-only evidence** after exact Linode fixed-window proof. No edge claim, lifecycle promotion, Frozen-OOS access, paper/demo promotion or real-execution authority is granted.

## Definitions used

These features are **executed-trade response proxies**, not claims about hidden/resting order-book liquidity.

- **Absorption proxy**: measures strong aggressive executed flow that produces relatively little same-window price response in the direction of that flow.
- **Exhaustion proxy**: measures weakening aggressive flow near the end of the observed price move/window.

Both are computed only from causal executed-trade footprint information already closed before the strategy decision. They do not reconstruct LOB depth, iceberg orders or OTC flow.

## Implementation

PR #59 added:

- causal absorption/exhaustion scores derived from normalized Binance USD-M aggregate trades;
- feature-dataset schema v3;
- allowlisted `of_absorption` / `of_exhaustion` research feature consumption;
- fail-closed behavior when the required physical v3 columns are unavailable;
- bounded research gates;
- deterministic directionality, boundary, zero/low-volume, replay/input-order and no-future-leakage coverage.

PR #59 merged as:

`a48fdb6a7845390cf3dcad9f5e649d4b716a12b1`

PR #60 moved the bounded Linode one-shot development proof to the absorption/exhaustion gate family while preserving prior Delta/CVD and stacked immutable reports. It also hardened external production proof so stale stacked evidence cannot satisfy this milestone.

PR #60 merged as:

`a49790838064769768fe4ca9fe500f6ed941ba82`

## Exact production proof

External proof run: `33081041663`

Completed: `2026-08-27T14:24:41Z`.

The proof verified exact server build:

`a49790838064769768fe4ca9fe500f6ed941ba82`

It also verified HTTPS, encrypted Binance Demo reconnect, Chart, Positions, Fast restart proof, terminal/evidence-complete M5 report, Frozen OOS closed and real execution locked.

Production report:

`/var/lib/eba-trader/research/evidence/m5-absorption-exhaustion-ablation-20260801T000000Z-20260801T040000Z.json`

Batch:

`abl_c9bf89e7fb1dd4971345d87d`

Workflow dataset:

`m5ds_eadc90a3c97b12f599de21fa`

Fixed development window remained unchanged:

`2026-08-01T00:00:00Z -> 2026-08-01T04:00:00Z`

## Candle-only baseline

The baseline reproduced the existing comparison result:

- total return: `-0.004244488397751933` (~`-0.42445%`)
- final equity: `9957.55511602248`
- trade count: `4`
- win rate: `0.25`
- max drawdown: `-0.004244488397751933`
- expectancy: `-10.611220994379892`
- total cost: `43.90484437829747`

## Absorption treatments

Thresholds `0.10` and `0.20` produced the same result in this fixed window:

- total return: `-0.0016739996904260313` (~`-0.16740%`)
- final equity: `9983.26000309574`
- trade count: `1`
- win rate: `0.0`
- max drawdown: `-0.0016739996904260313` (~`-0.16740%`)
- expectancy: `-16.739996904259897`
- total cost: `10.99299019778177`
- absolute baseline loss reduction: ~`60.56%`

Interpretation: absorption materially reduced exposure and absolute loss versus candle-only control, but the remaining trade lost. It was materially worse than prior Delta `0.2` and stacked threshold `1` on total return and expectancy.

## Exhaustion treatments

Thresholds `0.01` and `0.03` both produced:

- total return: `0.0`
- final equity: `10000.0`
- trade count: `0`
- win rate: `0.0`
- max drawdown: `0.0`
- expectancy: `0.0`
- total cost: `0.0`

Interpretation: these thresholds rejected every entry on this four-hour sample. A zero-trade result is **not evidence of profitable edge**; it only demonstrates that the gate is restrictive on this window. It must not be ranked as a winning strategy simply because it avoided the baseline loss.

## Comparison with earlier best development arms

- Prior Delta `0.2`: return ~`-0.12055%`, 2 trades, 50% win rate, expectancy `-6.0277`.
- Stacked threshold `1`: return ~`-0.12408%`, 2 trades, 50% win rate, expectancy `-6.2041`.
- Absorption `0.10/0.20`: return ~`-0.16740%`, 1 trade, 0% win rate, expectancy `-16.7400`.
- Exhaustion `0.01/0.03`: 0 trades; non-informative for profitability.

Delta `0.2` therefore remains the least-negative tested development arm on this fixed sample, but it is still negative-return/negative-expectancy and has no promotion authority.

## Conclusion

Absorption/exhaustion infrastructure is retained for future strategy combinations, but this isolated candidate family is closed without an edge claim. The next controlled M5 candidate is **price/delta divergence**: test whether price making a new local high/low while executed-flow delta fails to confirm adds information beyond the existing baseline/Delta/stacked/response features.

Frozen OOS remains locked. Real exchange execution remains locked.
