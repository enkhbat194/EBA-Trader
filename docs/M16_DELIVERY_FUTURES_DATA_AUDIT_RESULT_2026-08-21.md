# M16 Delivery Futures Historical Data Audit Result

Date: 2026-08-21

Decision: **`M16_DELIVERY_DATA_AUDIT_PASS`**

This cycle audited historical quarterly delivery-futures data only. No basis profitability, PnL, forward return, strategy generation, risk sizing, AI signal, or live execution was permitted.

## Frozen scope

- 2021-2024 quarterly delivery calendar: 16 contracts.
- Families audited independently:
  - USD-M (`um`): `BTCUSDT_YYMMDD`.
  - COIN-M (`cm`): `BTCUSD_YYMMDD`.
- Each contract: final 30 days before the predeclared 08:00 UTC delivery.
- 15m grid: 2,880 expected bars per contract.
- Frozen gates included official archive/checksum verification, coverage >=99.90%, max missing run <=4 bars, exact interval/close-time semantics, numeric integrity, duplicate/conflict integrity, and final-data proximity to delivery.
- 2025 remained `LOCKED_NOT_ACCESSED`.

## Authoritative evidence

- Source commit: `c0a63a8f21c69bf062cf3725751171415d06a739`.
- GitHub Actions run: `32449978355`.
- Artifact: `9435350726`.
- Evidence JSON SHA-256: `b966f290ddc0652fbeeaa453bb33a86ffae15695c80fd321f9173e5c42e86745`.
- Artifact ZIP SHA-256: `794ac8b1bf047269da7ea29e5c121236e383acccbcec01d5f256a6513f6f22e9`.
- Freeze verification: PASS.
- Repo-wide pytest: PASS.
- Ruff: PASS.

## Family verdicts

### USD-M

Decision: **`DELIVERY_DATA_ELIGIBLE`**.

All 16/16 contracts passed. Every USD-M contract had:

- 2,880 / 2,880 accepted 15m bars;
- 100.0000% coverage;
- 0 missing bars;
- max missing run 0;
- final edge 15 minutes before delivery;
- no conflicting duplicates;
- no alignment, close-time, or numeric-integrity violations.

Normalized contract SHA-256 values:

- `BTCUSDT_210326` `f79f15d08c6cd43ed2561b1b4265df3e36d9956fefbc57b087285226fb87d304`
- `BTCUSDT_210625` `2e632cb7e4ab2ce64d861559fca46769e5af369bc9cbe4b5f2ba85eb8118c615`
- `BTCUSDT_210924` `65e2fa23380b31dedf3cc4f531903eaa5ff1df32f2849a902e0bc087637f8595`
- `BTCUSDT_211231` `a5e3ca298896c9534964ddf809e2012975c970f9fb2b6e9020dae47f71716aec`
- `BTCUSDT_220325` `3505ed15fc1e56434f7973c0dd50d3d9289be9dfeb67af4977095dea5ee2de20`
- `BTCUSDT_220624` `900cdbbdbb0e6af702017b025756f487d1e0fa027d7b607ff9d2d7830b9c26c8`
- `BTCUSDT_220930` `9681acf8a3ee8859458ecf352cbb2668ece506a24e6ea094c3e22b62e6dc6279`
- `BTCUSDT_221230` `04fef855eac5ff6eaff26885a5766fc75306f7b0e96d8c0ab2c969408e2b2cdb`
- `BTCUSDT_230331` `dc611534031ef5d731aff14a7b33d686d99d91f32db29c732f54be7960859f5d`
- `BTCUSDT_230630` `9289310ec582a44699ef5b5db5f2faa6ee7c2920d4cdff855e165ef58796d2ba`
- `BTCUSDT_230929` `4f1613bb07d6eec43bce62e1a90c0572c1a93470ee46c56db33a79126f03467d`
- `BTCUSDT_231229` `4cfd4b62b78311ff891158d51e9db49f1e74c6470b037cb54760918d90e1385b`
- `BTCUSDT_240329` `e1af7fe888eb22c7541746718c8e1b7ef1a07cfc6f832763619f5c5cd3f4bb93`
- `BTCUSDT_240628` `b3361ea90026104b79acb664274adc52e8a89d32e1bb4026b5d6a7b95dc421c0`
- `BTCUSDT_240927` `0fc50fdd057392af9e7fadc91e62608574f60519b5c6aca5e06468e4334ea617`
- `BTCUSDT_241227` `685167715b3a1dd2d9d96cf0c26fe9fc5abd106f44006ac921b2bdae54d16979`

### COIN-M

Decision: **`DELIVERY_DATA_NOT_ELIGIBLE`**.

15/16 contracts passed, but the frozen family contract required all 12 discovery and all 4 reused-challenge contracts to pass. `BTCUSD_230929` failed with:

- 2,720 / 2,880 accepted bars;
- 94.4444% coverage;
- 160 missing bars;
- max missing run 160 bars;
- coverage gate FAIL;
- max-gap gate FAIL.

COIN-M is therefore not allowed into the next profitability cycle under this frozen audit.

## Research consequence

M16 qualifies **USD-M quarterly delivery futures only** for a separate profitability study. M16 itself does not establish an edge.

The next allowed research cycle is a frozen USD-M quarterly cash-and-carry/convergence study using the exact qualified M16 contract hashes plus the already frozen BTC Spot development data. The profitability protocol must be frozen before inspecting any cash-and-carry result. 2025 remains locked.
