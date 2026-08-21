# M10 Cross-Asset Historical Data Audit Protocol

Status: `FROZEN_PRE_AUDIT`
Frozen date: 2026-08-21
Scope: qualify ETHUSDT Spot 15m as a possible external market-state input for later BTC research.

## Purpose

M10 is a data-eligibility audit only. It asks whether ETHUSDT Spot 15m history for the already-used
development years can be acquired reproducibly and is structurally clean enough to support a later,
separately frozen cross-asset edge-discovery cycle.

M10 must not compute BTC forward returns, ETH/BTC correlations, lead-lag statistics, trading signals,
PnL, risk sizing, AI outputs, or live execution evidence.

## Frozen data boundary

Audit window:
- `2021-01-01T00:00:00Z` to `2025-01-01T00:00:00Z` exclusive.

Frozen OOS:
- `2025-01-01T00:00:00Z` to `2026-01-01T00:00:00Z`
- status: `LOCKED_NOT_ACCESSED`

No ETHUSDT 2025 data is requested or inspected in M10.

## Frozen source

Primary source:
- Binance Vision public Spot monthly klines
- symbol: `ETHUSDT`
- interval: `15m`
- path family: `data/spot/monthly/klines/ETHUSDT/15m`
- official `.CHECKSUM` must be fetched for every present monthly ZIP.

Expected monthly archives:
- 48 files: 2021-01 through 2024-12 inclusive.

The audit must not silently substitute REST candles, another exchange, another symbol, another
interval, or an unverified mirror if a monthly archive/checksum is unavailable.

## Frozen parsing and normalization

Expected Binance kline fields:
1. open time
2. open
3. high
4. low
5. close
6. base volume
7. close time
8. quote volume
9. trade count
10. taker-buy base volume
11. taker-buy quote volume
12. ignore

A CSV header may be present or absent and is not data.

Timestamps:
- open and close timestamps are interpreted as integer Unix milliseconds;
- every accepted open timestamp must lie inside the frozen audit window;
- open timestamps must be aligned to an exact 15-minute UTC boundary;
- close time must equal `open_time + 15m - 1ms`.

Duplicate handling:
- byte-equivalent / field-equivalent duplicate rows for the same open timestamp may collapse to one;
- conflicting rows for the same open timestamp are forbidden;
- no interpolation, forward-fill, back-fill, synthetic candle, or timestamp repair is allowed.

Numeric integrity:
- OHLC must be finite and strictly positive;
- high must be >= open and close;
- low must be <= open and close;
- high must be >= low;
- base volume and quote volume must be finite and >= 0;
- trade count must be an integer >= 0;
- taker-buy base and quote volumes must be finite and >= 0;
- taker-buy base volume may not exceed base volume beyond floating-point tolerance;
- taker-buy quote volume may not exceed quote volume beyond floating-point tolerance.

## Frozen coverage expectations

15m step: `900000` ms.

Expected full-window slots:
- `140256`.

Coverage is measured after deterministic duplicate collapse:
- `accepted_unique_rows / 140256`.

Missing-run length is measured in consecutive expected 15m slots absent from the normalized series.

## Frozen PASS gates

M10 passes only if all are true:

1. all 48 expected monthly ZIP files exist;
2. all 48 present ZIPs match their official `.CHECKSUM`;
3. no monthly parse error occurs;
4. conflicting duplicate open timestamps = 0;
5. first normalized open timestamp equals `2021-01-01T00:00:00Z`;
6. last normalized open timestamp equals `2024-12-31T23:45:00Z`;
7. normalized timestamps are unique and strictly increasing;
8. every normalized open timestamp is 15m-aligned;
9. every close timestamp has exact 15m close-time semantics;
10. all frozen OHLC/volume/trade/taker numeric integrity checks pass;
11. normalized coverage >= `0.9995` (99.95%);
12. maximum missing run <= `12` bars (3 hours);
13. normalized row count does not exceed the frozen expected slot count;
14. 2025 OOS status remains `LOCKED_NOT_ACCESSED`.

The gates are not weakened after observing the audit.

## Evidence

The audit report must record:
- monthly file/checksum manifest;
- missing months;
- source row count;
- exact duplicate count;
- conflicting duplicate count;
- accepted normalized row count;
- expected row count;
- coverage;
- missing slot count;
- maximum missing run;
- first/last timestamps;
- each integrity gate;
- SHA-256 of the deterministic normalized ETHUSDT 15m CSV;
- source provenance / code commit when available;
- final decision.

Decision:
- all frozen gates pass -> `M10_CROSS_ASSET_DATA_AUDIT_PASS`;
- otherwise -> `M10_CROSS_ASSET_DATA_AUDIT_FAIL`.

## Research consequence

A PASS only makes ETHUSDT 15m eligible as an input to a new separately versioned cross-asset
edge-discovery contract. It does not establish an edge and does not authorize a strategy.

A FAIL blocks ETHUSDT under this exact M10 contract. It may not be rescued by weakening coverage,
gap, duplicate, timestamp, or integrity gates after the result.

2025 remains untouched throughout M10.
