# Decision — Strategy Factory v2 Discovery Layer

Date: 2026-09-01

Status: **Accepted for foundation implementation; pilot search not yet authorized**

## Decision

EBA Trader will stop extending the SF1/SF2/SF3 pattern as an endless sequence of manually authored
24-candidate phases. The next architecture milestone is a bounded Strategy Factory v2 discovery
layer placed **before** the existing strict verification pipeline.

The first foundation/pilot contract uses:

- authority: `DISCOVERY_ONLY`;
- raw candidate hard cap: 500;
- per-family hard cap: 64;
- discovery-survivor hard cap: 30;
- target 8–12 genuinely different strategy families;
- deterministic, non-adaptive parameter sampling for pilot v1;
- structural and behavioral duplicate accounting;
- immutable trial ledger for every performance-inspected candidate;
- explicit D0/D1/D2/D3 data authority zones.

## Why

SF1/SF2/SF3 show that EBA's verification controls can reject sparse, negative and statistically
weak candidates correctly. The current bottleneck is discovery throughput and family diversity,
not a need to weaken verification gates.

A larger discovery funnel can reduce expensive compute spent on obviously poor candidates, but
only if every inspected trial is accounted for and hidden confirmation remains separate.

## What this does not authorize

This decision does not authorize:

- 5,000-candidate brute-force search;
- automatic budget expansion until a winner appears;
- genetic programming or unrestricted AI-generated strategy code;
- adaptive Bayesian tuning on hidden confirmation data;
- lifecycle promotion from discovery results;
- Frozen OOS access;
- forward-paper/Demo promotion;
- real-money execution;
- lowering the historical 30-trade/sample-quality bar to rescue SF3 sparse winners.

## Migration rule

SF1/SF2/SF3 remain immutable historical phases. Their inspected evidence is not fresh Strategy
Factory v2 confirmation data. SF3 compression/expansion results may inform a new family hypothesis,
but the inspected SF3 windows cannot be reused as hidden confirmation for that hypothesis.

## Verification boundary

A Factory v2 discovery survivor is only a nomination. Before any durable EBA lifecycle promotion,
it must be frozen and pass a separately authorized hidden-confirmation path followed by the current
robustness-before-Frozen-OOS lifecycle.

## Pilot authorization rule

The 500-cap pilot search starts only after the foundation PR proves:

1. fail-closed pilot-contract validation;
2. deterministic family/candidate identity;
3. immutable trial accounting;
4. behavioral duplicate controls;
5. no StrategyLifecycle promotion authority;
6. D1/D2/D3 isolation from discovery;
7. green regression/Ruff/runtime/continuity CI;
8. no production execution regression.

A zero-survivor pilot is a valid outcome.
