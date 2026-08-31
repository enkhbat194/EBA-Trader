# EBA Trader — Strategy Factory v2 Discovery Design

Status: **DISCOVERY-ONLY FOUNDATION**

This document defines the boundary between broad strategy search and the existing strict
EBA verification pipeline. It does not authorize Frozen OOS access, paper/demo promotion,
or real-money execution.

## 1. Goal

Increase the probability of finding genuinely different candidate edges without weakening
statistical integrity. The target is not a large candidate count by itself. The target is a
high-throughput, auditable search process that spends expensive verification compute only on
frozen survivors.

Core rule:

> Search broad. Account for every trial. Deduplicate behavior. Verify hard.

## 2. Non-negotiable authority boundary

Strategy Factory v2 discovery has exactly one authority level:

`DISCOVERY_ONLY`

Discovery may:

- register strategy-family hypotheses;
- expand bounded parameter spaces;
- run cheap development simulations on an explicitly designated discovery corpus;
- rank candidates for additional research;
- compute behavioral fingerprints and cluster near-duplicates;
- reject candidates;
- nominate a bounded set of discovery survivors for hidden confirmation.

Discovery may **not**:

- mark a strategy verified;
- transition the durable StrategyLifecycle;
- open Frozen OOS;
- authorize forward paper, Demo, shadow, micro-live or live execution;
- call development ranking a profitability claim;
- use Demo execution as a verification shortcut;
- relabel inspected/adaptively used data as fresh evidence.

A discovery survivor is only a research nomination.

## 3. Pilot budget

The first pilot is intentionally bounded:

- hard raw-candidate cap: **500**;
- hard per-family cap: **64**;
- hard discovery-survivor cap: **30**;
- target independent family count: **8–12**.

The cap is a maximum, not a target that must be consumed. Search may stop early when marginal
behavioral novelty collapses, a family is economically invalid, or the declared compute budget
is exhausted.

The pilot must not be expanded to 1,000–5,000 candidates merely because no winner appears.
Changing the budget is a new versioned campaign decision.

## 4. Family identity vs parameter variant

A strategy family represents an economic/market mechanism, not a parameter tuple.

Same mechanism with different thresholds/lookbacks remains one family. Examples:

- compression ratio 0.55 vs 0.65: parameter variants;
- momentum vs mean reversion: different families;
- price breakout vs executed-order-flow reversal: different families.

Reports must keep these counts separate:

1. raw candidates;
2. unique specifications;
3. behavioral clusters;
4. independent families.

Candidate volume must never be presented as independent-edge count.

## 5. Data zoning

Historical evidence is finite. Factory v2 separates data by authority.

### D0 — Discovery corpus

- repeatedly usable for discovery;
- all adaptive search decisions are considered contaminated by D0;
- no promotion authority;
- cheap/batched evaluation is allowed;
- every evaluated candidate must be recorded in the trial ledger.

### D1 — Hidden confirmation

- sealed from the discovery process;
- opened only after survivor specifications are frozen;
- one-way evidence boundary;
- results cannot be used to retune the same candidate and still keep D1 authority.

### D2 — Robustness reserve

- used after a candidate survives confirmation;
- parameter-neighborhood, cost-stress, regime/walk-forward and implementation-equivalence work;
- candidate-specific robustness protocol must be declared before use.

### D3 — Frozen OOS

- existing EBA Frozen OOS authority;
- inaccessible to Strategy Factory v2 discovery;
- remains sealed until the current EBA robustness-before-OOS rules permit access.

## 6. Candidate generation

Preferred pilot generation order:

1. bounded human/AI DSL family proposals;
2. deterministic quasi-random parameter sampling inside declared ranges;
3. small grids only for intentionally small declared neighborhoods;
4. Bayesian/evolutionary optimization disabled for pilot v1.

Why quasi-random first:

- avoids exponential grid growth;
- maintains deterministic replay from campaign seed/specification;
- does not adapt the next trial to observed D0 performance;
- gives broad coverage without pretending neighboring parameter values are independent ideas.

Unrestricted AI-generated Python and genetic programming remain outside pilot authority.

## 7. Cheap screening funnel

### Stage A — static/sanity screen

No performance ranking is required. Reject:

- invalid DSL/specification;
- unavailable or causally invalid features;
- impossible parameter combinations;
- exact duplicate specifications;
- obvious zero-opportunity strategies;
- impossible execution/holding rules;
- declared complexity/cost limits that cannot be satisfied.

### Stage B — low-fidelity D0 evaluation

