# EBA-Trader Project State

Updated: 2026-08-21
Current research branch at this checkpoint: `m12-cross-asset-eth-btc-edge`

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
Decision: `REJECT_DEVELOPMENT_CYCLE`. Retired.

### M3 / Trend V2
Decision: `REJECT_TREND_V2_SIGNAL_CYCLE`. 2024 return -17.53%, MDD -22.90%, 101 trades, PF 0.612, negative expectancy. Risk layer not run.

### M4 / V3 Bull Pullback Recovery
Decision: `REJECT_V3_SIGNAL_CYCLE`. 2024 return -13.73%, MDD -14.64%, 79 trades, PF 0.612, -$1.74/trade. Neighborhood positive expectancy 0/9; rolling positive-expectancy folds 4/30. Risk layer not run.

### M5 / Price-Volume Edge Discovery
Decision: `NO_STABLE_EDGE_FOUND`. 24 candidates × 3 horizons = 72 tests; discovery 0/72, challenge 0/72.

### M6 / Derivatives Historical Data Audit
Decision: `M6_DERIVATIVES_DATA_AUDIT_FAIL` for the full contract. Funding and BTC USD-M perpetual 15m independently passed; premium/index/alignment failed.

### M7 / Funding + Futures Edge Discovery
Decision: `NO_STABLE_DERIVATIVES_EDGE_FOUND`. 12 × 3 = 36 tests; discovery 0/36, final 0/36.

### M8 / Alternative Derivatives Historical Data Audit
Decision: `M8_ALT_DERIVATIVES_DATA_AUDIT_FAIL`. BookDepth 2023-2024 alone was partial-window eligible; other audited families did not qualify under the frozen contract.

### M9 / BookDepth Microstructure Edge Discovery
Decision: `NO_STABLE_MICROSTRUCTURE_EDGE_FOUND`. 8 × 3 = 24 tests; discovery 0/24, challenge 0/24. Evidence run `32435682751`, artifact `9430751063`.

### M10 / ETHUSDT Spot Historical Data Audit
Decision: `M10_CROSS_ASSET_DATA_AUDIT_FAIL`. 48/48 checksums, but 5 close-time violations, 99.946526% coverage below frozen 99.95%, and max missing run 19 bars above 12. Retired without repair or relaxed gates. Evidence run `32437273137`, artifact `9431194682`.

### M11 / ETHUSDT USD-M Perpetual Historical Data Audit
Decision: `M11_ETH_PERPETUAL_DATA_AUDIT_PASS`.

- 48/48 archives and checksums;
- 140,256/140,256 15m bars;
- 100% coverage;
- zero missing slots/gaps/conflicts/alignment/close-time/numeric violations;
- normalized SHA-256 `69855dcaf2f34c2a529ddb7f83964fa61b39ed0a27ae8796a6c0eaafd5b744f5`;
- run `32437837012`, artifact `9431376987`.

### M12 / ETH→BTC Cross-Asset Edge Discovery
Decision: **`NO_STABLE_CROSS_ASSET_EDGE_FOUND`**.

Frozen research surface:
- 8 predeclared ETH-perpetual candidates;
- horizons 4/16/48 15m bars;
- 24 total discovery tests;
- Base/Severe costs 30/70 bps;
- >=10 bps unconditional BTC baseline uplift gate;
- yearly stability plus BH-FDR q<=0.10;
- discovery 2021-2023; reused challenge 2024.

Authoritative evidence:
- source commit `5a04bf92c0c12ac0c1afd324dc4eda928437be5f`;
- run `32438774152`;
- artifact `9431703188`;
- evidence SHA-256 `d79c8549ed9731cce081dc2957ad9db2f9a709b76ce1e6aed525f81be1a859c4`;
- artifact ZIP SHA-256 `dc2963a2774232612c59187e9de49a5d5dc246e0767bac29d543d908a473e8a6`.

Result:
- LONG_EDGE_CANDIDATE: 0;
- NO_TRADE_VETO_CANDIDATE: 0;
- discovery-passing horizons: 0/24;
- challenge-passing horizons: 0/24;
- all 24 discovery tests had negative mean Base-net signed return;
- all 24 discovery tests had BH-FDR q = 1.0.

M12 had ample support: candidate/horizon event counts were typically hundreds to thousands, so this is not merely a low-sample rejection. Some 2024 48-bar Base-net observations were positive, but their discovery tests failed and Severe-net challenge means remained negative. They are not promotable and cannot be selected after the fact.

M12 is retired. Do not tune its thresholds, signs, horizons, filters, costs, years, or challenge observations to rescue it.

## Current system conclusion

**No deterministic BTC edge has earned promotion.**

Current state:
- research status: `NO_PROMOTABLE_EDGE_FOUND`;
- trading state: `NO_TRADE`;
- risk-sized strategy: blocked;
- AI signal layer: excluded;
- short authority: not granted;
- live execution: blocked;
- 2025 OOS: `LOCKED_NOT_ACCESSED`.

M2-M12 have already tested multiple materially different deterministic information families: trend/pullback, BTC price-volume, derivatives funding/flow, BookDepth microstructure, and qualified ETH-perpetual cross-asset states. Repeatedly inventing M13/M14 threshold searches simply to obtain a positive backtest would increase data-mining risk rather than finish the system correctly.

## Next allowed action

Do **not** automatically start another strategy search.

The current research campaign is considered complete with `NO_PROMOTABLE_EDGE_FOUND`. A new research cycle may be opened only if a materially new market mechanism or independently justified data source is identified before outcome inspection.

Until then, preserve the deterministic infrastructure, keep 2025 untouched, and keep execution disabled / NO_TRADE. If the product is moved forward operationally, it should be paper/monitoring infrastructure only, not claimed profitable live trading.
