# M17 USD-M Quarterly Cash-and-Carry Protocol

Status: `FROZEN_PREDECLARED_NOT_RUN`

## Purpose

Test a structurally different market-neutral mechanism using only M16-qualified Binance USD-M quarterly BTC delivery futures and the already frozen BTCUSDT Spot development data.

M17 is not a rescue of M14 or M15. It does not use perpetual funding thresholds or assume a perpetual basis will mean-revert. It measures convergence of a dated delivery future toward Spot as delivery approaches.

No live execution, risk sizing, leverage, or naked directional shorting is permitted.

## Qualified inputs

Only these inputs are allowed:

- BTCUSDT Spot research 2021-2023, frozen SHA-256 `253c6ae35856e58e35df17eaa71caeea5caaa3681c38dd7214a2872afccd8d63`.
- BTCUSDT Spot reused challenge 2024, frozen SHA-256 `3a96b6b668cfacb0fefabb8665675d4ca589cc712b0681fb57e7a13356eda0f2`.
- M16-qualified USD-M quarterly contracts `BTCUSDT_YYMMDD`, final 30 days only, each re-downloaded from official Binance Vision archives and required to reproduce its frozen M16 normalized SHA-256.

COIN-M is forbidden because M16 did not qualify the family.

2025-01-01 through 2026-01-01 remains `LOCKED_NOT_ACCESSED`.

## Hedge and capital

For each trade:

1. Buy BTCUSDT Spot using exactly `1.0 USD` notional at entry.
2. Let `q = 1.0 / spot_entry_price` BTC.
3. Short exactly the same BTC quantity `q` in the USD-M quarterly delivery future.
4. Futures margin allocated for the research denominator equals the full entry futures notional `q * futures_entry_price`; leverage is therefore modeled as 1x / fully funded.
5. Capital denominator is `1.0 + q * futures_entry_price`.

Using the same BTC quantity on both legs keeps the pair delta-neutral apart from execution frictions and the Spot/futures basis.

## Frozen entry configurations

Exactly one trade per contract is measured for each configuration.

Entry offsets before scheduled 08:00 UTC delivery:

- 28 days;
- 14 days;
- 7 days.

The entry timestamp is exactly the aligned 15m open at `delivery_time - entry_offset`.

No basis threshold is used. No entry is skipped because the observed basis is unattractive; doing so after seeing outcomes would create selection bias.

Total frozen configurations: 3.

## Frozen exit

Every trade exits both legs at the aligned 15m open exactly 15 minutes before scheduled delivery (`delivery_time - 15 minutes`).

M17 deliberately exits before delivery. It therefore does not estimate, reconstruct, or depend on the exchange's final settlement price or delivery fee.

No early basis-convergence exit, stop-profit, stop-loss, or rolling rule is allowed.

## PnL

With identical BTC quantity `q` on both legs:

- Spot PnL = `q * (spot_exit - spot_entry)`.
- Futures-short PnL = `q * (futures_entry - futures_exit)`.
- Gross PnL = Spot PnL + Futures-short PnL.
- Gross return = Gross PnL / frozen capital denominator.

Delivery futures have no perpetual funding cashflow in this study.

## Costs

Base friction: `15 bps` per side per leg.

Severe friction: `35 bps` per side per leg.

Costs apply to entry and exit turnover of both legs using their actual notional values.

No maker rebate, VIP discount, BNB discount, or fee rescue is allowed.

## Margin-safety diagnostic and gate

The futures leg is modeled with margin equal to 100% of its entry notional.

For each trade, inspect every qualified futures bar from entry through exit and compute the worst short-side adverse excursion from the bar high.

`margin_remaining_ratio = 1 - max(0, max_futures_high / futures_entry - 1)`

A trade is margin-safe only if `margin_remaining_ratio >= 0.50`.

This is a conservative research gate, not an exchange liquidation-price model.

## Development chronology

Discovery contracts: all 12 quarterly expiries in 2021, 2022, and 2023.

Reused development challenge: all 4 quarterly expiries in 2024, evaluated only for configurations that pass every discovery gate.

2024 is not pristine OOS. 2025 remains untouched.

## Statistical unit

The independent research unit is one quarterly contract return.

For each frozen configuration, discovery contains exactly 12 contract returns if all required timestamps are available.

A deterministic one-sided exact sign-flip permutation test is applied to the mean Base-net return across the 12 discovery contracts.

Benjamini-Hochberg FDR is applied across the 3 frozen discovery configurations.

Frozen promotion threshold: `q <= 0.10`.

## Discovery promotion gates

A configuration must satisfy every gate:

- exactly 12 valid discovery trades;
- positive mean Base-net return;
- positive mean Severe-net return;
- positive median Base-net return;
- positive median Severe-net return;
- Base-net profit factor `> 1.20`;
- Severe-net profit factor `> 1.00`;
- Base-net win rate `>= 0.75`;
- every discovery year (2021, 2022, 2023) has 4 trades and positive mean Base-net and Severe-net return;
- every trade passes the frozen margin-safety gate;
- exact sign-flip BH-FDR `q <= 0.10`.

Any failed discovery gate blocks 2024 challenge execution for that configuration.

## Reused-2024 challenge gates

If and only if discovery passes:

- exactly 4 valid trades;
- positive mean Base-net return;
- positive mean Severe-net return;
- positive median Base-net return;
- positive median Severe-net return;
- Base-net profit factor `> 1.20`;
- at least 3 of 4 trades have positive Severe-net return;
- every trade passes the frozen margin-safety gate.

A configuration passing discovery and challenge is classified `MARKET_NEUTRAL_DELIVERY_CARRY_CANDIDATE`.

Everything else is `OBSERVATION_ONLY`.

## Prohibited actions

- no 2025 access;
- no COIN-M use;
- no after-result change to entry offsets;
- no basis threshold added after results;
- no settlement-price reconstruction to rescue a result;
- no early exit or hold-period rescue;
- no sign flip;
- no leverage;
- no naked short;
- no cost relaxation;
- no dropping bad quarters;
- no strategy deployment or risk sizing from a failed result.

The first complete frozen evidence result is immutable.
