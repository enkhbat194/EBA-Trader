# EBA-Trader Project State

Updated: 2026-08-21
Current engineering branch: `m18-fee-aware-execution-economics`
Draft PR: #14 against `m17-usdm-quarterly-cash-carry`.

This file is the cross-chat continuity checkpoint. Read it before starting or modifying later research, UI, provider, paper, or execution work.

## Non-negotiable policy

- 2025-01-01 through 2026-01-01 is the true frozen OOS holdout and remains `LOCKED_NOT_ACCESSED`.
- 2024 has already been observed repeatedly and is reused development challenge data only, never pristine OOS.
- Rejected frozen cycles are not retuned, sign-flipped, filtered, cost-relaxed, or rescued after results are observed.
- Deterministic Risk Engine remains superior to any AI/ML/router/execution layer.
- `NO_TRADE` is a valid system state.
- Live execution remains locked.
- GitHub is the source of truth for M18/M18.1 development. Replit is not a required development dependency.

## Completed research history

### M2-M5 / Directional and price-volume
Trend V1, Trend V2 and V3 were rejected. M5 Price-Volume Edge Discovery promoted 0/72 tests.

### M6-M9 / Derivatives and microstructure
M6 full derivatives contract failed although BTC funding and USD-M perpetual 15m individually passed. M7 Funding + Futures promoted 0/36. M8 alternative data contract failed overall. M9 BookDepth Microstructure promoted 0/24.

### M10-M12 / ETH cross-asset
M10 ETH Spot audit failed. M11 ETH USD-M perpetual audit passed 140,256/140,256 bars. M12 ETH→BTC Cross-Asset Discovery promoted 0/24.

### M13 / Supervised ML Edge Engine
`NO_STABLE_ML_EDGE_FOUND`. Discovery 0/12, challenge 0/12. Run `32446152844`, artifact `9434173433`, evidence SHA `84f39d0619ef96f668df34ca178680a3d84bb2f1f227dfab7c16cdb0910d5859`.

### M14 / Market-Neutral Funding Carry
`NO_STABLE_FUNDING_CARRY_EDGE_FOUND`. Discovery 0/6. Run `32446970715`, artifact `9434444012`, evidence SHA `c5bd418a60260fb1619f8d0f563bf7ff93a1d66ee76525051df5f0c4bda136ec`.

### M15 / Market-Neutral Perpetual Basis Convergence
`NO_STABLE_BASIS_CONVERGENCE_EDGE_FOUND`. Discovery 0/9. Run `32449012036`, artifact `9435060914`, evidence SHA `4bd98328539c9d75f0e17839a631ab80c05c9ee14222d7b144f75ff8c4ae0559`.

### M16 / Quarterly Delivery Futures Historical Data Audit
`M16_DELIVERY_DATA_AUDIT_PASS`.

- USD-M quarterly `BTCUSDT_YYMMDD`: 16/16 contracts passed; each 2,880/2,880 15m bars, 100% coverage, gap 0.
- COIN-M not eligible because `BTCUSD_230929` failed frozen coverage/gap gates.
- run `32449978355`, artifact `9435350726`;
- evidence SHA `b966f290ddc0652fbeeaa453bb33a86ffae15695c80fd321f9173e5c42e86745`.

### M17 / USD-M Quarterly Cash-and-Carry
**`NO_STABLE_DELIVERY_CARRY_EDGE_FOUND`**.

Frozen mechanism: same-BTC-quantity long BTCUSDT Spot + short M16-qualified USD-M quarterly future; fully funded research capital; entries 28d/14d/7d before delivery; exit 15m before delivery; Base/Severe friction 15/35 bps per side per leg; 2024 challenge only after discovery pass.

Authoritative evidence:
- source commit `b3c9dfe8c28c78001b22176851f0f04e2ece3428`;
- run `32450971829`, artifact `9435702647`;
- evidence SHA `6561361055522f79441492a0ecf667876371eaa4641f9160e8a38821cbbbea4b`;
- discovery pass 0/3;
- challenge access `BLOCKED_NO_DISCOVERY_PASS`;
- 2025 remained locked.

Discovery means:
- 28d gross +0.259543%, Base -0.042706%, Severe -0.445705%;
- 14d gross +0.142694%, Base -0.155358%, Severe -0.552761%;
- 7d gross +0.066116%, Base -0.230700%, Severe -0.626456%.

M17 is retired. Do not alter its thresholds, costs, contract selection, exit or leverage to rescue it.

## M18 / Fee-Aware Execution Economics + M18.1 Multi-Provider App — ACTIVE

Purpose: build a truthful account-specific execution-cost/paper-scanning layer and a provider-independent product UI without retroactively changing M17 research.

### GitHub-only development

All current UI, backend, provider adapters, tests, CI and documentation are developed directly on GitHub branch `m18-fee-aware-execution-economics`. Replit is not used as source of truth and is not required for development.

### M18 fee-aware engine

Implemented:
- account-specific Spot and USD-M commission parsing;
- public Spot/Futures order-book ingestion and multi-level VWAP;
- nearest active `BTCUSDT_YYMMDD` delivery-symbol selection;
- stale/depth/symbol/economics deterministic vetoes;
- reserved exit fees, slippage allowance and safety buffer;
- outputs only `NO_TRADE` or `PAPER_CANDIDATE`;
- no order, cancel, transfer, withdrawal or leverage-changing methods;
- live execution and AI signal authority hard-locked.

Engineering defaults:
- quantity 0.001 BTC;
- depth 100 levels;
- quote freshness max 1,500 ms;
- taker/taker entry assumption;
- minimum screening net edge 5 bps on fully funded capital;
- exit slippage reserve 2 bps per leg;
- safety buffer 5 bps.

