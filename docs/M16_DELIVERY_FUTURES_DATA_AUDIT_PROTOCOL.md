# M16 Delivery Futures Historical Data Audit Protocol

Status: `FROZEN_PREDECLARED_DATA_AUDIT`

## Purpose

Determine whether Binance's official historical quarterly delivery-futures archives provide a reproducible 15m dataset suitable for a later, separately frozen cash-and-carry study.

M16 is data provenance only. It must not compute Spot-vs-delivery basis profitability, forward returns, trade entries, PnL, strategy parameters, or risk sizing.

## Candidate source families

Audit both families independently:

1. USD-M archive family: `data/futures/um/monthly/klines/BTCUSDT_YYMMDD/15m/`.
2. COIN-M archive family: `data/futures/cm/monthly/klines/BTCUSD_YYMMDD/15m/`.

Files must come from Binance's official `data.binance.vision` archive and every existing ZIP must verify against its adjacent `.CHECKSUM`.

No unofficial mirrors or reconstructed candles are allowed.

## Frozen contract calendar

Quarterly delivery dates are predeclared as the last Friday of March, June, September, and December for each year 2021-2024, at 08:00 UTC.

Expected suffixes:

- 2021: `210326`, `210625`, `210924`, `211231`
- 2022: `220325`, `220624`, `220930`, `221230`
- 2023: `230331`, `230630`, `230929`, `231229`
- 2024: `240329`, `240628`, `240927`, `241227`

The audit constructs symbols directly from this frozen calendar. It may record a family as unavailable if Binance did not publish that symbol/archive. Missing archives are evidence, not a reason to change the calendar after the run.

## Frozen audit window per contract

For each expected contract, audit exactly the final 30 calendar days before the predeclared 08:00 UTC delivery timestamp:

`[delivery_time - 30 days, delivery_time)`

Only 15m bars whose open timestamps fall inside that window count toward coverage.

Expected slots per contract: `30 × 24 × 4 = 2,880`.

## Integrity gates per contract

A contract passes only if all are true:

- every required monthly ZIP that contains accepted rows has a valid official SHA-256 `.CHECKSUM`;
- at least one verified archive exists;
- open timestamps are unique and strictly increasing after normalization;
- every accepted open timestamp is aligned to 15m UTC;
- every close timestamp equals `open_time + 15m - 1ms`;
- OHLC values are finite and positive;
- volume, quote volume and trade count are non-negative when present;
- accepted coverage is at least `99.90%` of 2,880 slots;
- maximum consecutive missing run is at most `4` bars (1 hour);
- the final accepted bar opens no earlier than 60 minutes before delivery;
- duplicate timestamps with conflicting OHLC are forbidden.

No interpolation or forward/back filling is allowed.

## Family-level eligibility

A source family is `DELIVERY_DATA_ELIGIBLE` only if:

- all 12 discovery contracts from 2021-2023 pass; and
- all 4 reused-development-challenge contracts from 2024 pass.

Anything less is `DELIVERY_DATA_NOT_ELIGIBLE`.

USD-M and COIN-M are judged separately. One family may pass while the other fails.

## Chronology and holdout

This audit may inspect only the predeclared 2021-2024 delivery contracts and their final 30-day windows.

2024 remains reused development data, not pristine OOS.

2025-01-01 through 2026-01-01 remains `LOCKED_NOT_ACCESSED`. No 2025 delivery symbol or archive may be requested.

## Frozen outputs

The immutable first complete report must record:

- every requested archive URL;
- archive existence and checksum status;
- accepted row count per contract;
- coverage;
- missing slot count;
- maximum missing run;
- first/last accepted timestamps;
- timestamp/close-time/numeric/duplicate/conflict violations;
- normalized SHA-256 per passing contract;
- family-level decision;
- overall decision;
- `oos_2025 = LOCKED_NOT_ACCESSED`.

## Prohibited actions

- no basis/PnL/return computation in M16;
- no changing delivery dates after seeing availability;
- no lowering coverage or gap gates after the run;
- no filling missing bars;
- no unofficial data source substitution;
- no 2025 requests;
- no strategy generation, risk sizing, AI signal, or live execution.

Only a family that passes this audit may be used in a later separately frozen delivery-futures cash-and-carry study.
