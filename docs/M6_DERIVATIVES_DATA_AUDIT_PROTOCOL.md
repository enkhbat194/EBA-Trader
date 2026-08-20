# M6 Derivatives Historical Data Audit Protocol

Status: `FROZEN_PRE_AUDIT`
Frozen date: 2026-08-21
Scope: BTCUSDT Binance USDⓈ-M public market data only.

## Purpose

M6 does not search for a trading strategy. It first determines which derivatives data families can be
reproduced across the full development window without touching the frozen 2025 OOS holdout.

Development audit window:
- start: `2021-01-01T00:00:00Z`
- end exclusive: `2025-01-01T00:00:00Z`

Frozen holdout:
- `2025-01-01T00:00:00Z` to `2026-01-01T00:00:00Z`
- status: `LOCKED_NOT_ACCESSED`

## Official Binance public sources audited

Core historical sources:
1. USDⓈ-M funding-rate history: `GET /fapi/v1/fundingRate`
2. USDⓈ-M premium-index 15m klines: `GET /fapi/v1/premiumIndexKlines`
3. USDⓈ-M perpetual BTCUSDT 15m klines: `GET /fapi/v1/klines`
4. USDⓈ-M BTCUSDT index-price 15m klines: `GET /fapi/v1/indexPriceKlines`

Documented retention-blocked sources:
5. Open-interest statistics: `GET /futures/data/openInterestHist`
   - Binance documents only the latest 1 month as available.
6. Basis: `GET /futures/data/basis`
   - Binance documents only the latest 30 days as available.

The retention-blocked sources are not downloaded for 2021-2024 and cannot be used in an M6 historical
edge search unless a separately audited archival source is introduced later.

## Causality and security

- Public market-data endpoints only; no API key is required.
- No order, account, wallet, withdrawal, leverage, or position endpoint is allowed.
- Any requested range overlapping 2025 must fail before network access.
- All kline timestamps are interpreted as UTC.
- Klines are identified by open time.
- No forward fill across a source gap is allowed in later research; feature state must reset across gaps.
- Funding values become usable only at or after their published `fundingTime`.

## Frozen audit criteria

### A. Funding history

PASS only if all are true:
- records are strictly increasing and unique by `fundingTime`;
- every record is inside the development audit window;
- at least 4,000 records are present;
- first record is no later than 8 hours after the audit start;
- last record is no earlier than 8 hours before the audit end;
- all funding rates are finite and have absolute value <= 5%;
- median positive cadence is <= 8 hours;
- maximum positive cadence is <= 24 hours.

### B. Each 15m kline family

Applied independently to premium-index, perpetual futures, and index-price datasets:
- timestamps are strictly increasing and unique;
- every open time is aligned to 15 minutes and inside the audit window;
- close time equals open time + 15 minutes - 1 millisecond;
- OHLC values are finite;
- premium-index OHLC may be negative; futures/index prices must be positive;
- OHLC high/low relationships must be valid;
- coverage is at least 99.90% of the expected 15m slots;
- maximum missing run is no more than 48 consecutive 15m slots (12 hours).

Additional perpetual-futures rules:
- volume and quote volume are non-negative;
- trade count is non-negative;
- taker-buy base/quote volumes are non-negative.

### C. Cross-source alignment

PASS only if:
- the intersection of premium-index, futures, and index-price 15m open times covers at least 99.80% of
  the expected development slots;
- synthetic perpetual/index basis `(futures_close / index_close) - 1` is finite on every aligned row.

## Audit decision

`ELIGIBLE_FOR_M6_EDGE_DESIGN` only when A, B, and C all pass.

Otherwise the decision is `M6_DERIVATIVES_DATA_AUDIT_FAIL`.

A PASS is data eligibility only. It does not prove an edge, does not create a strategy, does not unlock
2025, and does not authorize paper or live trading.

## After PASS

Only after the audit passes may a separate M6 edge-discovery search space be written and frozen. That
later search may use funding, premium-index, perpetual/index synthetic basis, and futures activity
features from the audited datasets. Open interest and Binance's `/futures/data/basis` remain excluded
from 2021-2024 historical research unless separately sourced and audited.
