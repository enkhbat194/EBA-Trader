# Trend V2 — Regime-Filtered Volatility-Aware Breakout Hypothesis

## Status and information boundary

`FROZEN_PREDECLARED_NOT_BACKTESTED`

This document defines the hypothesis before Trend V2 code or evidence is run. Its final review
resolved execution and evaluation ambiguities. After the accompanying freeze manifest is created,
any content change invalidates this cycle's freeze and requires an explicit new policy version.

- Development data only: BTCUSDT Spot, 2021-01-01 through 2025-01-01 exclusive.
- Research: 2021-01-01 through 2024-01-01 exclusive.
- Reused development validation: 2024-01-01 through 2025-01-01 exclusive.
- Frozen OOS: 2025-01-01 through 2026-01-01 exclusive; do not download or inspect.
- Long-only Spot, no leverage, no short selling, one position maximum.
- Normalized research equity: $1,000.

The 2024 window is not claimed to be pristine: aggregate Trend V1 results are already known. It
remains a fixed development-validation segment for V2. Only 2025 remains the procedural holdout.

## V1 diagnosis

Trend V1 used a strict EMA 20/50 crossover as both the market-selection and entry mechanism. It
traded 337 times in 2024 but produced -45.07% base return, negative expectancy, profit factor 0.770,
and -85.74% severe-cost return. The V2 hypothesis is that V1 repeatedly entered weak, sideways, or
volatility-shock conditions where a short-horizon EMA crossover had no durable directional edge.

Trend V2 is materially different:

1. a completed 1h regime determines whether long Trend trades are eligible;
2. 1h ADX/+DI/-DI measures trend strength and direction;
3. adaptive 15m ATR filtering rejects both quiet noise and volatility shocks;
4. a fresh 15m price breakout—not an EMA crossover—triggers entry;
5. EMA alignment is only supporting context and an exit condition;
6. risk-sized execution uses an ATR stop, ratcheting trailing stop, and a 50% Spot notional cap.

## Research rationale, not a profit claim

Published trend-following research supports testing persistent directional signals across many
markets and horizons, but it does not establish that this BTC/15m rule has an edge. Volatility
management research supports testing lower exposure in high-volatility states, but applying that
idea as an entry veto here is an inference that must earn its own evidence.

Primary references:

