# M8 Alternative Derivatives Historical Data Audit Protocol

Status: `FROZEN_PRE_AUDIT`
Frozen date: 2026-08-21
Scope: BTCUSDT alternative public derivatives and microstructure data, development-only.

## Purpose

M8 does not search for a trading strategy and does not compute forward-return edge evidence.
It determines whether materially new positioning, cross-exchange, order-book, and liquidation data
can be reproduced for development research without touching the frozen 2025 OOS holdout.

Development audit window:
- start: `2021-01-01T00:00:00Z`
- end exclusive: `2025-01-01T00:00:00Z`

Frozen holdout:
- `2025-01-01T00:00:00Z` to `2026-01-01T00:00:00Z`
- status: `LOCKED_NOT_ACCESSED`

The primary objective is to find full-window data families that are materially different from M5/M7
price-volume/funding-flow searches. Secondary partial-window archives are audited separately and may
never be silently promoted to full-window evidence.

## Frozen source families

### A. Binance USD-M 5m metrics — primary

Official Binance Vision daily archive:
`data/futures/um/daily/metrics/BTCUSDT/`

Frozen fields:
- `create_time`
- `symbol`
- `sum_open_interest`
- `sum_open_interest_value`
- `count_toptrader_long_short_ratio`
- `sum_toptrader_long_short_ratio`
- `count_long_short_ratio`
- `sum_taker_long_short_vol_ratio`

This family is materially new because M7 did not use historical open interest or trader-positioning
ratios.

### B. Bybit BTCUSDT linear perpetual public history — primary

Official public V5 market endpoints, no API key:
- `GET /v5/market/kline` with `category=linear`, `symbol=BTCUSDT`, `interval=60`
- `GET /v5/market/open-interest` with `category=linear`, `symbol=BTCUSDT`, `intervalTime=1h`
- `GET /v5/market/account-ratio` with `category=linear`, `symbol=BTCUSDT`, `period=1h`
- `GET /v5/market/funding/history` with `category=linear`, `symbol=BTCUSDT`

The Bybit kline is an alignment/control series. Bybit open interest and account ratio are materially
new cross-exchange positioning inputs. Bybit funding is audited only to determine whether a future
cross-exchange funding-spread feature is reproducible.

### C. Binance USD-M bookDepth — secondary partial-window audit

Official Binance Vision daily archive:
`data/futures/um/daily/bookDepth/BTCUSDT/`

Public archive availability is known not to cover the entire 2021-2024 development window. M8 audits
its actual availability and data integrity, but bookDepth cannot qualify as a full-window M8 primary
family unless the official archive unexpectedly covers the frozen full window.

A separate result `PARTIAL_WINDOW_ELIGIBLE` may be issued for the fixed secondary window:
- `2023-01-01T00:00:00Z` to `2025-01-01T00:00:00Z` exclusive.

Partial-window eligibility does not authorize combining it with full-window tests after results are
seen. Any future book-depth edge study requires its own predeclared contract and must explicitly use
the shorter data window.

### D. Binance USD-M liquidationSnapshot — secondary full-window availability test

Official Binance Vision daily archive:
`data/futures/um/daily/liquidationSnapshot/BTCUSDT/`

M8 requires full-window coverage for later confirmatory use. If the archive ends materially before
2025-01-01, the family is classified `EXCLUDED_INCOMPLETE_HISTORY`.

## Excluded from this audit

- 2025 OOS data from every venue
- failed M6 Binance premium-index and index-price families
- paid vendor data
- order-level private account data
- news, social media, macro data
- AI-generated features
- any strategy, PnL, forward-return target, or parameter search

Paid vendors may be considered only after the free official-source audit is complete and only under a
separate cost/provenance review.

## Causality and security

- Public market-data endpoints only.
- No API key, account, wallet, order, position-management, withdrawal, or leverage endpoint.
- Every request builder must reject any range whose end exceeds `2025-01-01T00:00:00Z` or whose
  requested interval overlaps the frozen 2025 holdout.
- All timestamps are UTC.
- No forward fill across source gaps is permitted in later research.
- Later features must reset state after source gaps.
- API pagination must be deterministic and deduplicate only under the frozen rules below.
- No forward returns or PnL may be computed inside M8.

## Frozen audit criteria

### A. Binance metrics 5m

Expected accepted timestamp grid:
- greater than audit start;
- less than audit end;
- aligned to five-minute UTC boundaries.

PASS only if all are true:
- every downloaded ZIP is verified against its Binance Vision `.CHECKSUM`;
- all parsed rows are BTCUSDT and inside the frozen audit window;
- timestamps are monotonic after deterministic normalization;
- exact duplicate timestamps may be collapsed only when every frozen metric field is identical;
- any conflicting duplicate timestamp is a hard FAIL;
- coverage is at least 99.50% of the expected five-minute grid;
- maximum missing run is no more than 288 consecutive five-minute slots (24 hours);
- `sum_open_interest` and `sum_open_interest_value` are finite and strictly positive;
- all four ratio fields are finite and strictly positive;
- no row contains NaN or infinity.

