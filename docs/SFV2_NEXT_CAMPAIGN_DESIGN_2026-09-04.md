# Strategy Factory v2 — Next Campaign Design

Date: 2026-09-04 (Asia/Ulaanbaatar)

Status: **DESIGN ONLY — PERFORMANCE EVALUATION NOT AUTHORIZED**

Canonical config: `config/sfv2_next_campaign_design_v1.json`

Validator: `src/eba_trader/strategy_factory_v2_next_design.py`

Reserved future campaign ID: `sfv2-existing-data-low-turnover-v1`

## Why a new campaign is required

The first `sfv2-discovery-pilot-v1` campaign inspected 406 candidates and froze zero survivors. The production postmortem shows that the next useful move is not to fill the unused 94 numerical slots or retune neighboring parameters of the same eight failed families.

The next campaign must respond to the actual failure modes:

- all 152 complete non-rejected candidates failed net return, expectancy and benchmark-relative return;
- 107 candidates were cost-sensitive only under a diagnostic cost-recovery proxy;
- ATR and Donchian style entries showed substantial post-signal chase before next-open execution;
- one-minute order-flow impulse generated extreme turnover;
- mean reversion remained negative despite a favorable pre-entry move;
- compression-expansion and volume-shock families were largely inactive/rejected.

Full evidence: `docs/SFV2_D0_FAILURE_POSTMORTEM_2026-09-04.md`.

## Repository/data-plane audit

### Historical research planes currently usable

The present causal historical research stack supports:

1. Binance USD-M futures candles / price / volume;
2. executed aggregate-trade order flow;
3. deterministic footprint-derived features from that executed-flow plane.

These are already provenance-checked and causally aligned in the M5/Strategy Factory infrastructure.

### Present but not a historical research corpus

`m18_fee_aware.py` can inspect current spot/futures books, commission schedules and fee-aware cash-and-carry snapshots. This is useful execution plumbing and cost modelling, but it is **not** a historical basis/funding/order-book research dataset and cannot be relabelled as one.

`momentum_engine.py` contains a BTCUSDT 1m/5m paper-only momentum prototype using EMA/RSI/ADX/ATR/volume/structure. It explicitly is not a validated profitability claim and is not itself the next Strategy Factory backtest family.

### Historical planes not currently available to this design

The audited repository does not currently provide an approved historical causal Strategy Factory corpus for:

- funding rates;
- open interest;
- futures basis/premium history;
- resting limit-order-book depth/imbalance history.

The design therefore records these as unavailable. They can become future campaign inputs only after a separate acquisition, availability-time, integrity, provenance and causal-alignment package is implemented and audited.

## Search budget decision

This design deliberately gets **smaller**, not larger:

- raw-candidate cap: **128**
- family cap: **32**
- survivor cap: **12**
- proposed family slots: **4**
- prior inspected candidates retained in search history: **406**

The 128 limit is a cap, not a quota. If a family has fewer scientifically defensible bounded specifications, its unused capacity is not reassigned after performance is observed.

No D0 performance evaluation is authorized by this document or config.

## Proposed new family slots

### 1. `mtf_trend_pullback_v1`

Mechanism: establish direction on a slower causal horizon and enter only after a lower-timeframe pullback rather than immediately chasing the trend signal.

Purpose:

- target materially lower turnover;
- avoid the measured +5.26 bps ATR next-open chase pattern;
- separate regime detection from entry timing.

This family may not copy the old ATR trailing entry/exit logic or simply widen ATR parameters.

### 2. `breakout_retest_entry_v1`

Mechanism: identify a causal range break, then wait for a separately defined post-break retest before entry.

Purpose:

- directly address the measured +7.63 bps Donchian next-open chase headwind;
- test whether a non-chasing breakout mechanism has economic value after costs.

This is not permission to rerun Donchian with lower fees or a one-bar shortcut. The retest/fill rule must be causal and frozen before evaluation.

### 3. `path_efficiency_persistence_v1`

Mechanism: measure directional distance relative to total path/noise and trade only when persistence/efficiency meets a bounded rule.

Purpose:

- test a different candle-derived economic hypothesis from ATR state, channel breakout and z-score displacement;
- prefer sustained low-noise moves over raw single-bar impulse;
- support slower decision horizons.

### 4. `low_turnover_flow_persistence_v1`

Mechanism: use multi-window executed-flow persistence with an explicit cooldown and minimum holding horizon.

Purpose:

- respond directly to the 20,227-trade order-flow impulse failure;
- prevent one-minute re-entry churn by construction;
- ask whether sustained flow information survives after turnover is structurally controlled.

