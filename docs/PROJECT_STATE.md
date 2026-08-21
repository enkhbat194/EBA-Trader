# EBA-Trader Project State

Updated: 2026-08-21
Current research branch at this checkpoint: `m13-ml-edge-engine`

This file is the cross-chat continuity checkpoint. Read it before starting or modifying a later research cycle.

## Non-negotiable research policy

- BTCUSDT Spot remains the intended outcome/execution market unless a later frozen contract explicitly changes it.
- 2025-01-01 through 2026-01-01 is the true frozen OOS holdout and remains `LOCKED_NOT_ACCESSED`.
- 2024 has already been observed repeatedly and is reused development challenge data only, never pristine OOS.
- Rejected frozen cycles are not retuned, sign-flipped, filtered, or rescued after results are observed.
- Search spaces, thresholds, horizons, costs, gates, model hyperparameters and multiple-testing rules are frozen before forward-return evidence.
- Risk sizing and live execution remain blocked until a signal/edge family earns promotion under a frozen contract.
- Deterministic Risk Engine is always superior to any future AI/ML signal.
- NO_TRADE is a valid outcome.

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
Decision: `M10_CROSS_ASSET_DATA_AUDIT_FAIL`. 48/48 checksums, but frozen coverage/gap/close-time gates failed. Run `32437273137`, artifact `9431194682`.

### M11 / ETHUSDT USD-M Perpetual Historical Data Audit
Decision: `M11_ETH_PERPETUAL_DATA_AUDIT_PASS`.

- 48/48 archives and checksums;
- 140,256/140,256 bars;
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
Decision: **`NO_STABLE_ML_EDGE_FOUND`**.

Frozen ML surface:
- 19 causal BTC Spot / BTC perpetual / funding / ETH perpetual features;
- model families: logistic regression and histogram gradient boosting;
- probability gates 0.60 / 0.65;
- horizons 4 / 16 / 48 bars;
- 12 total configurations;
- walk-forward discovery: train 2021 → predict 2022; train 2021-2022 → predict 2023;
- 2024 reused challenge allowed only after discovery pass;
- Base/Severe costs 30/70 bps;
- BH-FDR q<=0.10;
- scikit-learn 1.7.2, random_state 13.

Authoritative evidence:
- source commit `18a0d9d632531d679aa95d8c04e9ce77d17dbfe3`;
- run `32446152844`;
- artifact `9434173433`;
- evidence SHA-256 `84f39d0619ef96f668df34ca178680a3d84bb2f1f227dfab7c16cdb0910d5859`;
- artifact ZIP SHA-256 `d47080628c92de1548caee6bd9a5ba429a3e120dbd5845559cd5241dea2058a7`;
- full pytest PASS (266 tests);
- Ruff PASS.

M13 result summary:
- sample counts: 2021=8,737; 2022=8,760; 2023=8,758; 2024=8,783;
- mean Base-net > 0: 3/12 configs;
- mean Severe-net > 0: 0/12;
- median Base-net > 0: 3/12;
- Base-net PF > 1.10: 2/12;
- both 2022 and 2023 mean Base-net > 0: 1/12;
- BH-FDR q<=0.10: 0/12;
- complete discovery pass: 0/12;
- complete challenge pass: 0/12;
- `ML_LONG_EDGE_CANDIDATE`: 0.

Closest observation `logistic_p65_h16` had 118 OOF events, +0.1012% mean Base-net and positive 2022/2023 Base-net means, but Severe mean was -0.2988%, PF 1.0873 was below gate, and q=0.7699. It is not promotable.

M13 is retired. Do not tune its probability gates, features, model families, hyperparameters, horizons, costs or years to rescue it.

## Current system conclusion

No BTC edge has earned promotion under the completed deterministic or supervised-ML research campaign.

Current state:
- research status: `NO_PROMOTABLE_EDGE_FOUND`;
- trading state: `NO_TRADE`;
- risk-sized strategy: blocked;
- live AI/ML signal layer: blocked;
- short authority: not granted;
- live execution: blocked;
- 2025 OOS: `LOCKED_NOT_ACCESSED`.

M2-M13 have tested materially different families: trend/pullback, BTC price-volume, derivatives funding/flow, BookDepth microstructure, ETH cross-asset states, and a frozen supervised-ML combination of the qualified sources. Repeatedly adding thresholds/models until one backtest turns positive would now materially increase data-mining risk.

## Next allowed action

Do not rescue M13.

The research campaign remains closed with `NO_PROMOTABLE_EDGE_FOUND` unless a materially new, independently justified information source or market mechanism is introduced under a new frozen protocol. Operational product work may continue in paper/shadow mode: dashboard, exchange connectivity, deterministic Risk Engine, kill switch, execution simulator and monitoring. Do not claim profitable live readiness until a separately validated edge exists.
