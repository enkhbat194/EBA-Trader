# M12 Cross-Asset ETH→BTC Edge Discovery Protocol

Status: `FROZEN_PREDECLARED_NOT_RUN`
Date: 2026-08-21

## Purpose

M12 tests whether previously data-qualified ETHUSDT USD-M perpetual market states contain causal,
cost-robust information about later BTCUSDT Spot returns. This is an event study only. It does not
authorize a strategy, risk sizing, short execution, AI signals, or live trading.

M12 is materially different from M5/M7/M9 because the predictive input is an external ETH derivatives
market. The BTC market remains the outcome/execution reference.

## Data boundary

Discovery:
`2021-01-01T00:00:00Z` through `2024-01-01T00:00:00Z` exclusive.

Reused development challenge:
`2024-01-01T00:00:00Z` through `2025-01-01T00:00:00Z` exclusive.

True OOS:
`2025-01-01T00:00:00Z` through `2026-01-01T00:00:00Z` exclusive remains
`LOCKED_NOT_ACCESSED`.

2024 is not pristine OOS.

## Frozen inputs

ETH input:
- provider: Binance Vision;
- market: USD-M perpetual futures;
- symbol: ETHUSDT;
- interval: 15m;
- qualified by M11;
- normalized 2021-2024 SHA-256:
  `69855dcaf2f34c2a529ddb7f83964fa61b39ed0a27ae8796a6c0eaafd5b744f5`.

BTC outcomes:
- BTCUSDT Spot 15m research 2021-2023 SHA-256:
  `253c6ae35856e58e35df17eaa71caeea5caaa3681c38dd7214a2872afccd8d63`;
- BTCUSDT Spot 15m reused challenge 2024 SHA-256:
  `3a96b6b668cfacb0fefabb8665675d4ca589cc712b0681fb57e7a13356eda0f2`.

No M10 ETH Spot data is admitted.

## Causal timing

An event is identified only after the ETH and BTC 15m bars at signal time `t` are complete.
Features use `t` and earlier only.

The hypothetical BTC entry reference is the next contiguous 15m open, `t+1`.

Forward horizons are exactly:
- 4 bars ≈ 1 hour;
- 16 bars ≈ 4 hours;
- 48 bars ≈ 12 hours.

For horizon `H`, exit is BTC close at bar `t+H`.

Any event is discarded if the required ETH feature window or BTC signal→entry→exit path is not
15-minute contiguous. Event cooldown is 4 bars.

## Frozen features

At completed bar `t`:

- `eth_ret_1h = ETH_close[t] / ETH_close[t-4] - 1`;
- `eth_ret_4h = ETH_close[t] / ETH_close[t-16] - 1`;
- `btc_ret_1h = BTC_close[t] / BTC_close[t-4] - 1`;
- `eth_minus_btc_1h = eth_ret_1h - btc_ret_1h`.

ETH one-hour flow uses the four completed ETH bars ending at `t`:
- `taker_buy_share_1h = sum(taker_buy_base_volume) / sum(base_volume)`;
- `quote_volume_1h = sum(quote_volume)`.

`quote_volume_intensity_1h` is current `quote_volume_1h` divided by the median of the prior
96 completed one-hour rolling totals, excluding the current total. No future value may enter the
baseline.

## Frozen candidate search space

Exactly eight candidates are allowed.

1. `eth_1h_up_1_5`
   - condition: `eth_ret_1h >= +1.5%`
   - expected BTC direction: +1.

2. `eth_1h_down_1_5`
   - condition: `eth_ret_1h <= -1.5%`
   - expected BTC direction: -1 diagnostic / no-trade veto only.

3. `eth_4h_up_3`
   - condition: `eth_ret_4h >= +3.0%`
   - expected BTC direction: +1.

4. `eth_4h_down_3`
   - condition: `eth_ret_4h <= -3.0%`
   - expected BTC direction: -1 diagnostic / no-trade veto only.

