# M5 Edge Discovery Protocol — Price/Volume V1

## Status

`FROZEN_PREDECLARED_SEARCH_SPACE`

This cycle does not define or backtest a trading strategy. It searches a finite, predeclared set of
BTCUSDT 15-minute price/volume event hypotheses for stable forward-return behavior. A discovered
event may later motivate a separate strategy hypothesis, but this engine cannot auto-promote,
retune, deploy, or trade anything.

## Information boundary

- Discovery window: `2021-01-01` through `2024-01-01` exclusive.
- Fixed challenge window: `2024-01-01` through `2025-01-01` exclusive.
- Frozen OOS: `2025-01-01` through `2026-01-01` exclusive.
- 2025 must not be downloaded, read, inferred from, or used by this cycle.
- Discovery ranking and multiple-testing correction use 2021–2023 only.
- 2024 is evaluated only after the discovery statistics for the frozen search space exist.
- The 2024 challenge is not pristine OOS because prior strategy development has already used
  aggregate 2024 information. It is a fixed development challenge, not final validation.
- AI, news, funding, basis, open interest, liquidations, order book, and discretionary labels are
  excluded from Price/Volume V1.

## Data

Frozen BTCUSDT Spot 15m development caches:

- `data/cache/m2/btcusdt_15m_research.csv`
- `data/cache/m2/btcusdt_15m_validation.csv`

The existing exact dataset SHA-256 values and Binance source-gap allowlist remain authoritative.
Unexpected gaps, timestamp corruption, OHLC corruption, hash mismatch, or holdout overlap fail closed.

## Causal event/return contract

Every event is identified at a completed 15m bar `t`.

- Event features use bar `t` and earlier completed bars only.
- The hypothetical forward entry reference is the next contiguous 15m open, `t+1`.
- Forward horizons are exactly 4, 16, and 48 completed 15m bars after the signal
  (approximately 1h, 4h, and 12h from the next-open entry).
- For horizon `H`, exit reference is the close of bar `t+H`.
- An observation is discarded if any source gap lies between the feature window, signal, entry,
  and required exit.
- A fixed event cooldown of 4 completed 15m bars suppresses repeated triggers from the same episode.
- This is an event study, not a fill-accurate trading backtest.

Signed gross forward return:

`direction * (exit_close / next_open - 1)`

where direction is `+1` for an expected upward edge and `-1` for an expected downward edge.

Negative-direction candidates are diagnostic `NO_TRADE`/risk-veto research only. They do not
authorize short selling.

## Cost stress

To ask whether an effect is economically large enough to survive simple execution friction, subtract
the same round-trip cost assumptions used in prior cycles:

- Base: 10 bps fee + 5 bps slippage per side = 30 bps round trip.
- Severe: 15 bps fee + 20 bps slippage per side = 70 bps round trip.

`net_signed_return = signed_gross_return - round_trip_cost`

This is a conservative research adjustment, not an exchange execution model.

## Frozen features

All rolling statistics exclude future data and require at least 96 contiguous completed 15m bars.

- `ret_1h = close_t / close[t-4] - 1`
- `ret_4h = close_t / close[t-16] - 1`
- ATR14 with Wilder smoothing
- prior rolling VWAP96 using typical price and base volume, excluding the current bar
- prior rolling median volume96, excluding the current bar
- `volume_ratio = volume_t / prior_median_volume96`
- `vwap_displacement_atr = (close_t - prior_vwap96) / ATR14`
- prior 20-bar high and low, excluding the current bar
- relative ATR = current `ATR14/close` divided by the prior 96-bar median `ATR14/close`

No indicator or threshold may be added after results are seen in this cycle.

## Frozen candidate search space

Exactly 24 event candidates are tested. No opposite-direction flip is permitted after results.

### A. Return impulse — 8 candidates

Expected continuation:

- 1h return >= +1.5%
- 1h return >= +2.5%
- 4h return >= +3.0%
- 4h return >= +5.0%

Expected downward continuation / long-veto diagnostics:

- 1h return <= -1.5%
- 1h return <= -2.5%
- 4h return <= -3.0%
- 4h return <= -5.0%

### B. Volume-confirmed impulse — 8 candidates

Expected continuation:

