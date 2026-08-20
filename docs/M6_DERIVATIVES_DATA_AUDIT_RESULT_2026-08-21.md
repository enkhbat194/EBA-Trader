# M6 Derivatives Historical Data Audit Result — 2026-08-21

## Verdict

**`M6_DERIVATIVES_DATA_AUDIT_FAIL`**

The frozen full four-source audit did not pass. The audit criteria are not relaxed after observing
this result.

This is a data-eligibility verdict only. No strategy was tested, no trading edge was claimed, and no
risk/live layer was run.

## Reproducible acquisition

The first REST attempt from a GitHub-hosted Azure runner was blocked by Binance with HTTP 451 before
any audit report was produced. No proxy or geographic bypass was used.

The completed audit instead used Binance's official public `data.binance.vision` monthly USD-M
archives for the same source families. Every one of the 48 monthly ZIPs present for each of the four
families was verified against Binance Vision's published `.CHECKSUM` before parsing.

Completed source counts:

| Source | Rows | Verified monthly files | Missing monthly files | Audit |
|---|---:|---:|---:|---|
| Funding rate | 4,383 | 48 | 0 | PASS |
| Premium-index 15m | 139,582 | 48 | 0 | FAIL |
| Perpetual futures 15m | 140,256 | 48 | 0 | PASS |
| Index-price 15m | 139,103 | 48 | 0 | FAIL |

Expected 15m slots for 2021-01-01 through 2025-01-01 exclusive: **140,256**.

## Section results

### Funding — PASS

- records: **4,383**
- strict unique chronological order: PASS
- full audit-window edge checks: PASS
- finite / bounded rates: PASS
- median cadence: **8.0 hours**
- maximum observed cadence: approximately **8.000013 hours**
- frozen minimum records / cadence gates: PASS

Consolidated dataset SHA-256:
`73b9decde0d54a0609d55ccfd49131a6e825416b595d728457bb01a968b55fd6`

### Perpetual futures 15m — PASS

- rows: **140,256 / 140,256**
- coverage: **100.000%**
- maximum missing run: **0**
- timestamps / close times / OHLC: PASS
- volume / quote volume / trade count / taker-buy activity fields: PASS

Consolidated dataset SHA-256:
`3c97c9b59ded32595f129a480a23e920823c0edbbf2e4f32c5d66e5020e35947`

### Premium-index 15m — FAIL

- rows: **139,582 / 140,256**
- missing slots: **674**
- coverage: **99.51945%**
- frozen requirement: **>= 99.90%**
- maximum missing run: **384 × 15m = 96 hours**
- frozen maximum: **48 × 15m = 12 hours**

Monthly row deficits were observed in:
- 2021-07: 480 slots
- 2022-07: 2 slots
- 2022-10: 96 slots
- 2023-02: 96 slots

Consolidated dataset SHA-256:
`807eba68834c016e89358feb40ee3bd1457216fe6e3121e232c83af7e2bc7bfb`

### Index-price 15m — FAIL

- rows: **139,103 / 140,256**
- missing slots: **1,153**
- coverage: **99.17793%**
- frozen requirement: **>= 99.90%**
- maximum missing run: **192 × 15m = 48 hours**
- frozen maximum: **48 × 15m = 12 hours**

Monthly row deficits were observed in:
- 2022-04: 96 slots
- 2022-07: 576 slots
- 2022-10: 96 slots
- 2023-02: 192 slots
- 2023-04: 192 slots
- 2023-11: 1 slot

Consolidated dataset SHA-256:
`76201859297ec3ff18aa9a507e78ced7dd17b114ff097b8fb1529047f3b39603`

### Cross-source alignment — FAIL

- aligned premium + futures + index rows: **138,621**
- intersection coverage: **98.83427%**
- frozen requirement: **>= 99.80%**
- synthetic perpetual/index basis was finite on all aligned rows: PASS
- mean aligned synthetic basis: approximately **-0.00584%**
- observed aligned basis range: approximately **-2.8134% to +1.6334%**

The cross-source section fails because alignment coverage is below the frozen threshold, not because of
non-finite basis math.

## Provenance

Completed GitHub Actions historical audit:
- workflow run: `32422829081`
- source commit: `8a8b5c7d83d6be4bac69c8aea82c123f670e6e0f`
- Python: 3.12.14
- tracked worktree: clean
- evidence artifact ID: `9426328736`
- uploaded artifact ZIP SHA-256: `d241e991131a7e0d32dc514cc88aa63aabd943d7f2d79e79cc2add0887bb1a4d`

The exact evidence report and Binance Vision checksum manifest were uploaded together as the workflow
artifact `m6-derivatives-data-audit`.

## Research consequence

The full M6 four-source data contract is closed as **FAIL** and must not be rescued by weakening the
observed coverage/gap gates.

However, two source families independently passed their frozen data-quality gates before any edge
search:

1. funding-rate history;
2. perpetual-futures 15m price/activity data.

These passed data families may be considered in a **new, separately versioned and predeclared** edge
research cycle. The failed premium-index and index-price families are excluded from that next cycle.
Any new edge thresholds and candidate definitions must be frozen before looking at forward-return
results.

Open-interest statistics and Binance REST basis remain excluded for long-horizon research because of
their documented short retention windows.

## Holdout

**2025 OOS: `LOCKED_NOT_ACCESSED`**

No 2025 BTC data was downloaded, inspected, or used by this audit.
