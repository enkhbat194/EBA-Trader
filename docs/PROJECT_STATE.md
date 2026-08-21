# EBA-Trader Project State

Updated: 2026-08-21
Current engineering branch: `m18-fee-aware-execution-economics`

This file is the cross-chat continuity checkpoint. Read it before starting or modifying a later research or execution cycle.

## Non-negotiable policy

- 2025-01-01 through 2026-01-01 is the true frozen OOS holdout and remains `LOCKED_NOT_ACCESSED`.
- 2024 has already been observed repeatedly and is reused development challenge data only, never pristine OOS.
- Rejected frozen cycles are not retuned, sign-flipped, filtered, cost-relaxed, or rescued after results are observed.
- Search spaces, thresholds, horizons, costs, model hyperparameters, gates, and multiple-testing rules are frozen before research evidence.
- Deterministic Risk Engine remains superior to any future AI/ML/router/execution layer.
- NO_TRADE is a valid system state.
- Live execution remains locked.

## Completed research history

### M2-M5 / Directional and price-volume
Trend V1, Trend V2 and V3 were rejected. M5 Price-Volume Edge Discovery promoted 0/72 tests.

### M6-M9 / Derivatives and microstructure
M6 full derivatives contract failed although BTC funding and USD-M perpetual 15m individually passed. M7 Funding + Futures promoted 0/36. M8 alternative data contract failed overall, with BookDepth 2023-2024 partial-window eligible. M9 BookDepth Microstructure promoted 0/24.

### M10-M12 / ETH cross-asset
M10 ETH Spot audit failed. M11 ETH USD-M perpetual audit passed 140,256/140,256 bars. M12 ETH→BTC Cross-Asset Discovery promoted 0/24.

### M13 / Supervised ML Edge Engine
`NO_STABLE_ML_EDGE_FOUND`. Twelve frozen configs, discovery 0/12, challenge 0/12. Run `32446152844`, artifact `9434173433`, evidence SHA `84f39d0619ef96f668df34ca178680a3d84bb2f1f227dfab7c16cdb0910d5859`.

### M14 / Market-Neutral Funding Carry
`NO_STABLE_FUNDING_CARRY_EDGE_FOUND`. Six frozen configs, discovery 0/6. Run `32446970715`, artifact `9434444012`, evidence SHA `c5bd418a60260fb1619f8d0f563bf7ff93a1d66ee76525051df5f0c4bda136ec`.

### M15 / Market-Neutral Perpetual Basis Convergence
`NO_STABLE_BASIS_CONVERGENCE_EDGE_FOUND`. Nine frozen configs, discovery 0/9. Run `32449012036`, artifact `9435060914`, evidence SHA `4bd98328539c9d75f0e17839a631ab80c05c9ee14222d7b144f75ff8c4ae0559`.

### M16 / Quarterly Delivery Futures Historical Data Audit
`M16_DELIVERY_DATA_AUDIT_PASS`.

- USD-M quarterly `BTCUSDT_YYMMDD`: 16/16 contracts passed; each 2,880/2,880 15m bars, 100% coverage, gap 0.
- COIN-M not eligible because `BTCUSD_230929` failed frozen coverage/gap gates.
- run `32449978355`, artifact `9435350726`;
- evidence SHA `b966f290ddc0652fbeeaa453bb33a86ffae15695c80fd321f9173e5c42e86745`.

### M17 / USD-M Quarterly Cash-and-Carry
**`NO_STABLE_DELIVERY_CARRY_EDGE_FOUND`**.

Frozen mechanism: same-BTC-quantity long BTCUSDT Spot + short M16-qualified USD-M quarterly future; fully funded research capital; fixed entries 28d/14d/7d before delivery; exit 15m before delivery; no basis threshold; Base/Severe friction 15/35 bps per side per leg; exact sign-flip + BH-FDR; 2024 challenge only after discovery pass.

