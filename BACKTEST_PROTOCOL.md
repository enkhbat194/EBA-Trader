# EBA Trader Backtest & Validation Protocol

## Principle

A profitable backtest is evidence to investigate, not permission to trade real money.

## Required stages

### Stage 1 — Data integrity

Before evaluating a strategy:
- verify timestamp ordering,
- verify no duplicate/corrupt bars,
- normalize timezone,
- document missing data,
- ensure indicators use only information available at decision time.

### Stage 2 — In-sample research

Use an explicit research window to develop the hypothesis. Parameter tuning must be recorded.

### Stage 3 — Out-of-sample test

Reserve unseen data. No parameter changes are allowed after seeing the out-of-sample result without restarting the validation cycle.

### Stage 4 — Walk-forward

Evaluate repeated train/validate windows through different market regimes.

### Stage 5 — Cost stress

Every result must include:
- maker/taker fees,
- spread assumption,
- slippage assumption,
- latency sensitivity where relevant.

Run at least base, adverse and severe cost scenarios.

### Stage 6 — Robustness

Reject strategies that depend on one exact parameter value. Perturb key parameters and verify behavior remains coherent.

### Stage 7 — Benchmark comparison

At minimum compare with:
- BTC buy-and-hold over the same period,
- cash/no-trade,
- simple baseline strategy where appropriate.

## Mandatory metrics

Track at least:
- total return,
- annualized return where meaningful,
- maximum drawdown,
- profit factor,
- expectancy per trade,
- win rate,
- average win / average loss,
- Sharpe ratio,
- Sortino ratio,
- trade count,
- exposure time,
- fee/slippage cost,
- benchmark-relative return.

Win rate alone is not a valid quality measure.

## Bias controls

Explicitly check for:
- look-ahead bias,
- survivorship bias where relevant,
- data leakage,
- overfitting,
- repeated test-set peeking,
- unrealistic fills,
- ignored fees,
- selection bias from trying many strategies and reporting only winners.

## Promotion gates

A strategy may move:

`RESEARCH -> PAPER`
only after passing out-of-sample, walk-forward and cost stress tests.

`PAPER -> SHADOW`
only after behavior matches expected execution and risk characteristics.

`SHADOW -> MICRO_LIVE`
only after a recorded human approval and all safety checks are operational.

`MICRO_LIVE -> larger capital`
requires a new review. Capital is never increased automatically because of a short winning streak.

## Failure policy

A strategy is retired or returned to research when:
- drawdown violates its validated envelope,
- live/paper behavior materially diverges from backtest assumptions,
- expected edge disappears after costs,
- performance drift persists,
- market structure changes invalidate the hypothesis.
