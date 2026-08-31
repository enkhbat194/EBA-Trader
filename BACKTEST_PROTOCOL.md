# EBA Trader Backtest & Validation Protocol

## Principle

A profitable backtest is evidence to investigate, not permission to trade real money.

Strategy discovery, statistical confirmation, robustness, Frozen OOS, forward paper, Demo and
real execution are separate authorities. Success at an earlier stage cannot skip a later gate.

## Data authority zones

Strategy Factory v2 uses explicit historical-data zones:

### D0 — Discovery corpus

- reusable for broad/adaptive search;
- all performance-inspected trials are part of search history;
- no lifecycle-promotion authority;
- no result from D0 may be called fresh confirmation or OOS evidence.

### D1 — Hidden confirmation

- sealed until discovery survivors are frozen;
- opened only by a separately authorized confirmation workflow;
- any post-open retuning invalidates that survivor's D1 confirmation authority.

### D2 — Robustness reserve

- candidate-specific parameter-neighborhood, walk-forward/regime and cost-stress evaluation;
- robustness design is frozen before the relevant reserve evidence is inspected.

### D3 — Frozen OOS

- highest pre-forward-test historical authority;
- inaccessible to discovery workflows;
- remains sealed until development/confirmation and robustness requirements pass.

Reused or adaptively inspected data must never be relabelled as a higher-authority zone.

## Stage 0 — Strategy discovery

Discovery may generate and cheaply evaluate many hypotheses, but it has **selection authority
only**.

Required controls:

- bounded/versioned candidate budget;
- family identity separated from parameter variants;
- deterministic candidate/spec identity;
- trial ledger for every performance-inspected candidate;
- causal/static sanity screening;
- behavioral duplicate/cluster accounting;
- source-code and dataset identity;
- no Frozen OOS access;
- no durable StrategyLifecycle transition.

A `DISCOVERY_SURVIVOR` or equivalent nomination is not `BACKTESTED`, verified, paper-ready or
Demo-ready.

## Stage 1 — Data integrity

Before evaluating a strategy under any authoritative stage:

- verify timestamp ordering;
- verify no duplicate/corrupt bars;
- normalize timezone;
- reject unapproved missing data and document any predeclared source-outage gaps;
- ensure indicators/features use only information available at decision time;
- verify dataset provenance and immutable content identity;
- keep Spot, USD-M futures, executed order-flow and resting order-book planes distinct.

## Stage 2 — Development / confirmation

Use explicit windows and record every tuning/search decision that influenced the candidate.

For broad Factory v2 search, D0 is non-authoritative discovery data. A frozen survivor must face a
separate D1 hidden-confirmation workflow before it can enter strict verification.

Selection from many candidates must account for multiple-testing/search bias. Ranking by raw
return, Sharpe or expectancy alone is not promotion authority.

## Stage 3 — Robustness before Frozen OOS

Under lifecycle policy v2, robustness comes **before** the first Frozen OOS state.

Robustness must address, where relevant:

- walk-forward/regime stability;
- parameter-neighborhood stability;
- cost/slippage stress;
- turnover/activity stability;
- implementation/time-semantics equivalence;
- symbol/regime dependence;
- sparse-sample failure modes.

Reject strategies that depend on one exact threshold, one isolated window or unrealistic costs.

## Stage 4 — Frozen OOS

Only a separately authorized workflow may open D3 Frozen OOS after prior gates pass.

Rules:

- no parameter/spec changes after opening;
- no repeated peeking;
- a failed Frozen OOS does not permit retuning and replay under the same strategy version;
- changed strategy specifications require a new immutable version and a restarted validation
  cycle with fresh authority boundaries.

## Stage 5 — Forward paper

Forward paper observes live-market behavior without exchange orders.

Required evidence includes:

- signal timing;
- fill-model assumptions;
- position/exit lifecycle;
- cost and latency realization versus historical assumptions;
- persistence/restart behavior;
- risk-governor vetoes;
- drift versus verified research envelope.

Paper success does not imply Demo or live eligibility.

## Stage 6 — Binance Demo

Demo validates exchange/API execution plumbing and strategy/runtime integration without real money.

Demo is **not** a shortcut around research verification. A successful Demo round-trip proves order
plumbing, not profitability.

## Stage 7 — Shadow / micro-live eligibility / live