Authoritative evidence:
- source commit `b3c9dfe8c28c78001b22176851f0f04e2ece3428`;
- run `32450971829`, artifact `9435702647`;
- evidence SHA `6561361055522f79441492a0ecf667876371eaa4641f9160e8a38821cbbbea4b`;
- discovery pass 0/3;
- challenge access `BLOCKED_NO_DISCOVERY_PASS`;
- 2025 remained locked.

Discovery means:
- 28d gross +0.259543%, Base -0.042706%, Severe -0.445705%, Base PF 0.7478, Base win rate 16.67%, q=1.0;
- 14d gross +0.142694%, Base -0.155358%, Severe -0.552761%, Base PF 0.3350;
- 7d gross +0.066116%, Base -0.230700%, Severe -0.626456%, Base PF 0.1031.

M17 is retired. Do not add a basis filter, lower its frozen costs, select quarters, alter entry offsets, move its exit to settlement, or add leverage to rescue it.

## M18 / Fee-Aware Execution Economics — ACTIVE ENGINEERING LAYER

Branch: `m18-fee-aware-execution-economics`.
Draft PR: #14 against the M17 branch. Do not merge to `main` without explicit approval.

Purpose: build an account-specific, executable-price cost layer without retroactively changing M17 research.

Implemented:
- signed read-only Binance Spot commission query model for `GET /api/v3/account/commission`;
- signed read-only USD-M commission query model for `GET /fapi/v1/commissionRate`;
- public Spot and USD-M depth ingestion;
- automatic nearest active `BTCUSDT_YYMMDD` delivery-symbol selection from exchange info;
- depth-weighted Spot BUY and Futures SELL VWAP for equal BTC quantity;
- Spot standard/special/tax and BNB-discount-aware fee parser;
- Futures account-specific maker/taker fee parser;
- deterministic stale-book, depth, symbol and economics vetoes;
- reserved exit fees, 2 bps/leg exit-slippage allowance and 5 bps capital safety buffer;
- outputs only `NO_TRADE` or `PAPER_CANDIDATE`;
- no order, cancel, transfer, withdrawal, leverage-change or execution methods;
- live execution and AI signal authority hard-locked.

Frozen engineering defaults:
- default quantity 0.001 BTC;
- order-book depth 100 levels;
- quote freshness max 1,500 ms;
- taker/taker entry assumption;
- minimum screening net edge 5 bps on fully funded capital;
- exit slippage reserve 2 bps per leg;
- safety buffer 5 bps.

Validation:
- M18 safety contract PASS;
- repo-wide pytest PASS;
- Ruff PASS;
- GitHub Actions run `32455283467` PASS at commit `2e55877499619ed47bcbcdc3ca62295090b2b8c7`.

M18 has **not** yet queried the user's Binance account-specific commission rates. That requires runtime credentials or a connected Binance account and is read-only in this code path. No account secret belongs in Git or logs.

## Current system conclusion

No completed profitability cycle M2-M17 has earned promotion. M18 is operational infrastructure, not a new profitability pass.

Current state:
- research status: `NO_PROMOTABLE_EDGE_FOUND_THROUGH_M17`;
- engineering status: `M18_FEE_AWARE_READ_ONLY_ENGINE_GREEN`;
- trading state: `NO_TRADE`;
- paper candidate detector: implemented, awaiting account-specific live read-only snapshot;
- risk-sized strategy: blocked;
- live AI/ML signal layer: blocked;
- market-neutral live execution: blocked;
- live execution overall: blocked;
- 2025 OOS: `LOCKED_NOT_ACCESSED`.

## Next allowed action

Run an account-specific **read-only M18 snapshot** with Binance API credentials supplied only through runtime environment variables (or a connected account tool), never committed to Git. Capture current Spot and active quarterly Futures commission rates plus executable depth and calculate the screening net edge.

After that, paper/shadow monitoring can record opportunities over time. A new historical profitability claim requires a separately frozen research protocol; M18 must not be used to retroactively turn M17 into a pass.