Use a predeclared stratified subset of discovery data. It must include heterogeneous regimes;
chronological first-N-window racing is not sufficient.

Metrics may include:

- net expectancy after costs;
- trade/activity count;
- turnover and cost ratio;
- drawdown;
- benchmark delta;
- exposure;
- regime coverage.

These metrics have **selection authority only**, never promotion authority.

### Stage C — behavioral deduplication

Candidates receive behavioral fingerprints based on outcomes such as:

- signal timestamps/directions;
- trade overlap;
- holding/exposure behavior;
- regime-return vector;
- turnover/cost behavior.

Near-identical candidates are one behavioral cluster even when their code or parameters differ.
The pilot default near-duplicate threshold is 0.90 and is versioned in the campaign contract.

### Stage D — higher-fidelity D0 racing

Allocate more D0 compute to diverse representatives. A modified successive-halving approach is
allowed only when each fidelity level is stratified across regimes and the entire selection path
is recorded.

### Stage E — survivor freeze

At most 30 discovery survivors may be nominated. Before D1 opens, freeze:

- family identity;
- full strategy specification;
- parameters;
- feature definitions;
- timeframe/symbol-universe rule;
- execution/cost assumptions;
- source-code SHA;
- survivor-selection rule.

## 8. Search trial ledger

Every D0 trial is auditable even when no full immutable lifecycle evidence artifact is produced.
Each record includes at minimum:

- campaign ID;
- trial ID;
- family ID;
- deterministic candidate ID;
- candidate specification SHA-256;
- dataset SHA-256;
- source-code SHA;
- search round/fidelity;
- status;
- metrics;
- behavioral fingerprint when available;
- rejection reason;
- compute time.

Trial results become immutable after they are recorded. The same campaign definition cannot be
silently rewritten under the same campaign ID.

## 9. Multiple-testing policy

The pilot does not pretend that cheap screening removes multiple-testing risk.

Rules:

- every performance-inspected D0 candidate counts as part of search history;
- family and behavioral-cluster counts are tracked in addition to raw trials;
- FDR/Deflated Sharpe/PBO may be diagnostics for discovery ranking, not final promotion;
- hidden confirmation must account for the preceding search process;
- final promotion remains under the current EBA strict verification pipeline;
- no statistical method replaces untouched confirmation/Frozen OOS.

A later statistical design may use family-level omnibus testing plus dependency-aware candidate
corrections, but pilot v1 must not weaken the current strict gate while that design is being
validated.

## 10. Diversity policy

Diversity can break ties between economically viable candidates. It cannot rescue a negative-
expectancy strategy.

Candidate priority may include:

- positive net economics;
- activity/sample adequacy;
- parameter/local stability;
- regime coverage;
- turnover/cost sensitivity;
- complexity penalty;
- behavioral novelty versus existing survivors.

Any combined value is named `discovery_priority_score`; it is never called a verification score
or a p-value.

## 11. Compute architecture

Do not run 500 candidates as 500 heavyweight production jobs.

Preferred architecture:

1. materialize immutable D0 feature/data matrices once;
2. load a batch once per symbol/window group;
3. evaluate many bounded candidates in-process/vectorized where semantics allow;
4. persist compact trial metrics to the discovery ledger;
5. create heavyweight immutable verification evidence only for frozen confirmation survivors.

Production paper/execution runtime must retain resource priority over research.

## 12. Migration from SF1/SF2/SF3

SF1/SF2/SF3 remain immutable historical research phases. Their inspected windows do not become
fresh Factory v2 confirmation evidence.

SF3 result remains `NO_VERIFIED_CANDIDATE`. The compression-expansion result is a hypothesis clue,
not a verified strategy and not permission to lower the 30-trade threshold.

Factory v2 starts as a parallel discovery layer in front of the current verification engine.
The existing lifecycle and verification code is not replaced.

## 13. Pilot success criteria

The pilot succeeds as infrastructure if it can prove all of the following, even if zero strategy
survives:

- no more than 500 raw candidates can be declared;
- no family can consume more than its declared cap;
- every candidate has deterministic identity and immutable trial history;
- behaviorally duplicate candidates collapse into representative clusters;
- discovery survivors cannot alter StrategyLifecycle;
- D1/D2/D3 data boundaries remain closed from discovery;
- Frozen OOS and real execution remain locked;
- the search can be replayed deterministically from campaign/data/code identities;
- compute remains bounded enough not to interfere with production paper services.

Finding a profitable strategy is not required to call the infrastructure test successful.
