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

## M18 / Fee-Aware Execution Economics + M18.1 Multi-Provider App — ACTIVE

Branch: `m18-fee-aware-execution-economics`.
Draft PR: #14 against the M17 branch. Do not merge to `main` without explicit approval.

### M18 fee-aware engine

Purpose: build an account-specific, executable-price cost layer without retroactively changing M17 research.

Implemented:
- signed read-only Binance Spot commission query model;
- signed read-only USD-M commission query model;
- public Spot and USD-M depth ingestion and multi-level VWAP;
- automatic nearest active `BTCUSDT_YYMMDD` delivery-symbol selection;
- deterministic stale-book, depth, symbol and economics vetoes;
- reserved exit fees, slippage allowance and safety buffer;
- outputs only `NO_TRADE` or `PAPER_CANDIDATE`;
- no order, cancel, transfer, withdrawal, leverage-change or execution methods;
- live execution and AI signal authority hard-locked.

Engineering defaults:
- quantity 0.001 BTC;
- depth 100 levels;
- quote freshness max 1,500 ms;
- taker/taker entry assumption;
- minimum screening net edge 5 bps on fully funded capital;
- exit slippage reserve 2 bps per leg;
- safety buffer 5 bps.

### M18.1 provider-independent architecture

The product is no longer coupled to Binance.

Implemented provider-neutral types and lifecycle:
- `ConnectionManager`;
- `ProviderAdapter` interface;
- `ConnectionProfile`, `CredentialEnvelope`, connection state and capability model;
- `BinanceProviderAdapter` ready for read-only Demo connection checks;
- `MetaTrader5ProviderAdapter` scaffolded and deliberately reports not activated;
- `MetaTrader4ProviderAdapter` scaffolded for a future EA/bridge and deliberately reports not activated;
- provider capability model excludes live execution from current adapters.

Demo-first Binance endpoint set is explicit. Live provider connection requests are rejected by the web backend even if a caller bypasses the UI.

### M18.1 mobile PWA

High-fidelity mobile-first dark UI implemented from the approved visual concept:
- Home / Dashboard;
- Opportunities;
- Positions;
- History;
- Settings / Connections;
- bottom navigation;
- Demo status, connection count, bot paper controls, NO_TRADE reason;
- Binance / MetaTrader 5 / MetaTrader 4 connection cards;
- provider-specific connection form;
- `DEMO` enabled and `LIVE 🔒` disabled;
- installable PWA manifest and service worker.

Secret handling policy:
- API keys/passwords are never committed to Git;
- UI does not write credentials to `localStorage` or `sessionStorage`;
- connection form values are cleared after use/close;
- the web backend accepts credentials only for the current connection-test request and does not persist them;
- HTTP connection-test responses use `Cache-Control: no-store`;
- live execution remains false in all API responses.

Backend/UI bridge:
- static PWA served by the Python web server;
- `GET /api/health`;
- `GET /api/providers`;
- `POST /api/connections/test`;
- request body size is bounded;
- `live` environment is hard rejected in M18.1;
- CLI entry point `eba-web` added.

### Validation checkpoint

Latest validated code commit: `75953b7a13f4de4bcba67ad83f80238a2f9b62ef`.
GitHub Actions run: `32483893037`.

PASS:
- M18 read-only safety contract;
- M18.1 mobile UI safety contract;
- provider-neutral regression tests;
- secure web bridge regression tests;
- repo-wide pytest;
- Ruff.

No account-specific Demo credential has been used yet. No 2024 M17 challenge outcome and no 2025 OOS data were accessed by this engineering work.

## Current system conclusion

No completed profitability cycle M2-M17 has earned promotion. M18/M18.1 are operational infrastructure, not a profitability pass.

Current state:
- research status: `NO_PROMOTABLE_EDGE_FOUND_THROUGH_M17`;
- engineering status: `M18_1_MULTI_PROVIDER_DEMO_FIRST_APP_GREEN`;
- Binance Demo connection adapter: ready for credential test;
- MT5 adapter: scaffold only;
- MT4 adapter: scaffold only;
- mobile PWA: implemented;
- secure connection-test backend: implemented;
- trading state: `NO_TRADE`;
- paper candidate detector: implemented;
- live AI/ML signal layer: blocked;
- live execution overall: blocked;
- 2025 OOS: `LOCKED_NOT_ACCESSED`.

## Next allowed action

1. Run/deploy the M18.1 app in a preview environment so it can be opened from a phone.
2. Create/use a Binance Demo credential and paste it into the app's Binance Demo connection form.
3. Use only the in-app `Test Connection` flow; do not use a real-money Binance credential yet.
4. After Demo connection succeeds, wire account balance, account-specific fees and fee-aware opportunity snapshots into the Dashboard/Opportunities views.
5. Only after sustained paper/shadow validation should a separate explicit approval process consider any live connection or live execution work.

A new historical profitability claim still requires a separately frozen research protocol; M18/M18.1 must not be used to retroactively turn M17 into a pass.
