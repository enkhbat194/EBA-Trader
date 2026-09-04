# Strategy Factory v2 — First D0 Failure Postmortem

Date: 2026-09-04 (Asia/Ulaanbaatar)

## Status

**Package 1 is closed.**

This document records the read-only production postmortem of the immutable first Strategy Factory v2 D0 campaign. It does not alter any trial, candidate, selection, threshold, authority, dataset, D1 boundary, Frozen OOS boundary, Demo state, live state or real-money state.

- campaign: `sfv2-discovery-pilot-v1`
- D0 campaign authority: `DISCOVERY_ONLY`
- postmortem authority: `DISCOVERY_DIAGNOSTIC_ONLY`
- production analysis build: `b822a9815f8f5cc42c674f849e5626d8b7022602`
- production postmortem workflow: `Strategy Factory v2 D0 failure postmortem proof`
- Actions run: `33823539570`
- proof job: `100871190923`
- proof conclusion: `success`
- production proof completed: approximately `2026-09-04T01:02:54Z`

## Immutable campaign result

- raw candidates: 406
- independent pilot families: 8
- D0 strata: 12
- terminal candidate/stratum trials: 4,872 / 4,872
- complete candidates: 406
- rejected candidates: 254
- complete non-rejected / behaviorally eligible candidates: 152
- behavioral clusters: 127
- frozen D0 survivors: **0**
- D1 opened: false
- Frozen OOS opened: false
- live execution allowed: false
- real execution allowed: false

The zero-survivor result remains immutable. No result in this postmortem can convert a rejected or failed D0 candidate into a survivor.

## Global failure decomposition

The 152 complete non-rejected candidates all failed the core economic requirements:

- `non_positive_net_return`: 152
- `non_positive_expectancy`: 152
- `non_positive_benchmark_delta`: 152
- `cost_sensitive_proxy`: 107
- `rejected_or_incomplete`: 254

Family-level primary diagnoses:

- `COST_SENSITIVE_PROXY`: 6 families
- `INACTIVE_OR_REJECTED`: 2 families

The evaluator assumed 4.0 bps fee plus 1.5 bps slippage per side, or **11.0 bps round-trip friction**.

`cost_sensitive_proxy` is deliberately narrow: it adds the recorded cost attribution back to net return as a diagnostic. It is **not** a zero-cost counterfactual backtest, does not reconstruct different fills or signals and does not prove a positive gross edge.

## One-bar execution-delay result

Across all matched D0 trades:

- matched trades: 33,444
- mean pre-entry directional move: +0.09237 bps
- median pre-entry directional move: 0 bps
- positive directional-move share: 0.4860

Therefore the common one-bar delay is **not a global explanation** for the failed campaign. Its impact is highly family-specific.

## Family-level result

| Family | Primary diagnosis | Complete / raw | Trades | Mean net return | Mean expectancy | Cost-sensitive | Mean pre-entry move |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| `atr_trailing_v1` | COST_SENSITIVE_PROXY | 30 / 30 | 3,055 | -0.8377% | -9.4660 | 26 | +5.2569 bps |
| `compression_expansion_v1` | INACTIVE_OR_REJECTED | 0 / 64 | 0* | — | — | 0 | -1.0451 bps** |
| `donchian_breakout_v1` | COST_SENSITIVE_PROXY | 16 / 16 | 569 | -0.3437% | -13.1035 | 6 | +7.6320 bps |
| `mean_reversion_z_v1` | COST_SENSITIVE_PROXY | 44 / 64 | 2,626 | -0.4581% | -7.9549 | 44 | -5.7890 bps |
| `orderflow_delta_impulse_v1` | COST_SENSITIVE_PROXY | 40 / 40 | 20,227 | -4.5713% | -10.8696 | 20 | +0.0745 bps |
| `rolling_flow_trend_v1` | COST_SENSITIVE_PROXY | 20 / 64 | 1,225 | -0.6092% | -12.1931 | 9 | -0.2698 bps |
| `volume_shock_momentum_v1` | INACTIVE_OR_REJECTED | 0 / 64 | 0* | — | — | 0 | -0.5029 bps** |
| `vwap_reversion_flow_v1` | COST_SENSITIVE_PROXY | 2 / 64 | 175 | -0.7410% | -9.3359 | 2 | +0.2059 bps |

