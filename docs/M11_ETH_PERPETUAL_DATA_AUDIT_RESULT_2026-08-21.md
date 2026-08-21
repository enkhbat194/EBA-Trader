# M11 ETHUSDT USD-M Perpetual Historical Data Audit Result — 2026-08-21

## Decision

`M11_ETH_PERPETUAL_DATA_AUDIT_PASS`

The first complete frozen M11 audit qualified the exact ETHUSDT USD-M perpetual 15m Binance Vision source for later, separately frozen cross-asset research.

This is a data-eligibility PASS only. M11 computed no BTC forward returns, ETH/BTC correlations, lead-lag statistics, trading signals, PnL, risk sizing, AI outputs, or live execution evidence.

2025 OOS remains `LOCKED_NOT_ACCESSED`.

## Provenance and verification

- Source: official Binance Vision USD-M perpetual monthly `ETHUSDT/15m` archives
- Frozen window: `2021-01-01T00:00:00Z` to `2025-01-01T00:00:00Z` exclusive
- Authoritative GitHub Actions run: `32437837012`
- Evidence artifact ID: `9431376987`
- Evidence JSON SHA-256: `bdb2128025a17ef88a47aedcaceaf16fd6df474ec915a2c0836b29e86c75807d`
- Uploaded artifact ZIP SHA-256: `30623113c321601a0041a020d3d6ab2da496b5d7c84b4f4de0c9716ae8feb8e2`
- Normalized ETHUSDT USD-M 15m CSV SHA-256: `69855dcaf2f34c2a529ddb7f83964fa61b39ed0a27ae8796a6c0eaafd5b744f5`
- Full deterministic pytest suite before acquisition: PASS
- Ruff before acquisition: PASS
- Frozen-contract verification before acquisition: PASS

## Source and normalized dataset

| Metric | Result |
|---|---:|
| Expected monthly archives | 48 |
| Present archives | 48 |
| Checksum-verified archives | 48 |
| Parse-error archives | 0 |
| Source rows | 140,256 |
| Accepted unique rows | 140,256 |
| Expected 15m slots | 140,256 |
| Coverage | 100.000000% |
| Missing slots | 0 |
| Maximum missing run | 0 bars |
| Exact duplicate rows | 0 |
| Conflicting duplicate timestamps | 0 |
| Invalid rows | 0 |
| Alignment violations | 0 |
| Close-time violations | 0 |
| Numeric/activity integrity violations | 0 |

First timestamp and last timestamp both matched the frozen contract exactly.

## Frozen gates

All 14 frozen PASS gates passed:

1. 48/48 monthly archives exist;
2. 48/48 official checksums verified;
3. no monthly parse errors;
4. no conflicting duplicate timestamps;
5. exact first timestamp;
6. exact last timestamp;
7. unique strictly increasing timestamps;
8. all open timestamps 15m-aligned;
9. exact close-time semantics;
10. OHLC and futures activity numeric integrity;
11. coverage >= 99.95%;
12. maximum missing run <= 12 bars;
13. normalized row count <= expected;
14. 2025 OOS locked.

## Required action

M11 is complete and should not be rerun as a search cycle. Preserve the normalized dataset SHA-256 and source manifest as the admitted cross-asset derivatives input.

The next cycle may freeze a small, causal cross-asset edge-discovery search using this ETHUSDT USD-M perpetual 15m input together with the already-frozen BTCUSDT Spot development outcome data. The search space and statistical gates must be fixed before any BTC forward returns are evaluated.

M11 PASS does not authorize trading. 2025 remains untouched.
