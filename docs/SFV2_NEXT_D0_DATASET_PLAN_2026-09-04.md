# Strategy Factory v2 — next D0 dataset plan

Date: 2026-09-04

Authority: **DATASET_PLAN_FREEZE_ONLY**.

This package freezes the exact source windows and dedicated materialization workflow for the 128-candidate low-turnover campaign. It still does **not** authorize performance evaluation because the ten exact feature dataset SHA-256 receipts have not yet been materialized and frozen.

## Why the first window starts at 00:15Z

The causal order-flow feature builder needs the fully closed one-minute footprint immediately before the first candle. M5 Frozen OOS ends at `2026-08-22T00:00:00Z`. Starting a feature window exactly at that boundary would require reading `2026-08-21T23:59Z`, which belongs to sealed M5 Frozen OOS.

Therefore the first window begins at `2026-08-22T00:15:00Z`. Its required prior footprint begins at `00:14Z`, safely after the sealed boundary while also preserving 15-minute aggregation alignment.

## Frozen D0 windows

- next-d0-01: 2026-08-22 00:15Z → 2026-08-23 00:00Z
- next-d0-02: 2026-08-23 00:00Z → 2026-08-24 00:00Z
- next-d0-03: 2026-08-24 00:00Z → 2026-08-25 00:00Z
- next-d0-04: 2026-08-25 00:00Z → 2026-08-26 00:00Z
- next-d0-05: 2026-08-26 00:00Z → 2026-08-27 00:00Z
- next-d0-06: 2026-08-27 00:00Z → 2026-08-28 00:00Z
- next-d0-07: 2026-08-28 00:00Z → 2026-08-29 00:00Z
- next-d0-08: 2026-08-29 00:00Z → 2026-08-30 00:00Z
- next-d0-09: 2026-08-30 00:00Z → 2026-08-31 00:00Z
- next-d0-10: 2026-08-31 00:00Z → 2026-09-01 00:00Z

The final endpoint is exactly the SF4 prospective boundary. No next-D0 source request may cross into September 1.

## Frozen source contract

- BTCUSDT USD-M futures
- 1m source candles
- Binance public USD-M daily aggTrades archive with checksum verification
- price bucket: 5.0
- dedicated namespace: `sfv2_next_d0_low_turnover_v1`
- exact candidate catalog SHA: `0aa793ca70ba8719486ba6edae314c77803e1b87884665d17ec88019ec71654a`

The old M5 development workflow remains untouched and continues to reject data outside its original July–August-15 development range. The next campaign uses a separate workflow and the new historical-window guard rather than weakening that old boundary.

## Evidence meaning

These windows are D0 discovery evidence only. They are not hidden confirmation, not OOS, and not verification. Once their performance is inspected they become contaminated/inspected discovery evidence and must be added to future search-history boundaries.

## Next gate

Materialize all ten frozen windows, record exact workflow IDs and feature CSV SHA-256 values in one immutable dataset receipt, validate all files/provenance, and only then create a separate bounded D0 performance authorization. D1, Frozen OOS, SF4, Demo promotion, live and real execution remain closed.
