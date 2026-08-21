# EBA-Trader Project State

Updated: 2026-08-21
Current research branch at this checkpoint: `m15-market-neutral-basis-convergence`

This file is the cross-chat continuity checkpoint. Read it before starting or modifying a later research cycle.

## Non-negotiable research policy

- BTCUSDT Spot is the intended directional execution market unless a later frozen contract explicitly changes it.
- 2025-01-01 through 2026-01-01 is the true frozen OOS holdout and remains `LOCKED_NOT_ACCESSED`.
- 2024 has already been observed repeatedly and is reused development challenge data only, never pristine OOS.
- Rejected frozen cycles are not retuned, sign-flipped, filtered, cost-relaxed, or rescued after results are observed.
- Search spaces, thresholds, horizons, costs, model hyperparameters, gates, and multiple-testing rules are frozen before evidence.
- Deterministic Risk Engine remains superior to any future AI/ML/router layer.
- Risk sizing and live execution are blocked until a separately frozen edge earns promotion.
- NO_TRADE is a valid system state.

## Completed research history

### M2-M5 / Directional strategy and Price-Volume discovery
M2 Trend V1, M3 Trend V2, and M4 V3 were rejected. M5 Price-Volume Edge Discovery tested 72 frozen horizon tests and promoted none.

### M6-M9 / Derivatives and microstructure
M6 full derivatives data contract failed although BTC funding and USD-M perpetual 15m individually passed. M7 Funding + Futures Edge Discovery promoted 0/36. M8 alternative-derivatives audit did not qualify the full source set; BookDepth 2023-2024 alone was partial-window eligible. M9 BookDepth Microstructure promoted 0/24. M9 run `32435682751`, artifact `9430751063`.

### M10-M12 / ETH cross-asset
M10 ETHUSDT Spot audit failed its frozen integrity gates. M11 ETHUSDT USD-M perpetual audit passed with 140,256/140,256 15m bars and normalized SHA-256 `69855dcaf2f34c2a529ddb7f83964fa61b39ed0a27ae8796a6c0eaafd5b744f5`. M12 ETH→BTC Cross-Asset Discovery promoted 0/24; run `32438774152`, artifact `9431703188`, evidence SHA `d79c8549ed9731cce081dc2957ad9db2f9a709b76ce1e6aed525f81be1a859c4`.

### M13 / Supervised ML Edge Engine
Decision: `NO_STABLE_ML_EDGE_FOUND`.

- 19 causal features;
- LogisticRegression + HistGradientBoosting;
- 0.60/0.65 probability gates;
- 4/16/48-bar horizons;
- 12 frozen configs;
- walk-forward discovery 2021→2022 and 2021-2022→2023;
- discovery pass 0/12, challenge pass 0/12;
- run `32446152844`, artifact `9434173433`;
- evidence SHA `84f39d0619ef96f668df34ca178680a3d84bb2f1f227dfab7c16cdb0910d5859`.

Closest `logistic_p65_h16` had positive Base-net but failed Severe economics, PF and FDR. Retired without rescue.

### M14 / Market-Neutral Funding Carry
Decision: `NO_STABLE_FUNDING_CARRY_EDGE_FOUND`.

- 1:1 long BTC Spot + short BTC USD-M perpetual;
- no leverage/naked short/overlap;
- funding thresholds 1/3/5 bps × 3/9 funding-record holds = 6 configs;
- discovery pass 0/6, challenge pass 0/6;
- run `32446970715`, artifact `9434444012`;
- evidence SHA `c5bd418a60260fb1619f8d0f563bf7ff93a1d66ee76525051df5f0c4bda136ec`.

Closest 5bp/9-record observation had +0.01499% mean Base-net but negative Severe mean, negative median, weak year support and q=1.0. Retired without rescue.

### M15 / Market-Neutral Basis Convergence
Decision: **`NO_STABLE_BASIS_CONVERGENCE_EDGE_FOUND`**.

Frozen mechanism:
- 1:1 long BTC Spot + short BTC USD-M perpetual;
- signal from completed 15m `perp_close / spot_close - 1`;
- entry thresholds 75/125/200 bps;
- fixed convergence exit <=10 bps, executed next open;
- max holds 96/288/672 bars;
- funding included only for `entry_time < funding_time < exit_time`;
- 9 frozen configs;
- Base/Severe friction 15/35 bps per side per leg.

Authoritative evidence:
- source commit `ad9d5bd2ee2f2d84295eb8c8cb4aadde90d8c71a`;
- run `32449012036`;
- artifact `9435060914`;
- evidence SHA-256 `4bd98328539c9d75f0e17839a631ab80c05c9ee14222d7b144f75ff8c4ae0559`;
- artifact ZIP SHA-256 `1b60ed9657f29487f0fd4ba150516578ce7bd56e07222cd4d8019cf991ee7ca7`;
- freeze / repo-wide pytest / Ruff PASS.

Result:
- discovery pass 0/9;
- challenge pass 0/9;
- basis candidate 0;
- 125bp and 200bp configs produced zero discovery trades;
- 75bp configs produced the same 5 trades, all in 2021, all converging before the shortest hold;
- those 5 trades had +0.157798% mean Base-net, +0.170301% median Base-net, 100% Base win rate, q=0.0002695, but mean Severe-net was -0.245961%; 2022/2023 had zero trades.

M15 therefore failed support/year stability and Severe-cost economics despite the small attractive 2021 cluster. It is retired. Do not lower basis thresholds/costs or select only the 2021 observations after the fact.

## Current system conclusion

No tested directional, price-volume, derivatives-flow, microstructure, cross-asset, supervised-ML, perpetual-funding carry, or perpetual-basis convergence mechanism has earned promotion.

Current state:
- research status: `NO_PROMOTABLE_EDGE_FOUND`;
- trading state: `NO_TRADE`;
- risk-sized strategy: blocked;
- live AI/ML signal layer: blocked;
- naked short authority: blocked;
- market-neutral live execution: blocked;
- live execution overall: blocked;
- 2025 OOS: `LOCKED_NOT_ACCESSED`.

## Next allowed action

Do not rescue M15 and do not continue arbitrary threshold searches on perpetual basis.

A materially different structural mechanism may still be researched if justified before outcome inspection. A particularly different next candidate is **dated/quarterly delivery-futures cash-and-carry**, where convergence is contractually tied to expiry rather than assumed from a perpetual basis. That requires a separate historical delivery-futures data provenance audit before any profitability test.

Operational product work may also continue in paper/shadow mode: exchange connectivity, dashboard, deterministic Risk Engine, kill switch, execution simulator, accounting, monitoring, and strategy-plugin architecture.

Until a separately validated edge exists, the correct autonomous decision remains `NO_TRADE`.
