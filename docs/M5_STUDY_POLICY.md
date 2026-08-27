# M5 Order-Flow Chronological Study Policy

## Purpose

M5 order-flow research now has a dedicated chronological study policy instead of relying on the earlier first-cycle BTCUSDT holdout. The earlier holdout is a separate historical policy and remains locked; it is not reinterpreted as temporal OOS for a research cycle whose development work already used 2026 data.

This policy exists to prevent adaptive window shifting, accidental OOS acquisition and repeated tuning on the original four-hour pipeline-proof window.

## Sealed domain

- Symbol: `BTCUSDT`
- Venue: Binance USD-M futures
- Interval: `1m`
- Policy version: `1`
- Policy identity: deterministic SHA-derived `m5policy_*`

## Chronology

### Development

`2026-07-01T00:00:00Z -> 2026-08-15T00:00:00Z`

Normal M5 acquisition and real-ablation entry points are development-only and must stay inside this range.

### Frozen OOS

`2026-08-15T00:00:00Z -> 2026-08-22T00:00:00Z`

This range is sealed. Normal development acquisition has no authority to read/fetch it. A request overlapping this range fails before any Binance candle/order-flow network request.

### Forward period

Begins at:

`2026-08-22T00:00:00Z`

Forward/paper/demo use remains a later lifecycle concern and is not opened by this policy package.

## Pre-registered fresh development corpus

The corpus contains twelve non-overlapping four-hour windows. The already-inspected `2026-08-01T00:00:00Z -> 04:00:00Z` pipeline-proof window is deliberately excluded.

| Window | UTC range |
| --- | --- |
| dev-01 | 2026-07-02 00:00 -> 04:00 |
| dev-02 | 2026-07-06 08:00 -> 12:00 |
| dev-03 | 2026-07-10 16:00 -> 20:00 |
| dev-04 | 2026-07-14 00:00 -> 04:00 |
| dev-05 | 2026-07-18 08:00 -> 12:00 |
| dev-06 | 2026-07-22 16:00 -> 20:00 |
| dev-07 | 2026-07-26 00:00 -> 04:00 |
| dev-08 | 2026-07-30 08:00 -> 12:00 |
| dev-09 | 2026-08-03 16:00 -> 20:00 |
| dev-10 | 2026-08-07 00:00 -> 04:00 |
| dev-11 | 2026-08-11 08:00 -> 12:00 |
| dev-12 | 2026-08-14 16:00 -> 20:00 |

Corpus identity is deterministic (`m5corpus_*`). Window names must be unique, chronological and non-overlapping; corpus fan-out has a hard cap of 24 windows.

## Enforcement

`m5_dataset_workflow` now writes workflow schema `m5_usdm_feature_build_v2` and includes `study_policy_id` plus `study_phase=development` in immutable provenance.

Before candle/order-flow acquisition begins, the workflow validates:

- symbol is BTCUSDT;
- venue is USD-M futures;
- interval is 1m;
- required feature/order-flow range lies inside M5 development;
- range does not overlap the legacy first-cycle holdout;
- range does not overlap the new M5 frozen OOS.

`m5_ablation_cli` independently verifies the same policy identity and development phase before queue emission. A tampered/wrong-policy/OOS workflow fails closed.

## Research interpretation

The original four-hour comparisons established pipeline/evidence behavior but did not establish alpha. Isolated Delta/CVD, stacked imbalance, absorption/exhaustion and price/Delta divergence candidates all remain non-promotable.

The next valid research step is to materialize this pre-registered development corpus and evaluate candidate hypotheses across all windows with immutable per-window and aggregate evidence. Positive development survivors may proceed to robustness. Frozen OOS remains closed until lifecycle-policy-v2 requirements are met.

## Explicit non-goals

This policy package does not:

- fetch or inspect the new M5 frozen OOS;
- open the legacy 2025 holdout;
- enable paper/demo/live promotion;
- enable real exchange execution;
- treat resting L2/LOB liquidity as executed-trade footprint data;
- claim that any current order-flow feature has proven edge.
