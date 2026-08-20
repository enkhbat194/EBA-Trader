# M7 Funding + Futures Activity Edge Discovery Protocol

Status: `FROZEN_PREDECLARED_NOT_RUN`
Frozen date: 2026-08-21

## Purpose

M7 tests whether derivatives-native information that passed the M6 historical data audit predicts
subsequent BTCUSDT Spot returns strongly enough to survive costs, multiple-testing control, temporal
stability, and a fixed reused 2024 development challenge.

M7 is edge discovery, not a trading strategy. A surviving edge may justify a later separately frozen
strategy contract; it does not authorize trading.

## Data boundary

Discovery:
- `2021-01-01T00:00:00Z` to `2024-01-01T00:00:00Z` exclusive.

Reused development challenge:
- `2024-01-01T00:00:00Z` to `2025-01-01T00:00:00Z` exclusive.
- 2024 is not pristine OOS.

Frozen holdout:
- `2025-01-01T00:00:00Z` to `2026-01-01T00:00:00Z`
- status: `LOCKED_NOT_ACCESSED`

## Frozen source families

Predictors:
1. M6-PASS Binance USD-M BTCUSDT funding history.
2. M6-PASS Binance USD-M BTCUSDT perpetual 15m klines and activity fields:
   - OHLC
   - base volume
   - quote volume
   - trade count
   - taker-buy base volume
   - taker-buy quote volume

Outcome:
3. Existing frozen Binance BTCUSDT Spot 15m development datasets used in M2-M5.

Excluded:
- M6-failed premium-index data
- M6-failed index-price data
- REST open-interest history
- REST basis history
- liquidation history
- order-book history
- news/macro
- AI features

All input hashes must match their frozen values before any candidate result is computed.

## Causal timing

All predictor values must be known by the completed 15m signal close.

Spot outcome measurement:
- signal is observed at a completed 15m close;
- hypothetical entry is the next available contiguous Spot 15m open;
- exit is the Spot close after the frozen horizon;
- no outcome may cross a Spot source gap;
- no signal may use predictor data from after the signal close.

Funding timing:
- a funding record becomes usable only at or after its published `fundingTime`;
- pure-funding candidates signal at the close of the 15m futures bar containing the funding timestamp;
- funding-flow interaction candidates wait for four completed 15m futures bars beginning with the
  funding-containing bar, then signal at the fourth bar close;
- one funding record can create at most one pure-funding event and one interaction event per frozen
  candidate.

## Frozen features

### Funding percentile state

For a funding event, compute q10 and q90 from the previous **270 funding records**, excluding the
current record, using deterministic linear-interpolated percentiles over the sorted prior values.

An extreme-negative funding event requires:
- current funding rate < 0; and
- current funding rate <= prior q10.

An extreme-positive funding event requires:
- current funding rate > 0; and
- current funding rate >= prior q90.

Funding events without 270 prior records are ineligible.

### Futures taker-buy share

For a completed futures window:

`taker_buy_share = sum(taker_buy_base_volume) / sum(base_volume)`

The denominator must be positive and all activity fields must be valid.

### Futures activity intensity

For each 15m bar define rolling window totals for quote volume and trade count. For a 1h signal use
the four bars ending at the signal bar. For a 4h signal use the sixteen bars ending at the signal bar.

For each window length, the activity baseline is the median of the previous **96 completed rolling
window totals**, excluding the current rolling window total.

`quote_volume_intensity = current_window_quote_volume / prior_median_window_quote_volume`

`trade_count_intensity = current_window_trade_count / prior_median_window_trade_count`

The corresponding prior median must be positive.

### Futures price reaction

For a 1h window:

`futures_return_1h = signal_close / open_of_first_bar_in_4_bar_window - 1`

A price-neutral 1h window requires `abs(futures_return_1h) <= 0.005`.

## Frozen candidates

Exactly 12 candidates are tested.

Pure funding:
1. `funding_extreme_negative` — direction +1; extreme-negative funding event.
2. `funding_extreme_positive` — direction -1; extreme-positive funding event.

1h flow continuation:
3. `flow_1h_buy_vol_1_5` — direction +1; 1h taker-buy share >= 0.55 and quote-volume intensity >= 1.50.
4. `flow_1h_sell_vol_1_5` — direction -1; 1h taker-buy share <= 0.45 and quote-volume intensity >= 1.50.

4h flow continuation:
5. `flow_4h_buy_vol_1_25` — direction +1; 4h taker-buy share >= 0.53 and quote-volume intensity >= 1.25.
6. `flow_4h_sell_vol_1_25` — direction -1; 4h taker-buy share <= 0.47 and quote-volume intensity >= 1.25.

