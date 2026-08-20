# V3 — Bull Pullback Recovery Hypothesis

## Status and information boundary

`FROZEN_PREDECLARED_NOT_BACKTESTED`

This document defines a materially new BTCUSDT Spot strategy family after Trend V1 and Trend V2
both failed development. The purpose is to test a bull-regime pullback-recovery continuation edge,
not to rescue or retune either failed trend cycle.

- Development data only: BTCUSDT Spot, 2021-01-01 through 2025-01-01 exclusive.
- Research: 2021-01-01 through 2024-01-01 exclusive.
- Reused development validation: 2024-01-01 through 2025-01-01 exclusive.
- Frozen OOS: 2025-01-01 through 2026-01-01 exclusive; do not download or inspect.
- Long-only Spot, no leverage, no short selling, one position maximum.
- Normalized signal/allocation equity: $1,000.
- AI, news, funding, basis, open interest, liquidation feeds, and discretionary overrides are excluded.
- Once implementation begins, baseline parameters and gates below are immutable for this cycle.

The 2024 window is not pristine because aggregate V1/V2 development results are known. It remains
the fixed development-validation segment. Only 2025 remains the procedural holdout.

## Why V3 is materially different

Trend V1 bought an EMA crossover. Trend V2 bought a fresh breakout in a filtered bull regime.
Both lost money in development. V3 does not buy a breakout or an EMA crossover.

V3 asks a different question:

> During an established higher-timeframe bull regime, does a temporary intraday pullback followed
> by a causal price-and-volume recovery create positive continuation expectancy after costs?

The strategy is deliberately long-only and selective. It first waits for a pullback below a rolling
24-hour volume-weighted anchor, then requires recovery evidence before entering.

## Research rationale, not a profit claim

Published cryptocurrency reversal research documents short-horizon reversals across broad coin
panels, but also reports that reversal is strongest in smaller and less-liquid coins while the largest,
most-tradeable coins can exhibit momentum instead. That is a caution against a pure BTC reversal
strategy, not evidence that this rule works.

V3 therefore combines:
1. a higher-timeframe bull-regime requirement;
2. a bounded pullback rather than an extreme crash;
3. a recovery confirmation before entry;
4. fixed risk and time exits.

Primary references used only as hypothesis context:
- Kozlowski, Puleo and Zhou, *Cryptocurrency Return Reversals*, Applied Economics Letters 28(11),
  887-893.
- Zaremba et al., *Up or down? Short-term reversal, momentum, and liquidity effects in
  cryptocurrency markets*, International Review of Financial Analysis 78, 101908.

Neither paper establishes a BTCUSDT 15-minute edge.

## Causal data contract

All decisions use completed candles only. A signal generated at a completed 15m close can execute
only at the next available 15m open.

### 4h regime construction

- Build 4h bars from sixteen UTC-aligned 15m source bars.
- An incomplete 4h bar is invalid and is not supplied to regime indicators.
- At a 15m signal close, use only the most recent fully completed 4h bar.
- After an unapproved source gap, the study fails closed.
- After a preapproved historical source gap, new entries remain disabled until sixteen consecutive
  complete 15m bars rebuild one complete 4h bar and all rolling entry statistics are valid again.
- EMA uses `alpha = 2 / (period + 1)`.

### 15m indicators

- ATR14 uses Wilder smoothing.
- Typical price = `(high + low + close) / 3`.
- Rolling VWAP96 = `sum(typical_price * base_volume) / sum(base_volume)` over the previous
  96 completed 15m bars, excluding the current signal bar from the anchor.
- Rolling median volume96 uses the previous 96 completed 15m bars, excluding the current bar.
- All rolling values use past completed data only.

### Warm-up

Trading begins only after all of the following exist:
- 200 completed valid 4h bars for the slow regime EMA;
- 6 additional completed 4h bars for the 24h slow-EMA slope comparison;
- 96 prior completed 15m bars for VWAP and median volume;
- ATR14 and all entry-state variables are fully warmed.

Warm-up bars do not contribute trades, exposure, strategy equity, or benchmark performance.

## Frozen baseline parameters

| Layer | Parameter | Baseline |
|---|---|---:|
| Regime | 4h fast EMA | 50 |
| Regime | 4h slow EMA | 200 |
| Regime | slow-EMA slope lookback | 6 completed 4h bars |
| Pullback | 15m ATR period | 14 |
| Pullback | rolling VWAP window | 96 prior 15m bars |
| Pullback | minimum depth | 0.75 ATR below prior VWAP |
| Pullback | maximum depth | 2.25 ATR below prior VWAP |
| Pullback | maximum arm lifetime | 8 completed 15m bars |
| Recovery | local high lookback | 3 prior 15m bars |
| Recovery | minimum volume ratio | 1.00 × prior 96-bar median volume |
| Recovery | favorable entry-gap cap | 0.50 × signal ATR |
| Initial stop | swing-low buffer | 0.25 × signal ATR |
| Initial stop | minimum distance | 0.75 ATR |
| Initial stop | maximum distance | 3.00 ATR |
| Profit exit | fixed target | 2.00 R |
| Time exit | maximum holding period | 24 completed 15m bars |
| Re-entry | cooldown after any exit | 4 completed 15m bars |