- 1h return >= +1.5% with volume ratio >= 1.5
- 1h return >= +1.5% with volume ratio >= 2.0
- 4h return >= +3.0% with volume ratio >= 1.5
- 4h return >= +3.0% with volume ratio >= 2.0

Expected downward continuation / long-veto diagnostics:

- 1h return <= -1.5% with volume ratio >= 1.5
- 1h return <= -1.5% with volume ratio >= 2.0
- 4h return <= -3.0% with volume ratio >= 1.5
- 4h return <= -3.0% with volume ratio >= 2.0

### C. VWAP displacement continuation — 4 candidates

- displacement >= +1.0 ATR, expected up
- displacement >= +2.0 ATR, expected up
- displacement <= -1.0 ATR, expected down / long-veto
- displacement <= -2.0 ATR, expected down / long-veto

### D. Compressed breakout — 4 candidates

Compression requires `relative_ATR <= 0.80`.

- close above prior 20-bar high and volume ratio >= 1.5, expected up
- close above prior 20-bar high and volume ratio >= 2.0, expected up
- close below prior 20-bar low and volume ratio >= 1.5, expected down / long-veto
- close below prior 20-bar low and volume ratio >= 2.0, expected down / long-veto

Total hypothesis tests for multiple-testing control:

`24 candidates * 3 horizons = 72 tests`

## Dependence and significance control

Event returns can be serially dependent. The engine therefore does not treat every 15m observation
as an independent statistical sample.

For each candidate/horizon:

1. group accepted event outcomes by UTC signal day;
2. compute the mean signed base-net return for each day;
3. require at least 20 distinct event days before significance can pass;
4. compute a one-sided normal-approximation p-value for positive mean daily return;
5. apply Benjamini-Hochberg false-discovery-rate correction across all 72 discovery tests;
6. use `q <= 0.10` as the predeclared discovery significance threshold.

The p/q values are screening evidence, not proof of future profitability.

## Discovery gates — 2021–2023 only

A candidate/horizon is `DISCOVERY_PASS` only if all are true:

1. at least 60 accepted events total;
2. at least 20 distinct UTC event days;
3. at least 10 events in each of 2021, 2022, and 2023;
4. mean base-net signed return > 0;
5. mean severe-net signed return > 0;
6. each of 2021, 2022, and 2023 has positive mean base-net signed return;
7. Benjamini-Hochberg `q <= 0.10`.

Failure of any item is a discovery failure for that candidate/horizon.

## Fixed 2024 challenge gates

A discovery-passing candidate/horizon is `CHALLENGE_PASS` only if all are true on 2024:

1. at least 15 accepted events;
2. mean base-net signed return > 0;
3. mean severe-net signed return > 0;
4. median base-net signed return > 0.

Candidates that fail discovery are still measured on 2024 for a complete audit, but cannot be
promoted because of a good 2024 result.

## Candidate classification

- `LONG_EDGE_CANDIDATE`: direction `+1`, and at least one horizon passes both discovery and challenge.
- `NO_TRADE_VETO_CANDIDATE`: direction `-1`, and at least one horizon passes both discovery and challenge.
- `OBSERVATION_ONLY`: no horizon passes both stages.

A candidate is stronger, but not automatically promotable, when two or more horizons pass.

No candidate can automatically become V4. A separate frozen strategy contract is required before
entry/exit/risk rules may be tested.

## Anti-overfitting rules

After the first complete M5 report:

- do not change thresholds inside this frozen 24-candidate set and rerun it as if unchanged;
- do not flip a failed candidate's expected direction because the observed sign was opposite;
- do not select a new horizon from the same report;
- do not add a filter to rescue a candidate;
- do not call the 2024 challenge pristine OOS;
- do not open 2025.

A materially new search family requires a new protocol/version and must preserve the full M5 result.

## Required report

The JSON report must include:

- source and Git provenance;
- exact data boundaries and hashes;
- all 24 candidate definitions;
- all 72 discovery horizon results;
- all 72 challenge horizon results;
- event counts, distinct days, mean/median/win rate;
- base and severe net signed returns;
- yearly discovery breakdown;
- p-values and FDR q-values;
- discovery/challenge gate booleans;
- final candidate classification;
- explicit `oos_2025 = LOCKED_NOT_ACCESSED`.

The engine must report `NO_STABLE_EDGE_FOUND` when nothing qualifies. That is a valid result.