Price-neutral 1h flow:
7. `neutral_flow_1h_buy` — direction +1; abs 1h futures return <= 0.50%, 1h taker-buy share >= 0.55,
   quote-volume intensity >= 1.25, and trade-count intensity >= 1.25.
8. `neutral_flow_1h_sell` — direction -1; abs 1h futures return <= 0.50%, 1h taker-buy share <= 0.45,
   quote-volume intensity >= 1.25, and trade-count intensity >= 1.25.

Funding × post-funding 1h flow interactions:
9. `funding_negative_post_buy` — direction +1; extreme-negative funding and post-funding 1h
   taker-buy share >= 0.55.
10. `funding_negative_post_sell` — direction -1; extreme-negative funding and post-funding 1h
    taker-buy share <= 0.45.
11. `funding_positive_post_buy` — direction +1; extreme-positive funding and post-funding 1h
    taker-buy share >= 0.55.
12. `funding_positive_post_sell` — direction -1; extreme-positive funding and post-funding 1h
    taker-buy share <= 0.45.

No threshold or candidate may be added, removed, inverted, or changed after the first complete M7 run.

## Event de-duplication

Flow-only candidates use a 4 completed-bar cooldown after an accepted event for the same candidate.

Funding candidates are naturally event-based and accept at most one event per funding record.

## Frozen forward horizons

Each candidate is measured at exactly:
- 4 bars = 1 hour
- 16 bars = 4 hours
- 48 bars = 12 hours

Total frozen discovery hypothesis tests: **12 × 3 = 36**.

## Direction semantics

Direction +1 measures subsequent Spot long return.

Direction -1 measures the negative of subsequent Spot long return. A passing direction -1 result may
only become a future `NO_TRADE_VETO_CANDIDATE`; it never authorizes short execution.

## Cost stress

Research friction is subtracted from every direction-signed outcome:
- Base: 30 bps round trip
- Severe: 70 bps round trip

These are research screening costs, not a promise of actual execution cost.

## Directional baseline control

For each horizon and direction, calculate an unconditional directional Spot baseline over all eligible
completed signal bars in the same window using the same next-open outcome semantics.

A candidate must exceed its same-direction baseline mean Base-net return by at least **10 bps
(0.0010)** in addition to being economically positive. This prevents ordinary BTC drift from being
mistaken for derivatives information.

For yearly discovery stability, the same 10 bps uplift requirement is applied versus that year's
same-direction baseline.

## Discovery gates — 2021-2023

A candidate-horizon passes discovery only if all are true:
- at least 60 accepted events;
- at least 20 distinct UTC event days;
- at least 10 events in each of 2021, 2022, and 2023;
- mean Base-net direction-signed return > 0;
- mean Severe-net direction-signed return > 0;
- median Base-net direction-signed return > 0;
- mean Base-net return exceeds the same-direction unconditional baseline by >= 10 bps;
- each of 2021, 2022, 2023 has mean Base-net return > 0 and >=10 bps above that year's baseline;
- one-sided significance is computed on UTC daily mean Base-net outcomes;
- Benjamini-Hochberg FDR correction is applied across all 36 discovery tests;
- FDR q-value <= 0.10.

## Reused 2024 development challenge

The 2024 challenge is evaluated only for a candidate-horizon that passed every discovery gate.

It passes only if all are true:
- at least 15 events;
- mean Base-net return > 0;
- mean Severe-net return > 0;
- median Base-net return > 0;
- mean Base-net return exceeds the same-direction 2024 baseline by >= 10 bps.

## Classification and decision

If a direction +1 candidate-horizon passes discovery and 2024 challenge, its candidate class is
`LONG_EDGE_CANDIDATE`.

If a direction -1 candidate-horizon passes both, its candidate class is
`NO_TRADE_VETO_CANDIDATE`.

If no candidate-horizon passes both, M7 decision is:
`NO_STABLE_DERIVATIVES_EDGE_FOUND`.

If at least one passes both, M7 decision is:
`DERIVATIVES_EDGE_CANDIDATES_FOUND`.

Even a positive M7 result is only eligibility for a separate frozen strategy hypothesis. It does not
authorize paper/live trading and does not unlock 2025.

## Forbidden after first complete run

- changing candidate definitions or thresholds;
- adding an inverse candidate because a frozen candidate failed;
- weakening event counts, FDR, baseline uplift, costs, or challenge gates;
- introducing premium/index/OI/basis data after seeing M7 results;
- generating a strategy automatically from an observation;
- opening 2025 OOS.
