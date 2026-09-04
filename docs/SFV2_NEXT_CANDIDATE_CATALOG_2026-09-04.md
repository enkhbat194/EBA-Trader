# Strategy Factory v2 — next candidate catalog freeze

Date: 2026-09-04

Authority: **CATALOG_FREEZE_ONLY**.

This package freezes the exact deterministic catalog for the reserved campaign `sfv2-existing-data-low-turnover-v1`. It does not freeze a dataset and therefore cannot run performance evaluation.

## Frozen allocation

- `mtf_trend_pullback_v1`: 32
- `breakout_retest_entry_v1`: 32
- `path_efficiency_persistence_v1`: 32
- `low_turnover_flow_persistence_v1`: 32
- total: 128

Seed: `sfv2-existing-data-low-turnover-v1-catalog-v1`

Canonical catalog SHA-256:

`0aa793ca70ba8719486ba6edae314c77803e1b87884665d17ec88019ec71654a`

The generator is deterministic, performance-blind, and bounded. Every generated parameter set is validated by the corresponding causal engine configuration before the catalog is accepted.

## Search-history accounting

The prior 406 inspected Strategy Factory v2 candidates remain in search history. If this 128-candidate D0 campaign is eventually run, cumulative inspected candidate history becomes 534. This does not imply 534 independent strategies or 534 verified edges.

## Lower-turnover structure

All families use minimum holding periods of at least 30 minutes and cooldowns of at least 15 minutes. The flow-persistence family is stricter: minimum hold >=60 minutes, cooldown >=30 minutes, and long flow lookback is structurally greater than short flow lookback.

## Still closed

- dataset window freeze: not complete
- D0 performance evaluation: not authorized
- D1: sealed
- Frozen OOS: sealed
- SF4 prospective evidence: protected
- Demo promotion: disabled
- live/real execution: locked

The next required package is the exact D0 dataset/materialization freeze validated against `sfv2_historical_window_inventory_v1.json`.
