# M9 Book-Depth / Microstructure Edge Discovery Protocol

Status: `FROZEN_PREDECLARED_NOT_RUN`
Frozen date: 2026-08-21
Scope: BTCUSDT Spot outcome research using Binance USD-M `bookDepth` as development-only microstructure input.

## Purpose

M9 tests whether the M8-qualified Binance USD-M bookDepth archive contains a reproducible, cost-robust
short-horizon edge that is materially different from the rejected M5 price/volume and M7
funding/futures-threshold searches.

M9 is not a trading strategy, does not size risk, does not place orders, and does not use AI.

## Frozen data boundary

Discovery:
- `2023-01-01T00:00:00Z` to `2024-01-01T00:00:00Z` exclusive.

Reused development challenge:
- `2024-01-01T00:00:00Z` to `2025-01-01T00:00:00Z` exclusive.

Frozen OOS:
- `2025-01-01T00:00:00Z` to `2026-01-01T00:00:00Z`
- status: `LOCKED_NOT_ACCESSED`

2024 is not pristine OOS. It is only a reused development challenge because prior cycles have already
observed it.

## Frozen source inputs

Microstructure:
- Binance Vision USD-M daily `bookDepth/BTCUSDT`.
- Only 2023-01-01 through 2024-12-31 archives are permitted.
- Each present ZIP must match its official `.CHECKSUM`.
- Missing days stay missing; no forward fill or imputation is allowed.
- M8 established this fixed two-year family as `PARTIAL_WINDOW_ELIGIBLE`.

Outcome:
- existing frozen BTCUSDT Spot 15m cache.
- discovery source file: `data/cache/m2/btcusdt_15m_research.csv`
- challenge source file: `data/cache/m2/btcusdt_15m_validation.csv`
- the discovery loader must slice the research file to 2023 only.
- no 2025 file or request is permitted.

## Frozen book-depth feature construction

The archive has signed `percentage` rows in `{-5,-4,-3,-2,-1,1,2,3,4,5}` with `depth` and `notional`.

M9 deliberately does not reconstruct an implied market price from `notional/depth`. It uses only
same-snapshot, internally symmetric signed-side ratios.

Operational convention:
- negative-percentage rows are the negative side;
- positive-percentage rows are the positive side.

For each complete snapshot:
- `notional_1 = log(notional[-1] / notional[+1])`
- `notional_5 = log(notional[-5] / notional[+5])`
- `depth_1 = log(depth[-1] / depth[+1])`
- snapshot is unavailable if any required numerator/denominator is non-finite or <= 0.

For each completed UTC 15m signal bar ending at time `t`:
- use only complete snapshots with timestamp in `(t-15m, t]`;
- require at least 20 complete snapshots;
- require the latest accepted snapshot to be no more than 120 seconds stale at `t`;
- the raw 15m feature is the median of accepted snapshot values in that interval;
- a missing/invalid 15m feature is never forward-filled.

Standardization:
- rolling baseline = previous 96 contiguous available 15m feature bars, excluding the current bar;
- z-score uses sample mean and sample standard deviation of that prior window;
- if the previous 96 feature bars are not contiguous, the z-score is unavailable;
- zero standard deviation makes the z-score unavailable.

Change feature:
- `notional_1_change_4bar = current raw notional_1 - raw notional_1 four 15m bars earlier`;
- it also uses a previous-96 contiguous change-value z-score excluding the current change.

## Frozen candidate search space

Exactly 8 candidates:

1. `notional_1_negative_side_dominant`: `notional_1_z >= +1.50`, direction `+1`
2. `notional_1_positive_side_dominant`: `notional_1_z <= -1.50`, direction `-1`
3. `notional_5_negative_side_dominant`: `notional_5_z >= +1.50`, direction `+1`
4. `notional_5_positive_side_dominant`: `notional_5_z <= -1.50`, direction `-1`
5. `depth_1_negative_side_dominant`: `depth_1_z >= +1.50`, direction `+1`
6. `depth_1_positive_side_dominant`: `depth_1_z <= -1.50`, direction `-1`
7. `notional_1_imbalance_rising`: `notional_1_change_4bar_z >= +1.50`, direction `+1`
8. `notional_1_imbalance_falling`: `notional_1_change_4bar_z <= -1.50`, direction `-1`

