# EBA-Trader Project State

Updated: 2026-08-21
Current research branch at this checkpoint: `m14-market-neutral-funding-carry`

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

### M2 / Trend V1
Decision: `REJECT_DEVELOPMENT_CYCLE`.

### M3 / Trend V2
Decision: `REJECT_TREND_V2_SIGNAL_CYCLE`. 2024 return -17.53%, MDD -22.90%, 101 trades, PF 0.612, negative expectancy.

### M4 / V3 Bull Pullback Recovery
Decision: `REJECT_V3_SIGNAL_CYCLE`. 2024 return -13.73%, MDD -14.64%, 79 trades, PF 0.612, -$1.74/trade. Neighborhood positive expectancy 0/9; rolling positive-expectancy folds 4/30.

### M5 / Price-Volume Edge Discovery
Decision: `NO_STABLE_EDGE_FOUND`. 24 candidates × 3 horizons = 72 tests; discovery 0/72, challenge 0/72.

### M6 / Derivatives Historical Data Audit
Decision: `M6_DERIVATIVES_DATA_AUDIT_FAIL` for the full contract. Funding and BTC USD-M perpetual 15m independently passed; premium/index/alignment failed.

### M7 / Funding + Futures Edge Discovery
Decision: `NO_STABLE_DERIVATIVES_EDGE_FOUND`. 12 × 3 = 36 tests; discovery 0/36, final 0/36.

### M8 / Alternative Derivatives Historical Data Audit
Decision: `M8_ALT_DERIVATIVES_DATA_AUDIT_FAIL`. BookDepth 2023-2024 alone was partial-window eligible.

### M9 / BookDepth Microstructure Edge Discovery
Decision: `NO_STABLE_MICROSTRUCTURE_EDGE_FOUND`. 8 × 3 = 24 tests; discovery 0/24, challenge 0/24. Run `32435682751`, artifact `9430751063`.

### M10 / ETHUSDT Spot Historical Data Audit
Decision: `M10_CROSS_ASSET_DATA_AUDIT_FAIL`. 48/48 checksums existed, but frozen coverage/gap/close-time gates failed. Run `32437273137`, artifact `9431194682`.

### M11 / ETHUSDT USD-M Perpetual Historical Data Audit
Decision: `M11_ETH_PERPETUAL_DATA_AUDIT_PASS`.

- 48/48 archives and checksums;
- 140,256/140,256 15m bars;
- 100% coverage;
- normalized SHA-256 `69855dcaf2f34c2a529ddb7f83964fa61b39ed0a27ae8796a6c0eaafd5b744f5`;
- run `32437837012`, artifact `9431376987`.

### M12 / ETH→BTC Cross-Asset Edge Discovery
Decision: `NO_STABLE_CROSS_ASSET_EDGE_FOUND`.

- 8 candidates × 3 horizons = 24 tests;
- discovery 0/24;
- challenge 0/24;
- run `32438774152`;
- artifact `9431703188`;
- evidence SHA-256 `d79c8549ed9731cce081dc2957ad9db2f9a709b76ce1e6aed525f81be1a859c4`.

### M13 / Supervised ML Edge Engine
Decision: `NO_STABLE_ML_EDGE_FOUND`.

Frozen ML surface: 19 causal features, logistic regression + histogram gradient boosting, probability gates 0.60/0.65, horizons 4/16/48 bars, 12 configs, walk-forward 2021→2022 and 2021-2022→2023, reused 2024 challenge only after discovery pass, Base/Severe 30/70 bps, BH-FDR q<=0.10.

Authoritative evidence:
- source commit `18a0d9d632531d679aa95d8c04e9ce77d17dbfe3`;
- run `32446152844`;
- artifact `9434173433`;
- evidence SHA-256 `84f39d0619ef96f668df34ca178680a3d84bb2f1f227dfab7c16cdb0910d5859`;
- discovery pass 0/12; challenge pass 0/12; ML candidate 0;
- full pytest/Ruff PASS.

Closest observation `logistic_p65_h16` had positive Base-net but failed Severe economics, PF and FDR. M13 is retired without rescue tuning.

### M14 / Market-Neutral Funding Carry
Decision: **`NO_STABLE_FUNDING_CARRY_EDGE_FOUND`**.

This was a materially different non-directional mechanism: 1:1 long BTCUSDT Spot + short BTCUSDT USD-M perpetual, no leverage, no naked short, no overlapping positions. Frozen search: positive funding thresholds 1/3/5 bps × hold 3/9 funding records = 6 configurations. Base friction was 15 bps per side per leg; Severe friction 35 bps per side per leg. Discovery 2021-2023; reused 2024 challenge only after discovery pass.

Authoritative evidence:
- source commit `32a12c230af4fb99661f14d1669f20787ba112cf`;
- run `32446970715`;
- artifact `9434444012`;
- evidence SHA-256 `c5bd418a60260fb1619f8d0f563bf7ff93a1d66ee76525051df5f0c4bda136ec`;
- artifact ZIP SHA-256 `e9e27051ef31a23da69cd1698f4d531ce6fae4bd78b09606af8fd91698cb845a`;
- discovery pass 0/6; challenge pass 0/6; carry candidate 0;
- pytest/Ruff/freeze verification PASS.

All six configs had positive mean gross carry, but five had negative Base-net means. The closest `5bp / 9 records` observation had 37 trades, +0.31666% mean gross, +0.01499% mean Base-net, PF 1.2504, but median Base-net -0.04003%, Severe mean -0.38722%, FDR q=1.0, no 2022 trades, and only one 2023 trade with negative Base-net. It failed robustness/support/statistical gates and is not promotable.

M14 is retired. Do not lower costs, select the closest observation after the fact, change thresholds/hold periods, or add leverage to rescue it.

## Current system conclusion

No tested directional, cross-asset, supervised-ML, microstructure, derivatives-flow, or frozen market-neutral funding-carry mechanism has earned promotion.

Current state:
- research status: `NO_PROMOTABLE_EDGE_FOUND`;
- trading state: `NO_TRADE`;
- risk-sized strategy: blocked;
- live AI/ML signal layer: blocked;
- naked short authority: blocked;
- market-neutral carry live execution: blocked;
- live execution overall: blocked;
- 2025 OOS: `LOCKED_NOT_ACCESSED`.

## Next allowed action

Do not rescue M14 and do not continue arbitrary threshold/model searches merely to obtain a positive backtest.

A new research cycle may be opened only for a materially new, independently justified mechanism or data source frozen before outcome inspection. Operational product work may continue safely in paper/shadow mode: exchange connectivity, dashboard, deterministic Risk Engine, kill switch, execution simulator, accounting, monitoring, and strategy-plugin architecture.

Until a separately validated edge exists, the correct autonomous decision remains `NO_TRADE`.
