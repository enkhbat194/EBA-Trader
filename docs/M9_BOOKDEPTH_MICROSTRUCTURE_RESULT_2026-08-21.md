# M9 Book-Depth / Microstructure Edge Discovery Result — 2026-08-21

## Decision

`NO_STABLE_MICROSTRUCTURE_EDGE_FOUND`

The first complete frozen M9 evidence run found no candidate/horizon that passed the predeclared 2023 discovery gates. Therefore no candidate could be promoted through the reused 2024 development challenge. No threshold, candidate, horizon, cooldown, cost assumption, support gate, or quarter gate may be changed to rescue this cycle.

2025 OOS remains `LOCKED_NOT_ACCESSED`.

## Provenance and verification

- Frozen search: 8 candidates × 3 horizons = 24 hypothesis tests
- Discovery: 2023-01-01 to 2024-01-01 exclusive
- Reused development challenge: 2024-01-01 to 2025-01-01 exclusive
- Authoritative GitHub Actions run: `32435682751`
- Evidence artifact ID: `9430751063`
- Evidence JSON SHA-256: `2d603e445be459f414973b2909b356622ab98042a678fc590027454a343814e7`
- Feature dataset SHA-256: `3d51661c5513af127dfedb963884b44da350742bea31fa4f30e3ae27a1a8311d`
- Frozen Spot research SHA-256: `253c6ae35856e58e35df17eaa71caeea5caaa3681c38dd7214a2872afccd8d63`
- Frozen Spot challenge SHA-256: `3a96b6b668cfacb0fefabb8665675d4ca589cc712b0681fb57e7a13356eda0f2`
- Full deterministic pytest suite before evidence: PASS
- Ruff before evidence: PASS
- Frozen-contract verification before evidence: PASS
- AI module: excluded
- Risk sizing: excluded
- Live execution: excluded

The first evidence workflow attempt did not produce a research result because the GitHub runner did not contain the frozen Spot cache files. The workflow was fixed to seed only the exact pre-existing frozen Spot inputs from the source and require their frozen SHA-256 values before research could run. Run `32435682751` is the first complete authoritative M9 evidence run.

## BookDepth source audit

| Metric | Result |
|---|---:|
| Expected daily files | 731 |
| Existing/checksum-verified files | 728 |
| Daily file coverage | 99.5896% |
| Missing daily files | 3 |
| Invalid rows | 0 |
| Conflicting rows | 0 |
| Complete snapshots | 2,068,585 |
| Usable snapshots | 2,068,585 |
| Raw 15m feature bars | 68,832 |
| Standardized causal feature bars | 49,998 |
| Source audit status | PASS |

Missing source days were preserved as missing with no imputation:
- 2023-02-08
- 2023-02-09
- 2024-04-18

## Frozen search result

- Discovery-passing candidate/horizons: `0 / 24`
- Challenge-passing candidate/horizons: `0 / 24`
- `LONG_EDGE_CANDIDATE`: none
- `NO_TRADE_VETO_CANDIDATE`: none

The strongest discovery observation by Base-net mean was still negative:

- candidate: `notional_1_imbalance_rising`
- horizon: 48 bars / 12 hours
- discovery events: 604
- discovery Base-net mean: -0.2071%
- discovery Severe-net mean: -0.6071%
- discovery median Base-net: -0.2656%
- discovery baseline uplift: approximately -0.0001 percentage points
- BH-FDR q-value: 1.0
- 2024 challenge events: 1,193
- 2024 Base-net mean: -0.1421%
- 2024 Severe-net mean: -0.5421%

This is not a low-support rejection. The M9 family had ample events and source coverage, but the predeclared signed-side BookDepth imbalance features did not show a stable cost-robust edge.

## Required action

Close M9 as rejected. Do not retune or rescue the frozen search. Do not open 2025 OOS. Any future cycle must be materially different rather than another threshold variation of the same M9 BookDepth imbalance features.
