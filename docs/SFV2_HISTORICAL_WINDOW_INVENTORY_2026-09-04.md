# Strategy Factory v2 — historical window inventory

Date: 2026-09-04

Authority: **RESEARCH_BOUNDARY_ONLY**. This inventory does not authorize D0 evaluation, D1, Frozen OOS, Demo promotion, live execution, or real execution.

## Purpose

The next low-turnover Strategy Factory campaign must not silently relabel previously inspected data as fresh, and it must never enter protected SF4 or Frozen OOS evidence. The canonical machine-readable inventory is `config/sfv2_historical_window_inventory_v1.json`; the fail-closed guard is `strategy_factory_v2_window_inventory.py`.

## Frozen facts

- First-cycle BTCUSDT Frozen OOS remains 2025-01-01 through 2026-01-01.
- The twelve original M5 development windows are recorded as **INSPECTED**. SF1 and the first Strategy Factory v2 D0 campaign reused that materialized development evidence, so these windows are not fresh evidence.
- The twelve SF2 and twelve SF3 development windows are also **INSPECTED**.
- The old 2026-08-01 smoke day is conservatively quarantined as inspected because the canonical M5 policy explicitly says that proof window was already inspected but does not freeze its exact subwindow in the current corpus. Blocking the whole UTC day is deliberately conservative and cannot create a false freshness claim.
- M5 Frozen OOS remains 2026-08-15 through 2026-08-22 and is an absolute block.
- SF4 prospective replication evidence from 2026-09-01 through 2026-09-13 is an absolute block for all other research.

## Guard semantics

`assert_discovery_window_allowed()` has only two modes:

1. default: rejects both protected evidence and any previously inspected overlap;
2. explicit inspected reuse: permits only `INSPECTED` / `INSPECTED_QUARANTINE` overlap and returns those exact range ids so a caller can persist contamination/search-history provenance.

`FROZEN_OOS` and `PROTECTED_SF4` remain blocked even when inspected reuse is requested.

`assert_no_known_research_overlap()` proves only absence of overlap with this inventory. It **does not** prove that an unlisted range is fresh, independent, statistically valid, or eligible for confirmation/OOS.

## Next gate

Before any next-campaign performance run, a separate immutable package must freeze both:

- the exact D0 dataset window/materialization identity; and
- the exact deterministic candidate catalog under the existing 128 raw / 32-per-family cap.

The next campaign remains DESIGN_ONLY until both freezes exist and the existing safety boundary is revalidated.