Shadow observes real market/exchange behavior without sending real orders. Micro-live and later
states require explicit human approval plus deterministic safety checks and recorded evidence.

Eligibility is never an order-submission instruction.

## Cost model

Every performance claim must include costs appropriate to the venue/product, including as relevant:

- maker/taker fees;
- spread;
- slippage;
- funding/basis costs;
- latency sensitivity;
- market impact for size-sensitive designs.

Run at least base and adverse cost scenarios before robustness verification. Severe stress is
required when the strategy edge is close to the modeled execution-cost floor.

## Benchmark comparison

At minimum compare with context-appropriate references such as:

- cash/no-trade;
- same-period buy-and-hold where meaningful;
- a simple declared baseline strategy;
- benchmark-relative return under the same cost/data assumptions.

Beating a negative baseline while remaining absolutely unprofitable is not enough.

## Mandatory metrics

Track at least where meaningful:

- total and mean return;
- maximum drawdown;
- profit factor;
- expectancy per trade;
- win rate;
- average win / average loss;
- Sharpe/Sortino with sample caveats;
- trade count;
- exposure time;
- turnover;
- fee/slippage/funding cost;
- benchmark-relative return;
- cross-window/regime coverage;
- parameter/cost sensitivity.

Win rate alone is not a valid quality measure. Statistical significance with a sparse trade count
is also insufficient.

## Multiple-testing and search-bias controls

Explicitly account for:

- how many raw candidates were performance-inspected;
- how many unique specifications existed;
- how many behavioral clusters existed;
- how many genuine strategy families were searched;
- adaptive search rounds;
- symbol/timeframe/regime selection decisions;
- all hidden-confirmation peeks.

Discovery diagnostics may use methods such as Deflated Sharpe Ratio, PBO or FDR, but these are not
promotion shortcuts. Confirmatory testing may use family-level/dependency-aware procedures when
versioned and validated. No statistical correction replaces hidden confirmation or Frozen OOS.

## Canonical strategy lifecycle — policy v2

The machine-enforced promotion path for current/new research is:

```text
GENERATED
  -> BACKTESTED
  -> ROBUSTNESS_VERIFIED
  -> OOS_VERIFIED
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

Historical policy v1 used OOS before robustness. Stored v1 evidence remains historical and cannot
silently acquire policy-v2 authority.

## Promotion gates

A strategy may move to `BACKTESTED` only after strict development/confirmation evidence required by
its protocol is persisted. Discovery-only trial/survivor records do not satisfy this gate.

A strategy may move to `ROBUSTNESS_VERIFIED` only after its fixed robustness suite passes.

A strategy may move to `OOS_VERIFIED` only after robustness has passed and its separately authorized
Frozen OOS test passes without post-open retuning.

A strategy may move to `PAPER_CANDIDATE` / `PAPER_VERIFIED` only after research gates pass and
forward-paper evidence is recorded.

A strategy may move to `DEMO_CANDIDATE` / `DEMO_VERIFIED` only after a separate exchange-demo path is
validated. Paper simulation alone is not Demo verification.

A strategy may move to `SHADOW_VERIFIED` only after live-market shadow behavior is reconciled without
sending real orders.

`MICRO_LIVE_ELIGIBLE` and later states require recorded human approval plus all deterministic safety
checks. Capital is never increased automatically because of a short winning streak.

## Generic research-worker boundary

The generic research worker is a development execution mechanism, not Frozen-OOS or lifecycle-
promotion authority by itself.

- It accepts only registered backtest adapters.
- It validates exact dataset coverage before execution.
- It must fail closed on protected higher-authority datasets unless a separate authorized workflow
  explicitly grants access.
- Successful execution means the experiment completed; it does not mean the strategy passed a
  lifecycle gate.
- Authoritative evidence must preserve dataset, strategy-spec and source-provenance identities.

## Failure policy

Reject, quarantine, retest or retire a strategy when appropriate if:

- drawdown violates its validated envelope;
- live/paper behavior materially diverges from backtest assumptions;
- expected edge disappears after realistic costs;
- performance drift persists;
- market structure changes invalidate the hypothesis;
- activity/sample size is insufficient;
- robustness depends on a narrow parameter island;
- selection-bias accounting is invalid;
- data authority was contaminated or reused incorrectly.

A changed strategy specification is a new immutable version and must restart the appropriate
validation path rather than silently rewriting prior evidence.
