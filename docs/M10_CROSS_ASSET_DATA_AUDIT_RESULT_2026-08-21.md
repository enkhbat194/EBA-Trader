# M10 Cross-Asset Historical Data Audit Result — 2026-08-21

## Decision

`M10_CROSS_ASSET_DATA_AUDIT_FAIL`

The first complete frozen M10 audit did not qualify ETHUSDT Spot 15m under the predeclared data-quality contract. The audit gates are not relaxed after observing the result.

This is a data-eligibility verdict only. M10 computed no BTC forward returns, no ETH/BTC correlation or lead-lag statistic, no trading signal, no PnL, no risk sizing, no AI output, and no live execution evidence.

2025 OOS remains `LOCKED_NOT_ACCESSED`.

## Provenance and verification

- Source: official Binance Vision Spot monthly `ETHUSDT/15m` archives
- Frozen window: `2021-01-01T00:00:00Z` to `2025-01-01T00:00:00Z` exclusive
- Expected monthly archives: 48
- Authoritative GitHub Actions run: `32437273137`
- Evidence artifact ID: `9431194682`
- Evidence JSON SHA-256: `385a6355c224f15b4f1e48cd86eba09fb81f69de292ea363a4563e4df2e34fdb`
- Uploaded artifact ZIP SHA-256: `8d0cb2fc53865243a2c709d4cc5d2bb518962ef41c99cb23a263037ad9eb23b3`
- Normalized ETHUSDT 15m CSV SHA-256: `dca519027cf7473307d05a572073f31c310284a20564fd20cf82de2fd332b8ef`
- Full deterministic pytest suite before acquisition: PASS
- Ruff before acquisition: PASS
- Frozen-contract verification before acquisition: PASS

## Source acquisition

All 48 expected monthly ZIP archives existed and all 48 matched Binance Vision's published `.CHECKSUM` files.

- monthly archives present: 48/48
- checksum-verified archives: 48/48
- monthly parse-error files: 0
- source rows: 140,186
- exact duplicate rows: 0
- conflicting duplicate timestamps: 0
- invalid rows: 0
- alignment violations: 0
- numeric-integrity violations: 0

## Normalized coverage

| Metric | Result | Frozen gate |
|---|---:|---:|
| Expected 15m slots | 140,256 | fixed |
| Accepted unique rows | 140,181 | <= expected |
| Missing slots | 75 | diagnostic |
| Coverage | 99.946526% | >= 99.95% |
| Maximum missing run | 19 bars / 4h45m | <= 12 bars / 3h |
| Close-time semantic violations | 5 | 0 |
| First timestamp | exact PASS | 2021-01-01 00:00 UTC |
| Last timestamp | exact PASS | 2024-12-31 23:45 UTC |

The eight normalized missing ranges were:

1. 2021-02-11 03:30 through 04:45 UTC — 6 bars
2. 2021-03-06 02:00 through 03:15 UTC — 6 bars
3. 2021-04-20 02:00 through 04:15 UTC — 10 bars
4. 2021-04-25 04:00 through 08:30 UTC — 19 bars
5. 2021-08-13 01:45 through 06:15 UTC — 19 bars
6. 2021-09-29 07:00 through 08:45 UTC — 8 bars
7. 2021-12-24 04:45 UTC — 1 bar
8. 2023-03-24 12:30 through 13:45 UTC — 6 bars

Five source rows also violated the frozen exact close-time semantics, one each in:
- 2021-02
- 2021-04
- 2021-08
- 2021-12
- 2023-03

They were not repaired or made eligible.

## Frozen gate result

PASS:
- 01 all 48 monthly archives exist
- 02 all 48 checksums verified
- 03 no monthly parse errors
- 04 no conflicting duplicate timestamps
- 05 exact first timestamp
- 06 exact last timestamp
- 07 unique strictly increasing timestamps
- 08 all open timestamps 15m-aligned
- 10 numeric integrity
- 13 normalized row count not above expected
- 14 2025 OOS locked

FAIL:
- 09 exact close-time semantics — 5 violations
- 11 coverage >= 99.95% — actual 99.946526%
- 12 maximum missing run <= 12 bars — actual 19 bars

## Required action

Close M10 as a failed frozen data-audit contract. Do not rescue it by weakening the coverage threshold, increasing the allowed missing-run length, repairing close times, interpolating missing ETH candles, or silently substituting another source inside M10.

ETHUSDT Spot 15m from this exact M10 source contract is not admitted to the next edge-discovery cycle.

A later research cycle may audit a materially separate source under a new predeclared contract before any BTC forward-return analysis. 2025 remains untouched.
