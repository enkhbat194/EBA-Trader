# EBA-Trader Project State

Updated: 2026-08-21
Current research branch at this checkpoint: `m16-delivery-futures-data-audit`

This file is the cross-chat continuity checkpoint. Read it before starting or modifying a later research cycle.

## Non-negotiable research policy

- 2025-01-01 through 2026-01-01 is the true frozen OOS holdout and remains `LOCKED_NOT_ACCESSED`.
- 2024 has already been observed repeatedly and is reused development challenge data only, never pristine OOS.
- Rejected frozen cycles are not retuned, sign-flipped, filtered, cost-relaxed, or rescued after results are observed.
- Search spaces, thresholds, horizons, costs, model hyperparameters, gates, and multiple-testing rules are frozen before evidence.
- A data-audit PASS qualifies a source only; it does not establish profitability.
- Deterministic Risk Engine remains superior to any future AI/ML/router layer.
- Risk sizing and live execution are blocked until a separately frozen edge earns promotion.
- NO_TRADE is a valid system state.

## Completed research history

### M2-M5 / Directional strategy and price-volume discovery
M2 Trend V1, M3 Trend V2, and M4 V3 were rejected. M5 Price-Volume Edge Discovery tested 72 frozen horizon tests and promoted none.

### M6-M9 / Derivatives and microstructure
M6 full derivatives data contract failed although BTC funding and USD-M perpetual 15m individually passed. M7 Funding + Futures Edge Discovery promoted 0/36. M8 alternative-derivatives audit did not qualify the full source set; BookDepth 2023-2024 alone was partial-window eligible. M9 BookDepth Microstructure promoted 0/24.

### M10-M12 / ETH cross-asset
M10 ETHUSDT Spot audit failed its frozen integrity gates. M11 ETHUSDT USD-M perpetual audit passed with 140,256/140,256 15m bars and normalized SHA-256 `69855dcaf2f34c2a529ddb7f83964fa61b39ed0a27ae8796a6c0eaafd5b744f5`. M12 ETH→BTC Cross-Asset Discovery promoted 0/24.

### M13 / Supervised ML Edge Engine
Decision: `NO_STABLE_ML_EDGE_FOUND`.

- 19 causal features;
- LogisticRegression + HistGradientBoosting;
- 0.60/0.65 probability gates;
- 4/16/48-bar horizons;
- 12 frozen configs;
- discovery pass 0/12, challenge pass 0/12;
- run `32446152844`, artifact `9434173433`;
- evidence SHA `84f39d0619ef96f668df34ca178680a3d84bb2f1f227dfab7c16cdb0910d5859`.

### M14 / Market-Neutral Funding Carry
Decision: `NO_STABLE_FUNDING_CARRY_EDGE_FOUND`.

- 1:1 long BTC Spot + short BTC USD-M perpetual;
- funding thresholds 1/3/5 bps × 3/9 funding-record holds = 6 configs;
- discovery pass 0/6, challenge pass 0/6;
- run `32446970715`, artifact `9434444012`;
- evidence SHA `c5bd418a60260fb1619f8d0f563bf7ff93a1d66ee76525051df5f0c4bda136ec`.

### M15 / Market-Neutral Perpetual Basis Convergence
Decision: `NO_STABLE_BASIS_CONVERGENCE_EDGE_FOUND`.

- 9 frozen basis/hold configs;
- discovery pass 0/9, challenge pass 0/9;
- run `32449012036`, artifact `9435060914`;
- evidence SHA `4bd98328539c9d75f0e17839a631ab80c05c9ee14222d7b144f75ff8c4ae0559`.

The 75-bps family produced only 5 trades, all in 2021. They were Base-profitable but Severe-cost negative and had zero 2022/2023 support. M15 is retired without rescue.

### M16 / Quarterly Delivery Futures Historical Data Audit
Decision: **`M16_DELIVERY_DATA_AUDIT_PASS`**.

This was data provenance only. No profitability calculation was allowed.

Authoritative evidence:
- source commit `c0a63a8f21c69bf062cf3725751171415d06a739`;
- run `32449978355`;
- artifact `9435350726`;
- evidence SHA-256 `b966f290ddc0652fbeeaa453bb33a86ffae15695c80fd321f9173e5c42e86745`;
- artifact ZIP SHA-256 `794ac8b1bf047269da7ea29e5c121236e383acccbcec01d5f256a6513f6f22e9`;
- freeze / repo-wide pytest / Ruff PASS;
- 2025 OOS remained locked.

Family results:
- USD-M quarterly `BTCUSDT_YYMMDD`: **`DELIVERY_DATA_ELIGIBLE`**. All 16/16 contracts passed. Every contract had 2,880/2,880 accepted 15m bars, 100% coverage, max gap 0, and final data 15 minutes before delivery.
- COIN-M quarterly `BTCUSD_YYMMDD`: **`DELIVERY_DATA_NOT_ELIGIBLE`**. 15/16 passed, but `BTCUSD_230929` had 2,720/2,880 bars, 94.4444% coverage and a 160-bar missing run, failing the frozen coverage and gap gates.

M16 therefore qualifies **USD-M quarterly delivery futures only** for a separate profitability cycle. It does not establish an edge.

## Current system conclusion

No completed profitability cycle through M15 has earned promotion. M16 materially improves the research position by qualifying a clean USD-M quarterly delivery-futures data family, but profitability has not yet been tested.

Current state:
- research status: `M16_USDM_DELIVERY_DATA_ELIGIBLE_AWAITING_PROFITABILITY_STUDY`;
- trading state: `NO_TRADE`;
- risk-sized strategy: blocked;
- live AI/ML signal layer: blocked;
- naked short authority: blocked;
- market-neutral live execution: blocked;
- live execution overall: blocked;
- 2025 OOS: `LOCKED_NOT_ACCESSED`.

## Next allowed action

Open a separate frozen **USD-M quarterly cash-and-carry / expiry-convergence profitability cycle** using only the exact M16-qualified contract data and frozen BTC Spot development data.

The next contract must be frozen before outcome inspection. It must explicitly define entry timing, exit timing before or at expiry, hedge ratio, capital denominator, transaction costs, margin-safety treatment, statistical unit, 2021-2023 discovery gates, reused-2024 challenge gates, and the immutable no-rescue rule.

Do not use COIN-M in that cycle. Do not access 2025.