\* Aggregate trade count above is for complete non-rejected candidates. Rejected candidate/stratum trials can still contain diagnostic signal/trade observations.

\** Delay observation is descriptive diagnostic evidence from evaluated trial observations and is not survivor evidence.

## Mechanism-specific interpretation

### ATR trailing

The family was active but uniformly net-negative. Mean pre-entry movement of about +5.26 bps shows a material next-open chase effect for this trend style. Even its best candidate remained net-negative. A future trend study must not merely retune ATR neighbors; any retry must be a new family/campaign with a structurally different entry/execution mechanism and full search-history accounting.

### Donchian breakout

The strongest family-specific execution warning appeared here: +7.63 bps mean movement in the eventual trade direction before entry, with 100% positive matched directional moves. That is a major headwind relative to the fixed 11 bps round trip. This still does not prove that same-bar or limit execution would make the strategy profitable. A future breakout/retest mechanism must be separately preregistered and cannot retroactively rescue this failed family.

### Mean reversion z-score

The delay diagnostic was favorable rather than adverse: -5.79 bps on average before entry, yet the family remained negative. This rejects a simple “execution delay caused the failure” explanation for mean reversion. Core economics and friction remain insufficient under the frozen family.

The highest-ranked D0 candidate remained:

`dc_41ef5a002157b82e92bd8df9`

- mean net return: `-0.000596638634337889`
- mean expectancy: `-2.5838131662228028`
- total trades: 23
- mean benchmark-relative return: `-0.001547214383630785`
- cost-recovered diagnostic proxy: positive, but not a counterfactual backtest
- D0 survivor: false

### Order-flow delta impulse

This was the clearest turnover failure: 20,227 trades and roughly USD 452.54 mean candidate cost on USD 10,000 initial capital, while mean net return was about -4.57%. The one-bar delay was negligible. Future order-flow research should not add neighboring impulse thresholds; it needs structurally lower turnover, longer holding/decision horizons or genuinely different information.

### Rolling flow trend

Only 20 of 64 candidates completed non-rejected. Delay was small and slightly favorable, while economics remained negative. The next search should not treat timing as the primary fix.

### Compression expansion and volume shock momentum

Both frozen families were primarily inactive/rejected. This is not permission to lower the same thresholds after seeing the result. The exact `s3_vsm_s150` hypothesis remains independently frozen in SF4 and must be evaluated only under the prospective SF4 contract after its time gate.

### VWAP reversion + flow

Only 2 of 64 candidates completed non-rejected and both remained negative. The family therefore combines an activity problem with negative observed economics; the one-bar delay is not the main explanation.

## Package 1 conclusions

1. The first D0 campaign did **not** fail because all candidates were duplicate behavior: 152 behaviorally eligible candidates formed 127 clusters.
2. Net economics was the decisive campaign failure.
3. Friction matters materially, but `cost_sensitive_proxy` is diagnostic only and cannot be called profitable edge.
4. ATR and Donchian expose a family-specific next-open chase problem.
5. Order-flow delta impulse exposes a structural high-turnover problem.
6. Mean reversion still fails despite favorable pre-entry movement, so timing alone cannot rescue it.
7. Compression-expansion and volume-shock definitions were too inactive under their frozen rules.
8. The unused 94 slots below the 500 hard cap must remain unused for this campaign; they are not a post-hoc retuning budget.
9. The 406 inspected candidate specifications remain part of broad-search/multiple-testing history.
10. There is still **no verified profitable strategy**.

## Required next direction

The next Strategy Factory work is a **new versioned campaign design**, not an extension of this campaign. It must audit available data/engines, choose genuinely new mechanisms/data planes and/or execution horizons, freeze its budget/catalog before performance evaluation and preserve all D1/Frozen-OOS/live/real locks.

SF4 remains independent and cannot be evaluated before `2026-09-13T00:00:00Z`.