Result labels:
- `FULL_WINDOW_PASS`
- `FAIL`

### B. Bybit 1h kline

PASS only if:
- API responds successfully without credentials;
- timestamps are unique, UTC-hour aligned, and inside the frozen window;
- coverage is at least 99.90% of expected hourly slots;
- maximum missing run is no more than 6 consecutive hours;
- OHLC are finite and strictly positive with valid high/low relationships;
- volume and turnover are finite and non-negative.

### C. Bybit 1h open interest

PASS only if:
- API documents/returns history spanning the frozen window;
- timestamps are unique and UTC-hour aligned;
- coverage is at least 99.50%;
- maximum missing run is no more than 24 consecutive hours;
- open interest is finite and strictly positive.

### D. Bybit 1h long/short account ratio

PASS only if:
- timestamps are unique and UTC-hour aligned;
- coverage is at least 99.50%;
- maximum missing run is no more than 24 consecutive hours;
- buy and sell ratios are finite and each is in `[0, 1]`;
- `abs((buy_ratio + sell_ratio) - 1.0) <= 0.02` for every accepted row.

### E. Bybit funding history

PASS only if:
- timestamps are unique and strictly increasing after normalization;
- at least 4,000 records are present in the full audit window;
- first record is no later than 24 hours after the audit start;
- last record is no earlier than 24 hours before the audit end;
- every funding rate is finite with absolute value <= 5%;
- maximum positive cadence is no more than 24 hours.

### F. Cross-exchange primary alignment

Construct an hourly alignment set using:
- Bybit 1h kline timestamps;
- Bybit 1h open-interest timestamps;
- Bybit 1h account-ratio timestamps;
- Binance 5m metrics reduced causally to the latest completed metric timestamp at or before each UTC
  hour, with maximum staleness of 10 minutes.

PASS only if:
- at least 99.00% of expected hourly slots have Bybit kline plus at least one Bybit positioning
  series (`open_interest` or `account_ratio`) and a non-stale Binance metrics observation;
- no aligned Binance observation comes from after the hour being evaluated.

### G. Binance bookDepth secondary window

For `2023-01-01` through `2025-01-01` exclusive, `PARTIAL_WINDOW_ELIGIBLE` only if:
- at least 99.00% of expected daily files exist;
- every downloaded existing ZIP passes `.CHECKSUM`;
- rows parse as timestamp, percentage, depth, notional;
- percentage is one of `-5,-4,-3,-2,-1,1,2,3,4,5`;
- depth and notional are finite and non-negative;
- at least 95% of distinct snapshot-to-snapshot positive gaps within a day are <= 120 seconds;
- no future 2025 timestamp is accessed.

Otherwise result is `PARTIAL_WINDOW_FAIL`.

Regardless of this result, bookDepth is not a full-window M8 primary family.

### H. Binance liquidationSnapshot full-window test

`FULL_WINDOW_PASS` only if:
- at least 99.00% of expected daily files from 2021-01-01 through 2024-12-31 exist;
- the last available daily file is no earlier than 24 hours before the audit end;
- every downloaded existing ZIP passes `.CHECKSUM`;
- timestamps and numeric fields parse successfully;
- exact duplicate rows may be collapsed, but conflicting duplicate records fail.

Otherwise result is `EXCLUDED_INCOMPLETE_HISTORY`.

## M8 core decision

`ELIGIBLE_FOR_M8_POSITIONING_EDGE_DESIGN` only if all are true:
1. Binance 5m metrics = `FULL_WINDOW_PASS`;
2. Bybit 1h kline = PASS;
3. at least one of Bybit 1h open interest or Bybit 1h account ratio = PASS;
4. cross-exchange primary alignment = PASS.

Bybit funding PASS is optional and only enables a future cross-exchange funding-spread candidate family.

BookDepth and liquidationSnapshot are secondary classifications and do not block the core positioning
decision. Their failure cannot be rescued by weakening their frozen criteria.

If the four core conditions are not met, decision:
`M8_ALT_DERIVATIVES_DATA_AUDIT_FAIL`.

## After the audit

A data PASS proves only reproducibility and alignment. It does not prove predictive edge.

Only after the M8 audit is closed may a new edge-discovery protocol be written. That later protocol
must predeclare a small search space before computing forward returns and must keep 2025 locked.

Forbidden after seeing the audit result:
- weakening coverage or gap criteria;
- silently changing the audited window;
- substituting a paid or third-party dataset under the same M8 contract;
- treating partial bookDepth or incomplete liquidation history as full-window data;
- computing an edge first and writing the hypothesis afterward;
- opening 2025.
