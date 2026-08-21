# EBA-Trader Project State

Updated: 2026-08-21
Current research branch at this checkpoint: `m11-eth-perpetual-data-audit`

This file is the cross-chat continuity checkpoint. Read it before starting or modifying a later research cycle.

## Non-negotiable research policy

- BTCUSDT Spot remains the intended outcome/execution market unless a later frozen contract explicitly changes it.
- 2025-01-01 through 2026-01-01 is the true frozen OOS holdout and remains `LOCKED_NOT_ACCESSED`.
- 2024 has already been observed in repeated development cycles. Treat it only as reused development challenge data, never as pristine OOS.
- Rejected frozen cycles are not retuned, sign-flipped, filtered, or rescued after results are observed.
- Search spaces, thresholds, horizons, costs, gates and multiple-testing rules are frozen before forward-return evidence is computed.
- Risk sizing and live execution are blocked until a deterministic signal/edge family earns promotion under its frozen research contract.
- AI is excluded from signal discovery and may not override deterministic risk controls.
- NO_TRADE is a valid outcome.

## Completed research history

### M2 / Trend V1

Decision: `REJECT_DEVELOPMENT_CYCLE`. The original trend strategy failed development economics and robustness and is retired.

### M3 / Trend V2

Decision: `REJECT_TREND_V2_SIGNAL_CYCLE`. Primary 2024 result: -17.53% return, -22.90% maximum drawdown, 101 trades, 0.612 profit factor, negative expectancy. Risk-sized layer was not run.

### M4 / V3 Bull Pullback Recovery

Decision: `REJECT_V3_SIGNAL_CYCLE`. Primary 2024 result: -13.73% return, -14.64% maximum drawdown, 79 trades, 0.612 profit factor, -$1.74/trade expectancy. Neighborhood positive expectancy: 0/9. Rolling positive-expectancy folds: 4/30. Risk-sized layer was not run.

### M5 / Price-Volume Edge Discovery V1

Decision: `NO_STABLE_EDGE_FOUND`. Frozen search: 24 candidates × 3 horizons = 72 tests. Discovery-passing horizons: 0/72. 2024 challenge-passing horizons: 0/72.

### M6 / Derivatives Historical Data Audit

Decision: `M6_DERIVATIVES_DATA_AUDIT_FAIL` for the full four-source contract. Funding history and USD-M perpetual futures 15m price/activity individually passed. Premium-index, index-price and full cross-source alignment failed their frozen gates.

### M7 / Funding + Futures Edge Discovery

Decision: `NO_STABLE_DERIVATIVES_EDGE_FOUND`. Frozen search: 12 candidates × 3 horizons = 36 tests. Discovery passing: 0/36. Final discovery + reused-2024 challenge passing: 0/36.

### M8 / Alternative Derivatives Historical Data Audit

Decision: `M8_ALT_DERIVATIVES_DATA_AUDIT_FAIL` for the full audit. Binance USD-M 5m metrics failed; Bybit official endpoints were unavailable on the authoritative runner; liquidationSnapshot was incomplete; Binance USD-M bookDepth 2023-2024 was `PARTIAL_WINDOW_ELIGIBLE` only.

### M9 / BookDepth Microstructure Edge Discovery

Decision: `NO_STABLE_MICROSTRUCTURE_EDGE_FOUND`.

Authoritative evidence:
- run `32435682751`;
- artifact `9430751063`;
- evidence SHA-256 `2d603e445be459f414973b2909b356622ab98042a678fc590027454a343814e7`;
- feature SHA-256 `3d51661c5513af127dfedb963884b44da350742bea31fa4f30e3ae27a1a8311d`.

Source quality: 728/731 checksum-verified bookDepth days, 2,068,585 usable snapshots, 49,998 standardized causal 15m feature bars. Frozen search: 8 × 3 = 24 tests; discovery 0/24, challenge 0/24.

### M10 / ETHUSDT Spot Cross-Asset Historical Data Audit

Decision: `M10_CROSS_ASSET_DATA_AUDIT_FAIL`.

Authoritative evidence:
- run `32437273137`;
- artifact `9431194682`;
- evidence SHA-256 `385a6355c224f15b4f1e48cd86eba09fb81f69de292ea363a4563e4df2e34fdb`;
- normalized SHA-256 `dca519027cf7473307d05a572073f31c310284a20564fd20cf82de2fd332b8ef`.

All 48 monthly archives/checksums existed, but frozen data gates failed: 5 close-time violations; coverage 140,181/140,256 = 99.946526% below 99.95%; maximum missing run 19 bars above 12. M10 is retired and may not be repaired/interpolated or rescued by loosening gates.

### M11 / ETHUSDT USD-M Perpetual Historical Data Audit

Decision: `M11_ETH_PERPETUAL_DATA_AUDIT_PASS`.

This was data eligibility only; no BTC forward returns, correlations, lead-lag, strategy, risk, AI or live execution were computed.

Authoritative evidence:
- run `32437837012`;
- artifact `9431376987`;
- evidence SHA-256 `bdb2128025a17ef88a47aedcaceaf16fd6df474ec915a2c0836b29e86c75807d`;
- normalized ETHUSDT USD-M perpetual 15m SHA-256 `69855dcaf2f34c2a529ddb7f83964fa61b39ed0a27ae8796a6c0eaafd5b744f5`.

All 14 frozen gates passed: 48/48 archives, 48/48 checksums, 140,256/140,256 accepted rows, 100% coverage, zero missing slots, zero gaps, zero duplicates/conflicts, zero alignment/close-time/numeric-integrity violations. This exact dataset is admitted as a cross-asset derivatives input for a separately frozen edge-discovery cycle.

## Current conclusion

No deterministic BTC trading edge has yet earned promotion to a risk-sized strategy. The correct system state remains research-only / NO_TRADE.

M11 changes one important thing: there is now a clean, fully reproducible external ETH derivatives dataset available for materially new cross-asset research. It does not itself prove predictive value.

## Next allowed research direction

Proceed to **M12 Cross-Asset ETH→BTC Edge Discovery**, but freeze its feature/search space before computing BTC forward returns.

Required structure:

1. Use the exact M11 ETHUSDT USD-M perpetual 15m normalized dataset and the existing frozen BTCUSDT Spot development data only.
2. Discovery 2021-2023; reused development challenge 2024; 2025 remains locked.
3. Keep the search space small and causal: ETH impulse, BTC-vs-ETH relative movement/dispersion, and limited ETH activity-confirmation states.
4. Use next-open BTC diagnostic entry, frozen 1h/4h/12h horizons, Base 30 bps and Severe 70 bps costs, support gates, quarterly/year stability and BH-FDR multiple-testing control.
5. Record every test. No after-result threshold/horizon/sign/filter rescue.
6. Only a candidate surviving discovery and 2024 challenge may become a later strategy hypothesis. Risk sizing remains blocked during M12.
