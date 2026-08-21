# EBA-Trader Project State

Updated: 2026-08-21
Current research branch at this checkpoint: `m9-bookdepth-microstructure-edge`

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

Decision: `REJECT_DEVELOPMENT_CYCLE`.

The original trend strategy failed development economics and robustness. It is retired and must not be rescued.

### M3 / Trend V2

Decision: `REJECT_TREND_V2_SIGNAL_CYCLE`.

Primary 2024 result: -17.53% return, -22.90% maximum drawdown, 101 trades, 0.612 profit factor, negative expectancy. Gates: 9 PASS / 14 FAIL / 13 BLOCKED. Risk-sized layer was not run.

### M4 / V3 Bull Pullback Recovery

Decision: `REJECT_V3_SIGNAL_CYCLE`.

Primary 2024 result: -13.73% return, -14.64% maximum drawdown, 79 trades, 0.612 profit factor, -$1.74/trade expectancy. Neighborhood positive expectancy: 0/9. Rolling positive-expectancy folds: 4/30. Risk-sized layer was not run.

### M5 / Price-Volume Edge Discovery V1

Decision: `NO_STABLE_EDGE_FOUND`.

Frozen search: 24 candidates × 3 horizons = 72 tests. Discovery-passing horizons: 0/72. 2024 challenge-passing horizons: 0/72. No long edge or no-trade-veto candidate earned promotion.

### M6 / Derivatives Historical Data Audit

Decision: `M6_DERIVATIVES_DATA_AUDIT_FAIL` for the full four-source contract.

Individually eligible families:
- funding history: PASS;
- USD-M perpetual futures 15m price/activity: PASS.

Rejected under the frozen contract:
- premium-index 15m: FAIL coverage/gap gates;
- index-price 15m: FAIL coverage/gap gates;
- full cross-source alignment: FAIL.

### M7 / Funding + Futures Edge Discovery

Decision: `NO_STABLE_DERIVATIVES_EDGE_FOUND`.

Frozen search: 12 candidates × 3 horizons = 36 tests. Discovery passing: 0/36. Final discovery + reused-2024 challenge passing: 0/36. No stable long edge or no-trade-veto edge was found.

### M8 / Alternative Derivatives Historical Data Audit

Decision: `M8_ALT_DERIVATIVES_DATA_AUDIT_FAIL` for the full audit.

Key outcomes:
- Binance USD-M 5m metrics: FAIL frozen integrity gates;
- Bybit primary families: unavailable on the authoritative GitHub runner because official endpoints returned HTTP 403; not promoted;
- liquidationSnapshot: excluded for incomplete official archive history;
- Binance USD-M bookDepth 2023-2024: `PARTIAL_WINDOW_ELIGIBLE` and permitted only under a separately frozen shorter-window study.

### M9 / BookDepth Microstructure Edge Discovery

Decision: `NO_STABLE_MICROSTRUCTURE_EDGE_FOUND`.

Authoritative evidence:
- GitHub Actions run: `32435682751`;
- evidence artifact ID: `9430751063`;
- evidence SHA-256: `2d603e445be459f414973b2909b356622ab98042a678fc590027454a343814e7`;
- feature dataset SHA-256: `3d51661c5513af127dfedb963884b44da350742bea31fa4f30e3ae27a1a8311d`.

Source quality:
- 728/731 checksum-verified daily bookDepth files;
- 99.5896% daily file coverage;
- 2,068,585 complete/usable snapshots;
- 49,998 standardized causal 15m feature bars;
- invalid rows: 0;
- conflicting rows: 0.

Frozen search: 8 candidates × 3 horizons = 24 tests. Discovery passing: 0/24. Challenge passing: 0/24. No long edge or no-trade-veto candidate earned promotion. M9 is retired; do not change thresholds or filters to rescue it.

## Current conclusion

No deterministic BTC trading edge has yet earned promotion to a risk-sized strategy. The correct system state is research-only / NO_TRADE, not live deployment.

The repeated failures are informative: simple Spot trend/pullback logic, broad price-volume threshold discovery, funding/futures threshold states, and the tested signed-side BookDepth imbalance family have not demonstrated a stable cost-robust edge under the frozen gates.

## Next allowed research direction

Do not create a V4 strategy from the failed observations above.

The next cycle should introduce materially new information before any new strategy hypothesis. The preferred next family is **cross-asset market-state / lead-lag information**, beginning with a no-forward-return historical data audit of an external crypto market such as ETHUSDT Spot 15m over development years only.

Recommended sequence:

1. M10 Cross-Asset Historical Data Audit — qualify the exact external 15m source, coverage, gaps, timestamps and reproducible SHA-256 without computing BTC forward returns.
2. Only if M10 passes, freeze a separately versioned cross-asset edge-discovery contract before looking at BTC outcomes.
3. Keep the candidate family small and causal: predeclared ETH impulse / BTC-ETH relative move / dispersion states, with multiple-testing control and 2024 reused-development challenge.
4. Only a candidate that survives costs, support, stability and FDR may be converted into a later strategy hypothesis.
5. Keep 2025 untouched throughout development.