5. `eth_relative_1h_outperform_1`
   - condition: `eth_minus_btc_1h >= +1.0%`
   - expected BTC direction: +1.

6. `eth_relative_1h_underperform_1`
   - condition: `eth_minus_btc_1h <= -1.0%`
   - expected BTC direction: -1 diagnostic / no-trade veto only.

7. `eth_flow_1h_up_buy_confirm`
   - conditions:
     - `eth_ret_1h >= +1.5%`;
     - `taker_buy_share_1h >= 0.55`;
     - `quote_volume_intensity_1h >= 1.25`;
   - expected BTC direction: +1.

8. `eth_flow_1h_down_sell_confirm`
   - conditions:
     - `eth_ret_1h <= -1.5%`;
     - `taker_buy_share_1h <= 0.45`;
     - `quote_volume_intensity_1h >= 1.25`;
   - expected BTC direction: -1 diagnostic / no-trade veto only.

Candidate sign reversal after results is forbidden.

## Costs and baseline

Signed gross BTC forward return:
`direction * (BTC_exit_close / BTC_next_open - 1)`.

Base round-trip screening cost: 30 bps.
Severe round-trip screening cost: 70 bps.

Net signed return subtracts the applicable round-trip cost.

Each candidate/horizon also compares against the same-direction unconditional BTC Spot forward-return
baseline over the same window. Required baseline uplift is at least +10 bps.

A negative direction never grants short authority.

## Dependence and multiple testing

There are exactly `8 × 3 = 24` discovery hypotheses.

For significance screening, accepted event base-net returns are aggregated by UTC signal day and the
daily mean is used for a one-sided normal-approximation p-value for positive mean return.

At least 20 distinct event days are required for significance.

Benjamini-Hochberg FDR is applied across all 24 discovery tests with `q <= 0.10`.

P-values and q-values are screening evidence, not proof.

## Discovery gates: 2021-2023

A candidate/horizon must pass all of:

1. at least 60 accepted events;
2. at least 20 distinct UTC event days;
3. at least 10 accepted events in each of 2021, 2022 and 2023;
4. mean Base-net signed return > 0;
5. mean Severe-net signed return > 0;
6. median Base-net signed return > 0;
7. same-direction unconditional BTC baseline uplift >= +10 bps;
8. each of 2021, 2022 and 2023 has positive mean Base-net signed return;
9. each year has non-negative baseline uplift;
10. BH-FDR q <= 0.10.

All ten are required.

## Reused-2024 challenge gates

Challenge gates are promotion gates only for candidate/horizons that passed discovery.
All candidate/horizons may still be measured for audit.

Required:
1. at least 15 events;
2. mean Base-net signed return > 0;
3. mean Severe-net signed return > 0;
4. median Base-net signed return > 0;
5. same-direction unconditional BTC baseline uplift >= +10 bps.

All five are required.

## Classification

If at least one horizon passes both discovery and challenge:
- direction +1 → `LONG_EDGE_CANDIDATE`;
- direction -1 → `NO_TRADE_VETO_CANDIDATE`.

Otherwise → `OBSERVATION_ONLY`.

If no candidate is promoted, decision is `NO_STABLE_CROSS_ASSET_EDGE_FOUND`.

If one or more candidates are promoted, decision is
`CROSS_ASSET_EDGE_CANDIDATE_FOUND_REQUIRES_NEW_STRATEGY_FREEZE`.

No M12 result automatically becomes a strategy.

## Anti-overfit stop rules

After the first complete M12 report:
- no threshold tuning;
- no sign flipping;
- no new horizon;
- no rescue filter;
- no dropping failed years;
- no reclassifying 2024 as pristine OOS;
- no opening 2025;
- no substituting failed M10 ETH Spot history;
- no generating a strategy from an observation-only candidate.

A materially changed cross-asset family requires a new versioned research cycle.

AI module: excluded.
Strategy generation: forbidden.
Risk sizing: forbidden.
Live execution: forbidden.
2025 OOS: `LOCKED_NOT_ACCESSED`.
