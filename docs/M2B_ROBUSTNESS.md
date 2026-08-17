# M2B — Robustness, Walk-Forward & Regime Diagnostics

## Goal

Reject fragile Trend Following V1 results before any PAPER execution is considered.

M2B does not try to make the backtest look better. Its purpose is to break the strategy if the apparent edge depends on one exact EMA pair, one market window, one warm-up artifact, or one market regime.

## Strict crossover semantics

Trend Following V1 is a **strict EMA crossover** strategy.

- BUY requires the EMA state to change from `fast <= slow` to `fast > slow` on a completed candle.
- EXIT requires the reverse change.
- Being already above the slow EMA when an evaluation window begins does not create a synthetic BUY.
- Orders are modeled at the next candle open after the completed signal candle.

This distinction matters: a state-entry strategy can invent an entry at every backtest/window boundary even though no crossover occurred there.

## Parameter neighborhood

The frozen first neighborhood is intentionally small:

- fast EMA: 15, 20, 25
- slow EMA: 40, 50, 60

All valid fast/slow combinations are tested with the same fee and slippage assumptions.

The neighborhood is a **fragility diagnostic, not a tuning menu** for the first cycle. EMA 20/50 was predeclared before real historical evidence is opened; a better-looking neighbor does not replace it for the frozen 2025 OOS.

The report records:

- fraction of parameter pairs with positive return;
- fraction beating BTC buy-and-hold;
- fraction with positive expectancy;
- median return;
- worst return;
- median and worst maximum drawdown;
- per-parameter metrics.

A single winning parameter pair surrounded by failures is treated as an overfitting warning.

## Rolling walk-forward

Default research-only walk-forward:

- train: 180 days
- test: 30 days
- step: 30 days
- candidate set: the frozen parameter neighborhood above

For every fold:

1. only the train segment is visible during parameter selection;
2. the train winner is selected by highest train total return;
3. ties prefer shallower drawdown;
4. test evaluation receives the train history only as **causal EMA warm-up context**;
5. no train-period order, equity contribution, exposure or benchmark contribution is counted in test metrics;
6. all test trading/performance starts exactly at the unseen test boundary;
7. the test segment never influences parameter selection for that fold.

Using prior train history for indicator state avoids falsely cold-starting EMA calculations at every test boundary. The trading gate prevents that historical context from becoming in-sample performance.

The first selection rule is deliberately simple so the result is auditable. More elaborate optimization is prohibited until the baseline survives this test.

Run on a sufficiently long cached research CSV:

```bash
eba-validate-trend \
  --csv data/cache/m2/btcusdt_15m_research.csv \
  --report artifacts/m2_trend_robustness.json
```

## Causal regime diagnostics

Trade results are split by historical market regime.

The regime label is causal: it uses only trailing closes that were fully completed before trade entry. A trade entered at a candle open uses the **previous completed candle's** regime; the current candle close is unavailable and cannot be used.

The directional score is cumulative log return divided by the square-root energy of trailing log returns. First default settings:

- lookback: 14 days
- bull: score >= +1.5
- bear: score <= -1.5
- range: otherwise
- insufficient history: unknown

This is a research label, not a production regime classifier. Its purpose is to reveal where the baseline actually earns or loses money.

```bash
eba-regime-report \
  --csv data/cache/m2/btcusdt_15m_research.csv \
  --report artifacts/m2_trend_regimes.json
```

The report includes trade count, total PnL, average PnL, win rate and average trade return for bull, bear, range and unknown buckets.

## Failure signals

Trend Following V1 should be treated as fragile if any of these appear:

- only one or two EMA pairs are profitable while nearby parameters fail;
- walk-forward test returns are mostly negative;
- positive train performance repeatedly turns negative immediately out of sample;
- severe drawdown is concentrated in one common regime;
- most profit comes from one isolated fold or one isolated trade;
- cost increases erase the result;
- parameter selection changes wildly every fold without stable test performance;
- performance depends on artificial entries created at window boundaries.

## Promotion rule

M2B output is evidence only. It does not automatically promote a strategy.

PAPER remains forbidden until the strategy has:

1. credible positive expectancy after costs;
2. acceptable drawdown;
3. non-fragile parameter-neighborhood behavior;
4. useful walk-forward evidence;
5. understood regime dependence;
6. validation and frozen out-of-sample review.