No candidate, sign, threshold or feature may be added, removed or changed after the first evidence run.

## Event de-clustering

- Minimum cooldown: 4 completed 15m bars after an accepted event for the same candidate.
- A candidate may emit again only after that cooldown.
- No outcome information participates in event selection.

## Frozen forward-return horizons

Exactly:
- 4 bars = 1 hour
- 16 bars = 4 hours
- 48 bars = 12 hours

Total hypothesis tests: `8 × 3 = 24`.

Signal and execution semantics:
- signal exists only after the completed 15m signal close and completed microstructure interval;
- diagnostic entry = next available contiguous Spot 15m open;
- diagnostic exit = close of the horizon bar;
- any missing/non-contiguous Spot bar invalidates that event/horizon;
- outcome direction is multiplied by the predeclared candidate direction.

Direction `-1` is research-only downside evidence. If it survives, its classification is
`NO_TRADE_VETO_CANDIDATE`; it does not authorize short execution.

## Costs

Diagnostic round-trip cost assumptions:
- Base: 30 bps
- Severe: 70 bps

For every event:
- `base_net = signed_gross_return - 0.0030`
- `severe_net = signed_gross_return - 0.0070`

## Baseline

Each candidate/horizon is compared with unconditional same-direction Spot outcomes across all
microstructure-eligible signal timestamps in the same window.

Required candidate uplift over the same-direction baseline:
- at least 10 bps (`0.0010`) in discovery;
- at least 10 bps in the 2024 challenge.

## Statistical control

For each discovery candidate/horizon:
- aggregate event Base-net returns by UTC day;
- compute a one-sided positive-mean test from daily means;
- apply Benjamini-Hochberg FDR jointly across all 24 discovery tests;
- required `q <= 0.10`.

No FDR selection is rerun with a reduced subset after seeing results.

## Discovery gates

A candidate/horizon passes 2023 discovery only if all are true:
- at least 80 events;
- at least 40 distinct event days;
- mean Base-net > 0;
- mean Severe-net > 0;
- median Base-net > 0;
- baseline uplift >= 10 bps;
- BH-FDR q <= 0.10;
- at least 3 of the 4 UTC calendar quarters have:
  - at least 12 events,
  - positive mean Base-net,
  - baseline uplift >= 10 bps.

## Reused 2024 challenge gates

Evaluated only for candidate/horizons that passed every discovery gate.

PASS only if all are true:
- at least 50 events;
- at least 30 distinct event days;
- mean Base-net > 0;
- mean Severe-net > 0;
- median Base-net > 0;
- baseline uplift >= 10 bps;
- at least 3 of 4 UTC calendar quarters with at least 8 events have positive mean Base-net;
- at least 3 of 4 UTC calendar quarters with at least 8 events have positive baseline uplift.

## Classification

If discovery and challenge both pass for at least one horizon:
- direction `+1` -> `LONG_EDGE_CANDIDATE`
- direction `-1` -> `NO_TRADE_VETO_CANDIDATE`

Otherwise:
- `OBSERVATION_ONLY`

Cycle decision:
- any classified candidate -> `MICROSTRUCTURE_EDGE_CANDIDATES_FOUND`
- none -> `NO_STABLE_MICROSTRUCTURE_EDGE_FOUND`

A candidate classification is not a live-trading approval and not a strategy.

## Integrity / anti-overfit rules

- 2025 remains locked.
- Search parameters are immutable after the first complete evidence run.
- Record every one of the 24 tests, not only survivors.
- Do not rescue a rejected result by changing z thresholds, horizons, cooldown, costs, support gates or
  quarter gates.
- Do not silently substitute Bybit, paid vendor, liquidation, funding, premium-index or price-derived
  filters into M9.
- Do not add price-trend filters after seeing M9 results.
- No risk sizing, leverage, futures execution, short execution, AI routing or live order path is part
  of M9.