## Bull-regime rule

The most recent completed 4h bar is `BULL_REGIME` only when all are true:

1. `close_4h > EMA200_4h`;
2. `EMA50_4h > EMA200_4h`;
3. `EMA200_4h(t) > EMA200_4h(t-6)`.

Otherwise V3 cannot arm or enter a new position. An open position is not force-exited from one
temporary regime failure; the normal regime exit below governs open trades.

## Pullback arming rule

With no position open and cooldown complete, V3 becomes `ARMED` only when all are true on the same
completed 15m bar:

1. the completed 4h regime is `BULL_REGIME`;
2. source/data health is valid;
3. `signal_atr > 0`;
4. the bar close is below the prior rolling VWAP96;
5. `pullback_depth = (prior_vwap96 - close) / ATR14` satisfies
   `0.75 <= pullback_depth <= 2.25`;
6. current 15m true range is not greater than `3.0 * ATR14`;
7. current bar volume is positive.

The arm records:
- `arm_time`;
- `arm_vwap`;
- `arm_atr`;
- `pullback_low`, initialized to the arm-bar low.

While armed:
- update `pullback_low` with each completed 15m low;
- expire the setup after 8 completed 15m bars without a valid recovery;
- cancel immediately if the completed 4h bull regime becomes invalid;
- cancel if source/data health becomes invalid;
- do not re-arm from a deeper bar until the current arm either expires or cancels.

## Recovery entry rule

A long proposal exists only when an active, unexpired arm exists and every condition below is true
on the same completed 15m signal bar:

1. completed 4h regime remains `BULL_REGIME`;
2. `close_t > max(high[t-3:t])`, using only the three bars before `t`;
3. `close_t > open_t`;
4. `volume_t >= prior_median_volume96`;
5. `close_t > prior_vwap96 - 0.25 * ATR14`;
6. `low_t > pullback_low` is not required; the recovery may retest the pullback low, but the close
   must satisfy all recovery conditions;
7. no cooldown, stale-data, source-gap, or execution-health veto is active.

The entry reference is the next 15m open. Cancel the entry and record `NO_TRADE` when:
- next open is above `signal_close + 0.50 * signal_ATR`;
- next open is at or below the planned initial stop;
- the completed 4h regime is invalid before execution;
- source/data/execution health becomes invalid;
- Spot cash, fee, minimum-size, or risk constraints cannot be satisfied.

## Stop and exit contract

### Initial stop

At signal time:

`raw_stop = pullback_low - 0.25 * signal_ATR`

At actual entry:

`stop_distance = entry_price - raw_stop`

The order is rejected if `stop_distance < 0.75 * signal_ATR` or
`stop_distance > 3.00 * signal_ATR`.

If accepted:
- active stop = `raw_stop`;
- initial risk unit `R = entry_price - active_stop`;
- fixed profit target = `entry_price + 2.00 * R`.

### Exit order

For each bar after entry:

1. If bar open is at or below active stop, exit at bar open.
2. Else if bar open is at or above profit target, exit at bar open.
3. Else if both stop and target lie inside the same bar range, use the conservative stop-first
   assumption.
4. Else if low touches stop, exit at stop.
5. Else if high touches target, exit at target.
6. Else, if 24 completed 15m bars have elapsed since entry, exit at the next 15m open.
7. Else, if two consecutive completed 4h bars fail the bull-regime rule, exit at the next 15m open.

There is no trailing stop, partial take-profit, pyramiding, averaging down, martingale, or
discretionary exit in the baseline cycle.

## Frozen risk and cost assumptions

Signal/allocation diagnostics use normalized $1,000 equity and a single all-cash position subject to
fees and available cash. This layer tests the signal family before risk sizing.

The separately gated risk-sized layer uses:
- planned risk per trade: 0.35% of current equity;
- maximum invested notional including entry fee: 50% of current equity;
- maximum open positions: one;
- daily realized-loss entry halt: 1.50% of start-of-day UTC equity;
- hard mark-to-market drawdown entry halt: 8.00%;
- leverage, shorting, pyramiding, martingale, and averaging down: forbidden.

Cost scenarios remain unchanged from V2:

| Scenario | Fee / side | Slippage / side |
|---|---:|---:|
| Base | 10 bps | 5 bps |
| Adverse | 10 bps | 10 bps |
| Severe | 15 bps | 20 bps |

## Required controls