- Hurst, Ooi and Pedersen, [A Century of Evidence on Trend-Following Investing](https://www.aqr.com/insights/research/journal-article/a-century-of-evidence-on-trend-following-investing).
- Moreira and Muir, [Volatility Managed Portfolios](https://www.nber.org/papers/w22208).

## Causal data and indicator contract

All calculations use completed candles only. A signal generated at a 15m close may execute only at
the next available 15m open.

### Multi-timeframe construction

- Build 1h bars from four UTC-aligned 15m source bars.
- An incomplete 1h bar is invalid and is not supplied to indicators.
- After a source gap, entries remain disabled until four consecutive complete 1h bars exist.
- At a 15m signal close, use only the most recent fully completed 1h bar.
- EMA uses `alpha = 2 / (period + 1)`.
- ATR, +DI, -DI and ADX use Wilder smoothing with period 14.
- All rolling thresholds exclude future bars; the volatility median excludes the current bar.
- Indicator state advances across complete bars only; an invalid 1h bar neither updates nor resets
  EMA/ADX state.

### Warm-up

Trading begins only when all of the following exist:

- 200 completed valid 1h bars for the slow regime EMA;
- 24 additional 1h bars for the slow-EMA slope comparison;
- 2,880 prior completed 15m bars (30 days) for the volatility median;
- all 15m entry and stop indicators are fully warmed.

Warm-up bars do not contribute trades, exposure, strategy equity, or benchmark performance.

For 2024 validation and every rolling test fold, earlier development bars may provide causal
indicator context. Position, cash, equity, benchmark, exposure, costs, and trade accounting reset
at the evaluation boundary. No position may carry into an evaluation window.

BTC buy-and-hold enters at the first evaluation 15m open and marks to the final evaluation close;
it never starts at the beginning of warm-up context.

## Frozen baseline parameters

| Layer | Parameter | Baseline |
|---|---|---:|
| Regime | 1h fast EMA | 50 |
| Regime | 1h slow EMA | 200 |
| Regime | slow-EMA slope lookback | 24 completed 1h bars |
| Strength | 1h ADX period | 14 |
| Strength | entry ADX threshold | 25 |
| Strength | regime-loss ADX threshold | 20 |
| Volatility | 15m ATR period | 14 |
| Volatility | median window | 2,880 prior 15m bars |
| Volatility | minimum ATR-ratio | 0.60 × median |
| Volatility | maximum ATR-ratio | 1.80 × median |
| Volatility | absolute ATR/close ceiling | 3.00% |
| Entry | Donchian breakout lookback | 20 prior 15m bars |
| Alignment | 15m EMA pair | 20 / 50 |
| Alignment | EMA20 slope lookback | 4 completed 15m bars |
| Execution | maximum favorable entry gap | 0.50 × signal ATR |
| Initial stop | ATR multiple | 2.50 |
| Trailing stop | ATR multiple | 3.00 |
| Regime exit | consecutive invalid 1h bars | 2 |
| Re-entry | cooldown after any exit | 4 completed 15m bars |

## Regime and filter rules

### Long-eligible 1h regime

The most recent completed 1h bar is `BULL_TREND` only when all are true:

1. `close_1h > EMA50_1h > EMA200_1h`;
2. `EMA200_1h(t) > EMA200_1h(t-24)`;
3. `ADX14_1h >= 25`;
4. `+DI14_1h > -DI14_1h`.

Otherwise Trend V2 returns `NO_TRADE` for new entries. `BEAR_TREND`, `RANGE`, `BREAKOUT`,
`HIGH_VOLATILITY`, `CHAOS`, and `UNKNOWN` never authorize a long Trend V2 entry.

### Volatility eligibility

For the completed 15m signal bar:

```text
atr_pct          = ATR14_15m / close_15m
prior_median     = median(previous 2,880 completed atr_pct values)
relative_atr     = atr_pct / prior_median
```

Entry volatility is eligible only when:

```text
0.60 <= relative_atr <= 1.80
and atr_pct <= 0.03
```

Values outside this envelope produce `NO_TRADE`. Position size is not increased in low
volatility, and a high-volatility veto cannot be overridden by signal strength.

## Entry contract

A new long proposal exists only when every condition is true on the same completed 15m signal bar:

1. no position is open and the four-bar cooldown is complete;
2. the completed 1h regime is long-eligible;
3. the volatility filter is eligible;
4. `EMA20_15m > EMA50_15m`;
5. `EMA20_15m(t) > EMA20_15m(t-4)`;
6. `breakout_level_t = max(high[t-20], ..., high[t-1])` and `close_t > breakout_level_t`;
7. `prior_level = max(high[t-21], ..., high[t-2])` and `close[t-1] <= prior_level`, so this is a
   fresh transition rather than an already-active breakout state.

The entry reference is the next 15m open. Cancel the entry and record `NO_TRADE` when:

- next open is above `signal_close + 0.50 × signal_ATR`;
- next open is at or below `signal_close - 2.50 × signal_ATR`;
- data/regime/execution health becomes invalid before execution;
- Spot cash, fee, minimum-size, or risk constraints cannot be satisfied.

## Exit contract

### Protective and trailing exit

- Initial stop: `executed_entry - 2.50 × signal_ATR14`.
- Chandelier candidate after entry: `highest_completed_high_since_entry - 3.00 × ATR14`.
- The active stop may only ratchet upward: `max(previous_stop, chandelier_candidate)`.
- If a bar opens below the active stop, exit at that bar open.
- Otherwise, if its low touches the stop, exit at the stop price.
- On an entry bar with ambiguous intrabar ordering, use the conservative stop-first assumption.

The stop inherited from the previous completed bar is active for the entire next bar. If it does
not execute, the new chandelier candidate and normal-exit signals are calculated at that bar's
close and become actionable no earlier than the following bar. The entry-bar initial stop is active
immediately after execution at the bar open.

### Normal close-signal exit

Exit at the next 15m open when either is observed on completed data:

- `close_15m < EMA50_15m`; or
- two consecutive completed 1h bars invalidate the long regime because structural alignment is
  false, `+DI <= -DI`, or `ADX14 < 20`.

If multiple exits trigger, use the earliest executable protective price. There is no take-profit,
pyramiding, averaging down, or discretionary exit.

An incomplete 1h bar cannot count as either valid or invalid for the two-bar regime exit. It does
activate the data-health entry veto. Cooldown counts four subsequently completed 15m closes after
the exit bar; the earliest new signal is the fourth such close.

## Signal/allocation versus risk-sized layers

The A–D development layer is a signal/allocation diagnostic:

- one long position maximum;
- each entry invests all available cash after entry fees;
- no leverage or borrowing;
- the same entry, stop, trailing stop, normal exit, and cost model as the frozen hypothesis;
- no 0.35% risk sizing, 50% notional cap, daily-loss halt, or 8% drawdown halt.

This layer measures raw signal quality and is never execution authority. The E layer replays the
identical causal signals using the risk-sized policy below. Signal and risk layers must never share
position state or equity.

## Frozen risk and cost assumptions

- Planned risk per trade: 0.35% of current equity; hard maximum 0.35% + numeric tolerance.
- Position size: `risk_budget / abs(entry - initial_stop)`.
- Maximum invested notional: 50% of current equity including entry fee.
- Available Spot cash is an additional hard cap.
- Maximum open positions: one.
- Daily realized-loss entry halt: 1.50% of start-of-day equity.
- Maximum drawdown entry halt: 8.00%.
- Leverage, shorting, pyramiding, martingale, and averaging down: forbidden.
- No new entry while any data-health, source-gap cooldown, or execution-health veto is active.

The daily halt uses realized PnL accumulated since 00:00 UTC against start-of-day equity. The
drawdown halt uses mark-to-market equity at every completed 15m close relative to the prior equity
peak. Reaching either limit blocks new entries; reaching 8% blocks entries for the remainder of the
evaluation, but does not invent a forced liquidation. An existing position remains governed by its
protective and normal exits.

Cost scenarios remain unchanged from V1 so V2 cannot gain eligibility from cheaper assumptions:

| Scenario | Fee / side | Slippage / side |
|---|---:|---:|
| Base | 10 bps | 5 bps |
| Adverse | 10 bps | 10 bps |
| Severe | 15 bps | 20 bps |

## Required controls

The study must report these alongside Trend V2:

1. BTC buy-and-hold over the identical evaluation boundary;
2. cash / `NO_TRADE`;
3. Trend V1 EMA20/50 frozen result, for historical context only;
4. an unfiltered V2 control using the same Donchian entry, EMA alignment, exits, and costs but with
   the 1h regime/ADX and adaptive-volatility entry vetoes removed.

The unfiltered control retains data-health, warm-up, source-gap cooldown, next-open, entry-gap,
position, and Spot constraints. Only the three named entry filters are removed.

The unfiltered control cannot replace the frozen V2 configuration. Its sole purpose is to test
whether the new filters add measurable value.

## Predeclared development gates

Trend V2 passes development only if every gate passes. A null metric, zero-trade fold where a
positive metric is required, policy mismatch, or data-integrity exception is a failure.

### A. Signal/allocation validation gates — 2024

1. At least 20 closed trades.
2. Base-cost total return > 0.
3. Base-cost expectancy > 0 USD per closed trade.
4. Base-cost profit factor >= 1.15.
5. Severe-cost total return > 0.
6. Severe-cost expectancy > 0.
7. Signal/allocation maximum-drawdown magnitude <= 25%.
8. Time exposure is between 5% and 60%.
9. If return is below BTC buy-and-hold, strategy drawdown magnitude must be <= 60% of BTC drawdown.
10. Every entry must satisfy all regime, strength, volatility, freshness, and breakout invariants.

### B. Filter-value gates — 2024

Relative to the unfiltered V2 control under base costs, filtered V2 must have:

11. strictly higher expectancy;
12. strictly higher profit factor;
13. no worse maximum-drawdown magnitude; and
14. at least 25% lower total trading cost, unless the control has fewer than 20 trades, in which
    case this gate fails rather than becoming not applicable.

### C. Parameter robustness — research window only

The neighborhood is diagnostic, never a tuning menu. Evaluate exactly nine configurations:

1. frozen baseline;
2. Donchian lookback 16;
3. Donchian lookback 24;
4. ADX entry threshold 20;
5. ADX entry threshold 30;
6. maximum relative ATR 1.50;
7. maximum relative ATR 2.10;
8. minimum relative ATR 0.50;
9. minimum relative ATR 0.70.

All unspecified values remain frozen. Required gates:

15. At least 6 of 9 variants have positive base-cost expectancy.
16. At least 6 of 9 variants have base-cost profit factor > 1.0.
17. At least 5 of 9 variants retain positive severe-cost expectancy.
18. The frozen baseline is not the sole best result on both return and expectancy.

For gate 18, “sole best” means its return is strictly greater than every other variant's return and
its expectancy is strictly greater than every other variant's expectancy. A tie on either metric
passes this anti-peak condition. It does not waive gates 15–17.

### D. Rolling temporal stability — research window only

Use fixed Trend V2 parameters with 180-day context, 30-day test windows, and 30-day steps. Context
may warm indicators; performance starts at each test boundary. No fold-specific parameter selection.

A fold with no closed trades counts as failing gates 20–22. Profit factor is considered passing only
when it is a finite value > 1.0, or when the fold has at least one closed winning trade and zero
closed losing trades. Open positions are force-closed at the final evaluation close with exit costs.

19. At least 80% of folds contain one or more closed trades.
20. At least 60% of all folds have positive total return.
21. At least 60% of all folds have positive expectancy.
22. At least 60% of all folds have profit factor > 1.0.
23. At least 60% of all folds have shallower drawdown than BTC buy-and-hold.

### E. Risk-sized execution gates — 2024

Risk execution is run only after A–D all pass.

24. At least 20 closed trades.
25. Base-cost total return > 0.
26. Base-cost expectancy > 0.
27. Base-cost profit factor >= 1.10.
28. Maximum planned risk per trade <= 0.35% of equity.
29. Invested notional including entry fee <= 50% of equity.
30. Base run never reaches the 8% hard drawdown halt.
31. Base maximum drawdown remains strictly above -8%.
32. Severe-cost total return > 0.
33. Severe-cost expectancy > 0.
34. Severe-cost profit factor > 1.0.
35. Severe run never reaches the 8% hard drawdown halt.
36. No entry occurs during a daily-loss halt, source-gap cooldown, stale-data state, or invalid regime.

All study windows force-close an open position at the final evaluation close with the applicable
exit fee and slippage. This close counts as a closed trade. Stops use the 15m OHLC conservative
ordering contract; no lower timeframe is inferred.

## Decision policy

- All A–D gates pass: eligible to implement and run the separately gated risk-sized layer.
- Any A–D gate fails: `REJECT_TREND_V2_SIGNAL_CYCLE`; do not run risk evidence for promotion.
- All A–E gates pass: `ELIGIBLE_FOR_TREND_V2_FINAL_FREEZE_REVIEW`, not automatic freeze.
- Any E gate fails: `REJECT_TREND_V2_EXECUTION_CYCLE`.
- Any rejection leaves 2025 OOS locked. Do not rescue the cycle by choosing a better neighborhood
  value or weakening a threshold after seeing 2021–2024 results.
- Even a development pass does not authorize PAPER, SHADOW, MICRO_LIVE, leverage, or real money.

## Implementation order after owner approval

1. Freeze this document and its SHA-256 in a Trend V2 policy module.
2. Add pure indicator/resampling tests, including incomplete-1h and source-gap behavior.
3. Add causal entry/exit and next-open execution tests.
4. Add signal evidence, controls, robustness, and verdict code.
5. Run the full deterministic suite.
6. Only then run Trend V2 on cached 2021–2024 data.

No Trend V2 code or backtest is authorized by this draft alone.