It may not be a renamed threshold neighborhood of `orderflow_delta_impulse_v1` or `rolling_flow_trend_v1`.

## Horizon policy

The source remains 1-minute causally aligned data, but future family implementations may derive closed:

- 5-minute bars;
- 15-minute bars;
- 60-minute bars.

Derived bars must use only fully closed underlying 1-minute observations. Signal availability and order availability must be explicit. A family may not read a higher-timeframe bar before its close.

The design explicitly prohibits one-minute impulse re-entry as the default mechanism and targets lower turnover than the first D0 campaign.

## Execution design requirement

The postmortem proves that one common execution assumption affects different families very differently. Therefore the next implementation package must define entry availability by family instead of assuming that every new signal should simply enter at the next market open.

Allowed future causal examples include:

- next-open market entry after a fully closed decision bar;
- a resting limit/retest order created only after the signal becomes available and filled only if later price causally reaches it;
- expiry/cancel rules defined before performance inspection.

Prohibited:

- same-bar fills using information unavailable at order creation;
- choosing market vs limit entry after seeing which performs better without counting both as inspected trials;
- using future high/low to infer a fill before the order existed.

## Dataset gate before evaluation

The existing D0 materialization is already inspected. It may remain useful for engineering and contaminated discovery diagnostics, but the next campaign requires a deliberate dataset decision appropriate to slower horizons.

Before candidate evaluation, a separate package must freeze:

1. exact symbol/venue universe;
2. exact historical window(s);
3. exact temporal strata size;
4. warmup rules;
5. whether the data was previously inspected and therefore its evidence authority;
6. dataset content hashes;
7. causal aggregation rules;
8. explicit non-overlap with protected SF4 prospective evidence and Frozen OOS.

`new_dataset_window_frozen` therefore remains `false` in the design config.

## Candidate-catalog gate before evaluation

A separate implementation package must define bounded parameter axes and generate the exact deterministic catalog. It must prove:

- no more than 32 candidates per family;
- no more than 128 total;
- deterministic replay from a fixed seed;
- unique specifications;
- no forbidden failed-family neighbor padding;
- static causal validation before any performance metric is inspected.

`candidate_catalog_frozen` therefore remains `false` in the design config.

## Multiple-testing/search-history rule

The prior 406 candidates remain part of the broad inspected search history. A future statistical verification layer may not pretend the next 128-cap campaign is the first search ever performed.

Within the future campaign, every performance-inspected candidate counts even if it is later rejected for poor economics, inactivity, duplication or compute triage.

## Future data-plane campaign — separate from this design

Funding, OI, basis and historical resting-book data are potentially valuable because they could introduce genuinely new information rather than another transformation of the same candles/flow. They are **not** silently added to this campaign.

A later data-plane package should first implement and prove acquisition/provenance. Only after that should a separate versioned campaign consider mechanisms such as:

- funding/basis convergence;
- OI/price/flow dislocation;
- cross-symbol relative strength or relative value;
- resting-book liquidity response.

Keeping this separate prevents data engineering decisions from being adapted after seeing strategy returns.

## Explicit exclusions

The next campaign may not spend its budget on neighboring parameter variants of:

- `atr_trailing_v1`;
- `donchian_breakout_v1`;
- `mean_reversion_z_v1`;
- `orderflow_delta_impulse_v1`;
- `rolling_flow_trend_v1`;
- `volume_shock_momentum_v1`;
- `vwap_reversion_flow_v1`;
- `compression_expansion_v1`.

SF4 is not part of this campaign. The exact SF4 hypotheses remain frozen and inaccessible before `2026-09-13T00:00:00Z`.

## Safety / authority

This design grants none of the following:

- candidate evaluation authority;
- fresh-confirmation status;
- D1 access;
- Frozen OOS access;
- SF4 prospective-data access;
- Demo promotion;
- live execution;
- real-money execution.

The config validator fails closed if any of those boundaries are changed.

## Completion criteria for the next implementation package

The next package after this design is complete only when it has:

1. implemented the four causal family engines/adapters without importing failed-family parameter neighborhoods;
2. implemented causal multi-timeframe aggregation and family-specific order-availability/fill rules;
3. inventoried protected/inspected historical windows and frozen a permissible D0 dataset contract;
4. frozen the deterministic <=128 candidate catalog;
5. added regression tests for no-lookahead, fill availability, cooldown/turnover constraints and search-budget accounting;
6. left evaluation disabled until those exact contracts are merged and CI-green.

Only then should a separately authorized D0 run be considered.
