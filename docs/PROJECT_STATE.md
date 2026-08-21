# EBA-Trader Project State

Updated: 2026-08-21
Current research branch at this checkpoint: `m17-usdm-quarterly-cash-carry`

This file is the cross-chat continuity checkpoint. Read it before starting or modifying a later research cycle.

## Non-negotiable research policy

- 2025-01-01 through 2026-01-01 is the true frozen OOS holdout and remains `LOCKED_NOT_ACCESSED`.
- 2024 has already been observed repeatedly and is reused development challenge data only, never pristine OOS.
- Rejected frozen cycles are not retuned, sign-flipped, filtered, cost-relaxed, or rescued after results are observed.
- Search spaces, thresholds, horizons, costs, model hyperparameters, gates, and multiple-testing rules are frozen before evidence.
- A data-audit PASS qualifies a source only; it does not establish profitability.
- Deterministic Risk Engine remains superior to any future AI/ML/router layer.
- Risk sizing and live execution remain blocked until a separately frozen edge earns promotion.
- NO_TRADE is a valid system state.

## Completed research history

### M2-M5 / Directional and price-volume
Trend V1, Trend V2 and V3 were rejected. M5 Price-Volume Edge Discovery promoted 0/72 tests.

### M6-M9 / Derivatives and microstructure
M6 full derivatives contract failed although BTC funding and USD-M perpetual 15m individually passed. M7 Funding + Futures promoted 0/36. M8 alternative data contract failed overall, with BookDepth 2023-2024 partial-window eligible. M9 BookDepth Microstructure promoted 0/24.

### M10-M12 / ETH cross-asset
M10 ETH Spot audit failed. M11 ETH USD-M perpetual audit passed 140,256/140,256 bars. M12 ETH→BTC Cross-Asset Discovery promoted 0/24.

### M13 / Supervised ML Edge Engine
Decision: `NO_STABLE_ML_EDGE_FOUND`. 19 causal features, two frozen model families, 12 configurations, discovery 0/12, challenge 0/12. Run `32446152844`, artifact `9434173433`, evidence SHA `84f39d0619ef96f668df34ca178680a3d84bb2f1f227dfab7c16cdb0910d5859`.

### M14 / Market-Neutral Funding Carry
Decision: `NO_STABLE_FUNDING_CARRY_EDGE_FOUND`. Six frozen configs, discovery 0/6, challenge 0/6. Run `32446970715`, artifact `9434444012`, evidence SHA `c5bd418a60260fb1619f8d0f563bf7ff93a1d66ee76525051df5f0c4bda136ec`.

### M15 / Market-Neutral Perpetual Basis Convergence
Decision: `NO_STABLE_BASIS_CONVERGENCE_EDGE_FOUND`. Nine frozen configs, discovery 0/9. Run `32449012036`, artifact `9435060914`, evidence SHA `4bd98328539c9d75f0e17839a631ab80c05c9ee14222d7b144f75ff8c4ae0559`.

### M16 / Quarterly Delivery Futures Historical Data Audit
Decision: `M16_DELIVERY_DATA_AUDIT_PASS`.

- USD-M quarterly `BTCUSDT_YYMMDD`: `DELIVERY_DATA_ELIGIBLE`, 16/16 contracts passed, each 2,880/2,880 15m bars, 100% coverage, gap 0.
- COIN-M quarterly: not eligible because `BTCUSD_230929` failed frozen coverage/gap gates.
- run `32449978355`;
- artifact `9435350726`;
- evidence SHA `b966f290ddc0652fbeeaa453bb33a86ffae15695c80fd321f9173e5c42e86745`.

M16 qualified USD-M data only; it did not establish profitability.

### M17 / USD-M Quarterly Cash-and-Carry
Decision: **`NO_STABLE_DELIVERY_CARRY_EDGE_FOUND`**.

Frozen mechanism:
- same-BTC-quantity long BTCUSDT Spot + short M16-qualified USD-M quarterly delivery future;
- fully funded 1x futures margin research model;
- fixed entries 28d / 14d / 7d before scheduled delivery;
- exit both legs exactly 15 minutes before delivery;
- no basis threshold and no settlement-price model;
- Base/Severe friction 15/35 bps per side per leg;
- exact sign-flip test across 12 discovery contracts + BH-FDR across 3 configs;
- 2024 challenge allowed only after complete discovery pass.

Authoritative evidence:
- source commit `b3c9dfe8c28c78001b22176851f0f04e2ece3428`;
- run `32450971829`;
- artifact `9435702647`;
- evidence SHA `6561361055522f79441492a0ecf667876371eaa4641f9160e8a38821cbbbea4b`;
- artifact ZIP SHA `55f631db6bc63e55dff3f96a28c377f2f27405a1d6a34ce7f22ba23c48f7ca4d`;
- freeze / repo-wide pytest / Ruff PASS;
- challenge access `BLOCKED_NO_DISCOVERY_PASS`;
- 2025 remained locked.

Discovery summary:
- 28d: gross +0.259543%, Base -0.042706%, Severe -0.445705%, Base PF 0.7478, Base win rate 16.67%, q=1.0;
- 14d: gross +0.142694%, Base -0.155358%, Severe -0.552761%, Base PF 0.3350, q=1.0;
- 7d: gross +0.066116%, Base -0.230700%, Severe -0.626456%, Base PF 0.1031, q=1.0.

All M17 trades passed the conservative fully-funded margin-safety gate. The structural delivery premium existed gross, but it was too small/inconsistent to overcome the frozen friction model, and 2022/2023 were not stable. Discovery pass 0/3; 2024 outcomes were not opened by M17.

M17 is retired. Do not add a basis filter, lower costs, drop quarters, alter entry offsets, move exit to settlement, or add leverage to rescue it.

## Current system conclusion

No completed profitability cycle M2-M17 has earned promotion.

Current state:
- research status: `NO_PROMOTABLE_EDGE_FOUND_THROUGH_M17`;
- trading state: `NO_TRADE`;
- risk-sized strategy: blocked;
- live AI/ML signal layer: blocked;
- market-neutral live execution: blocked;
- live execution overall: blocked;
- 2025 OOS: `LOCKED_NOT_ACCESSED`.

## Next allowed action

Do not rescue M17 by changing its frozen economics after seeing results.

A later research cycle must introduce a materially different information source, venue/execution mechanism, or market structure. A realistic venue-fee/execution audit may be performed to understand whether the conservative friction assumptions materially differ from executable exchange fees, but it must be treated as a new frozen mechanism and not as a retroactive M17 pass.

Operational product work may continue in paper/shadow mode: exchange connectivity, dashboard, deterministic Risk Engine, kill switch, execution simulator, accounting, monitoring and strategy-plugin architecture.
