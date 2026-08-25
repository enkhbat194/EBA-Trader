# EBA Trader Backtest & Validation Protocol

## Principle

A profitable backtest is evidence to investigate, not permission to trade real money.

## Required stages

### Stage 1 — Data integrity

Before evaluating a strategy:
- verify timestamp ordering,
- verify no duplicate/corrupt bars,
- normalize timezone,
- reject unapproved missing data and document any predeclared source-outage gaps,
- ensure indicators use only information available at decision time.

### Stage 2 — In-sample research

Use an explicit research window to develop the hypothesis. Parameter tuning must be recorded.

### Stage 3 — Out-of-sample test

Reserve unseen data. No parameter changes are allowed after seeing the out-of-sample result without restarting the validation cycle as a new strategy version.

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

## Canonical strategy lifecycle

The durable strategy lifecycle is:

```text
GENERATED
  -> BACKTESTED
  -> OOS_VERIFIED
  -> ROBUSTNESS_VERIFIED
  -> PAPER_CANDIDATE
  -> PAPER_VERIFIED
  -> DEMO_CANDIDATE
  -> DEMO_VERIFIED
  -> SHADOW_VERIFIED
  -> MICRO_LIVE_ELIGIBLE
  -> LIVE_ELIGIBLE
  -> LIVE_ACTIVE
```

Failure/revalidation states are `REJECTED`, `QUARANTINED`, `RETEST_REQUIRED` and `RETIRED`.
Promotion transitions require recorded evidence and may not skip gates.

The earlier shorthand `RESEARCH -> PAPER -> SHADOW -> MICRO_LIVE` remains a conceptual summary only; the lifecycle above is the machine-enforced contract for new M4+ work.

## Promotion gates

A strategy may move to `BACKTESTED` only after development evidence is persisted.

A strategy may move to `OOS_VERIFIED` only after its frozen OOS test passes without post-open retuning.

A strategy may move to `ROBUSTNESS_VERIFIED` only after walk-forward, parameter-neighborhood and cost-stress requirements pass.

A strategy may move to `PAPER_CANDIDATE` / `PAPER_VERIFIED` only after research gates pass and forward-paper behavior is recorded.

A strategy may move to `DEMO_CANDIDATE` / `DEMO_VERIFIED` only after a separate exchange-demo execution path is tested. Paper simulation alone is not Demo verification.

A strategy may move to `SHADOW_VERIFIED` only after live-market shadow behavior is reconciled without sending real orders.

`MICRO_LIVE_ELIGIBLE` and later states require a recorded human approval plus all deterministic safety checks. Eligibility is not an order-submission instruction.

Capital is never increased automatically because of a short winning streak.

## Failure policy

A strategy is rejected, quarantined, returned to retest or retired when:
- drawdown violates its validated envelope,
- live/paper behavior materially diverges from backtest assumptions,
- expected edge disappears after costs,
- performance drift persists,
- market structure changes invalidate the hypothesis.

A changed strategy specification is a new immutable version and must restart the appropriate validation path rather than silently rewriting prior evidence.
