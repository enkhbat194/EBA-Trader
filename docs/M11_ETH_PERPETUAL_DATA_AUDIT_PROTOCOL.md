# M11 ETHUSDT USD-M Perpetual Historical Data Audit Protocol

Status: `FROZEN_PRE_AUDIT`
Frozen date: 2026-08-21
Scope: qualify ETHUSDT USD-M perpetual 15m as a separate cross-asset derivatives input source.

## Purpose

M11 is a data-eligibility audit only. It tests whether official ETHUSDT USD-M perpetual 15m history
for 2021-2024 is reproducible and structurally clean enough for a later, separately frozen BTC
cross-asset edge-discovery cycle.

M11 must not compute BTC forward returns, ETH/BTC correlations, lead-lag statistics, trading signals,
PnL, risk sizing, AI outputs, or live execution evidence.

M11 is not a repair of the failed M10 ETHUSDT Spot contract. The market/source family is separate.

## Frozen data boundary

Audit window:
- `2021-01-01T00:00:00Z` to `2025-01-01T00:00:00Z` exclusive.

Frozen OOS:
- `2025-01-01T00:00:00Z` to `2026-01-01T00:00:00Z`
- status: `LOCKED_NOT_ACCESSED`

No ETHUSDT 2025 archive is requested or inspected.

## Frozen source

Primary source:
- Binance Vision public USD-M futures monthly klines
- instrument: ETHUSDT USD-M perpetual
- interval: 15m
- path family: `data/futures/um/monthly/klines/ETHUSDT/15m`
- every present ZIP must match the official `.CHECKSUM`.

Expected monthly archives:
- 48 files: 2021-01 through 2024-12 inclusive.

No REST substitution, alternate exchange, Spot substitution, mirror, interpolation, or source repair is
allowed inside M11.

## Frozen row schema and normalization

Expected kline fields:
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

A header row may be present and is not data.

Timestamps:
- open and close timestamps are integer Unix milliseconds;
- open time must lie inside the frozen audit window;
- every open timestamp must align to an exact 15-minute UTC boundary;
- close time must equal `open_time + 15m - 1ms`.

Duplicate handling:
- exact field-equivalent duplicates for one open timestamp may collapse to one;
- conflicting rows for one open timestamp are forbidden;
- no timestamp or candle repair is permitted.

Numeric integrity:
- OHLC finite and strictly positive;
- high >= open and close;
- low <= open and close;
- high >= low;
- base volume and quote volume finite and >= 0;
- trade count integer and >= 0;
- taker-buy base and quote volumes finite and >= 0;
- taker-buy base volume <= base volume within floating-point tolerance;
- taker-buy quote volume <= quote volume within floating-point tolerance.

## Frozen coverage expectations

15m step: 900000 ms.
Expected full-window slots: 140256.

Coverage:
- `accepted_unique_rows / 140256`.

Maximum missing run:
- longest consecutive sequence of absent expected 15m slots.

## Frozen PASS gates

M11 passes only if all are true:

1. all 48 expected monthly ZIP archives exist;
2. all 48 archives match official `.CHECKSUM`;
3. no monthly parse error;
4. conflicting duplicate timestamps = 0;
5. exact first open time = `2021-01-01T00:00:00Z`;
6. exact last open time = `2024-12-31T23:45:00Z`;
7. timestamps unique and strictly increasing;
8. all open timestamps 15m-aligned;
9. exact close-time semantics on every accepted row;
10. OHLC/activity numeric integrity passes on every accepted row;
11. coverage >= 0.9995 (99.95%);
12. maximum missing run <= 12 bars (3 hours);
13. normalized row count <= 140256;
14. 2025 OOS remains `LOCKED_NOT_ACCESSED`.

The gates are not weakened after observing the audit.

## Evidence

The first complete report must record:
- all 48 monthly checksum/source statuses;
- source and accepted row counts;
- duplicates/conflicts;
- timestamp/close-time/numeric violations;
- coverage, missing slots and maximum missing run;
- exact first/last timestamps;
- all gate results;
- SHA-256 of the deterministic normalized ETHUSDT USD-M perpetual 15m CSV;
- source provenance;
- final decision.

Decision:
- all frozen gates pass -> `M11_ETH_PERPETUAL_DATA_AUDIT_PASS`;
- otherwise -> `M11_ETH_PERPETUAL_DATA_AUDIT_FAIL`.

## Research consequence

PASS only qualifies this exact ETHUSDT USD-M perpetual 15m dataset as a potential external input.
It does not establish a predictive edge or authorize a strategy.

FAIL closes this exact M11 contract without threshold relaxation or repair.

2025 remains untouched.
