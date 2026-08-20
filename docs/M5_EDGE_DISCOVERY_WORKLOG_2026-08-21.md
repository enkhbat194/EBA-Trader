# M5 Edge Discovery Work Log — 2026-08-21

## Branch

`edge-discovery-engine`

Base commit:

`dfbddf944a462d499e4a9917ad842794c4319266`

## Why M5 exists

Trend V1, Trend V2, and V3 all failed development. M5 deliberately stops inventing another trading
strategy first. It searches for stable event-conditioned BTC forward-return behavior before any new
entry/exit/risk hypothesis is allowed.

## Frozen Price/Volume V1 search

Completed:

- [x] finite protocol frozen in `docs/M5_EDGE_DISCOVERY_PROTOCOL.md`;
- [x] portable protocol SHA-256 freeze manifest;
- [x] exactly 24 predeclared event candidates;
- [x] exactly 3 forward horizons: 4, 16, 48 bars;
- [x] exactly 72 discovery hypothesis tests;
- [x] next-open causal forward-return semantics;
- [x] 4-bar event cooldown;
- [x] source-gap-reset ATR/VWAP/median-volume feature handling;
- [x] base and severe cost stress;
- [x] per-year 2021/2022/2023 stability checks;
- [x] daily aggregation for dependence-aware screening;
- [x] Benjamini-Hochberg FDR correction across all 72 tests;
- [x] fixed 2024 development-challenge gates;
- [x] separate long-edge vs NO_TRADE-veto classification;
- [x] no automatic V4 generation;
- [x] deterministic tests added;
- [x] Windows/Bash one-command runners added;
- [x] GitHub Actions pytest/Ruff workflow added.

## Information boundary

- Discovery: 2021-01-01 through 2024-01-01 exclusive.
- Challenge: 2024-01-01 through 2025-01-01 exclusive.
- 2025 OOS: `LOCKED_NOT_ACCESSED`.
- Funding/basis/OI/news/AI: excluded from Price/Volume V1.

## Next strict step

1. Run the full repository pytest suite on Python 3.12.
2. Run Ruff.
3. Fix implementation defects only; do not change the frozen M5 candidate set or thresholds.
4. Commit the green implementation.
5. On a clean tracked tree run `scripts/run_edge_discovery.ps1` on Windows.
6. Preserve the first complete M5 JSON report; the runner refuses to overwrite it.
7. If no candidate survives, record `NO_STABLE_EDGE_FOUND` instead of inventing a rescue filter.
8. If one or more candidates survive, audit the evidence before writing any V4 strategy contract.
9. Do not access 2025.