### Binance Demo / Testnet contract

Demo connection now requires both legs before it can report `CONNECTED`:

1. Spot Testnet: `https://testnet.binance.vision` with its API key/secret.
2. USD-M Futures Testnet: `https://testnet.binancefuture.com` with its API key/secret.

The two credential pairs are separate fields because the Testnet environments can issue independent keys. Spot-only credentials cannot unlock the paper scanner.

Connection validation is read-only:
- Spot account: `GET /api/v3/account`;
- USD-M account: `GET /fapi/v3/account`.

On success the Dashboard receives real Demo balance data from the read-only responses. The previous fake `$25,430.68` placeholder was removed; before connection, Balance/P&L/Net fields display `—`.

### RAM-only Demo session

After both Binance Demo legs pass:
- backend creates a cryptographically random opaque session token;
- credentials stay only in server process memory for a 30-minute TTL;
- credentials are never written to Git or disk;
- UI keeps only the opaque token in JavaScript memory;
- no `localStorage` or `sessionStorage` is used;
- form credential values are cleared after the connection request;
- process restart or TTL expiry invalidates the session;
- expired/missing tokens fail closed.

### Demo fee-aware scanner

New Demo-only read path:
- `POST /api/demo/snapshot` accepts only the RAM-session token;
- Spot Testnet commission/depth and USD-M Testnet commission/depth are queried read-only;
- active Testnet quarterly delivery contract is selected if one exists;
- if Testnet has no active quarterly delivery contract, result is `NO_TRADE` with `NO_ACTIVE_TESTNET_DELIVERY_CONTRACT`; there is no silent fallback to Live data or a different strategy;
- UI displays Spot buy, Futures sell, Gross edge, fee reserve, slippage reserve, safety buffer and NET edge;
- paper scanner refresh interval is 15 seconds while enabled;
- this is scanning only: no orders or simulated fills are created yet.

### Provider-independent architecture

Implemented:
- `ConnectionManager`;
- `ProviderAdapter` interface;
- provider-neutral connection/capability models;
- Binance Demo adapter active for read-only tests;
- MetaTrader 5 adapter scaffold only;
- MetaTrader 4 adapter scaffold only;
- provider capability model does not grant live execution.

Future providers can be added behind the same interface without rebuilding the app UI.

### Mobile PWA

High-fidelity dark mobile-first UI implemented from the approved visual concept:
- Home / Dashboard;
- Opportunities;
- Positions;
- History;
- Settings / Connections;
- bottom navigation;
- Binance / MT5 / MT4 connection cards;
- Demo enabled and `LIVE 🔒` disabled;
- installable PWA manifest and service worker.

Dashboard/paper safety behavior:
- no fake balance or fake profit values;
- paper scanner remains disabled until both Binance Demo connections pass and a RAM session exists;
- session failure/restart/expiry re-locks paper mode;
- Opportunities is driven by read-only Demo snapshot data;
- Positions/History explicitly state that M18 has no order-placement path.

### Backend/UI bridge

- `GET /api/health`;
- `GET /api/providers`;
- `POST /api/connections/test`;
- `POST /api/demo/snapshot`;
- request body size bounded;
- responses use `Cache-Control: no-store`;
- `live` environment hard rejected;
- CLI entry point `eba-web` serves the app.

### Validation checkpoint

Latest validated code commit: `fd9b469dd9ee808e22c026c248425d5c360ded44`.
GitHub Actions run: `32500447292`.

PASS:
- M18 read-only safety contract;
- Binance Demo client safety contract;
- M18.1 mobile UI safety contract;
- dual Spot + USD-M credential regression tests;
- RAM-only session tests;
- Demo snapshot tests;
- provider-neutral tests;
- secure web bridge tests;
- repo-wide pytest;
- Ruff.

No user Demo credential has been used yet. No real-money credential has been used. No M17-blocked 2024 challenge outcome and no 2025 OOS data were accessed by this engineering work.

## Current system conclusion

No completed profitability cycle M2-M17 has earned promotion. M18/M18.1 are operational infrastructure, not a profitability pass.

Current state:
- research status: `NO_PROMOTABLE_EDGE_FOUND_THROUGH_M17`;
- engineering status: `M18_1_GITHUB_ONLY_DUAL_DEMO_SCANNER_GREEN`;
- Binance Spot Testnet adapter: ready for credential test;
- Binance USD-M Futures Testnet adapter: ready for credential test;
- RAM-only Demo session: implemented;
- Demo fee-aware scanner: implemented;
- MT5 adapter: scaffold only;
- MT4 adapter: scaffold only;
- mobile PWA: implemented;
- trading state: `NO_TRADE`;
- live AI/ML authority: blocked;
- live execution: blocked;
- 2025 OOS: `LOCKED_NOT_ACCESSED`.

## Next allowed action

1. Make the GitHub-built app reachable through a suitable runtime/hosting target; Replit is not required.
2. Create/use Demo/Testnet credentials only: one Spot Testnet pair and one USD-M Futures Testnet pair.
3. Paste them into the in-app Binance Demo form and run `TEST BOTH DEMO CONNECTIONS`.
4. Verify real Demo balances and the first read-only fee-aware snapshot.
5. If Testnet has no active quarterly delivery contract, keep the explicit `NO_TRADE` result and decide separately whether a live-public-market/paper-account shadow mode deserves a new engineering contract.
6. Only after sustained paper/shadow validation and explicit approval may live connection/execution work be considered.

A new historical profitability claim still requires a separately frozen research protocol; M18/M18.1 must not be used to retroactively turn M17 into a pass.