Report V3 alongside:
1. BTC buy-and-hold over the identical evaluation boundary;
2. cash / `NO_TRADE`;
3. frozen Trend V1 and Trend V2 validation results for historical context only;
4. a `REGIME_ONLY_RECOVERY_CONTROL` that uses the same 4h bull regime, recovery trigger, stop,
   target, time exit, and costs, but does not require the bounded VWAP pullback depth or volume
   confirmation.

The control cannot replace V3 and cannot be used as a tuning path.

## Predeclared development gates

V3 passes development only if every applicable gate passes. Null metrics, invariant violations,
policy mismatch, data-integrity failure, or a zero-trade fold where a positive metric is required
count as failure.

### A. Signal/allocation validation — 2024

1. At least 25 closed trades.
2. Base-cost total return > 0.
3. Base-cost expectancy > 0 USD per closed trade.
4. Base-cost profit factor >= 1.15.
5. Severe-cost total return > 0.
6. Severe-cost expectancy > 0.
7. Maximum-drawdown magnitude <= 20%.
8. Time exposure <= 40%.
9. If return is below BTC buy-and-hold, strategy drawdown magnitude must be <= 60% of BTC drawdown.
10. Entry/exit/data invariant violations = 0.

### B. Added-value control — 2024

Relative to `REGIME_ONLY_RECOVERY_CONTROL` under base costs:
11. V3 expectancy must be strictly higher.
12. V3 profit factor must be no worse.
13. V3 maximum-drawdown magnitude must be no worse.
14. V3 total trading cost must be no higher.

### C. Parameter robustness — research window only

Evaluate exactly nine configurations. The baseline remains frozen and variants are diagnostic only:

1. frozen baseline;
2. minimum pullback depth = 0.50 ATR;
3. minimum pullback depth = 1.00 ATR;
4. maximum pullback depth = 1.75 ATR;
5. maximum pullback depth = 2.75 ATR;
6. recovery local-high lookback = 2 bars;
7. recovery local-high lookback = 4 bars;
8. fixed profit target = 1.50 R;
9. fixed profit target = 2.50 R.

All unspecified values remain frozen.

Required:
15. At least 6 of 9 variants have positive base-cost expectancy.
16. At least 6 of 9 variants have base-cost profit factor > 1.0.
17. At least 5 of 9 variants have positive severe-cost expectancy.

No variant may replace the frozen baseline after results are observed.

### D. Rolling temporal stability — research window only

Use fixed baseline parameters with 180-day context, 30-day test windows, and 30-day steps.
Context may warm indicators; performance begins at each unseen test boundary.

18. At least 80% of folds contain one or more closed trades.
19. At least 60% of all folds have positive total return.
20. At least 60% of all folds have positive expectancy.
21. At least 60% of all folds have profit factor > 1.0.

### E. Risk-sized execution — 2024

Run only after A-D all pass.

22. At least 25 closed trades.
23. Base-cost total return > 0.
24. Base-cost expectancy > 0.
25. Base-cost profit factor >= 1.10.
26. Maximum planned risk per trade <= 0.35% of equity.
27. Invested notional including entry fee <= 50% of equity.
28. Base run never reaches the 8% hard drawdown halt.
29. Base maximum drawdown remains strictly above -8%.
30. Severe-cost total return > 0.
31. Severe-cost expectancy > 0.
32. Severe-cost profit factor > 1.0.
33. Severe run never reaches the 8% hard drawdown halt.
34. No entry occurs during a daily-loss halt, source-gap cooldown, stale-data state, invalid regime,
    or other hard veto.

## Decision policy

- All A-D gates pass: eligible to run the separately gated risk-sized layer.
- Any A-D gate fails: `REJECT_V3_SIGNAL_CYCLE`; do not run risk evidence for promotion.
- All A-E gates pass: `ELIGIBLE_FOR_V3_FINAL_FREEZE_REVIEW`, not automatic freeze.
- Any E gate fails: `REJECT_V3_EXECUTION_CYCLE`.
- Any rejection leaves 2025 OOS locked.
- Do not rescue a rejected cycle by choosing a better neighborhood value, weakening a threshold,
  changing the evaluation boundary, or adding AI/news/funding after seeing the result.
- Even a development pass does not authorize PAPER, SHADOW, MICRO_LIVE, leverage, or real money.

## Implementation order

1. Freeze this exact document by SHA-256 and record the base Git commit.
2. Add a pure policy/constants module.
3. Add deterministic 4h resampling, EMA, ATR, rolling VWAP, median-volume, arm/recovery state tests.
4. Add causal next-open entry, gap cancel, stop/target ambiguity, time exit, regime exit, source-gap
   cooldown, and control-strategy tests.
5. Add signal evidence, robustness, rolling-fold, and verdict code.
6. Run full deterministic pytest and Ruff.
7. Only then run V3 on cached 2021–2024 development data.
8. Do not access 2025 OOS.
