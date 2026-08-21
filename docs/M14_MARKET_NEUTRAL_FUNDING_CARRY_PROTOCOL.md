# M14 Market-Neutral Funding Carry — Frozen Research Protocol

Status: `FROZEN_PREDECLARED_NOT_RUN`

## Objective

Test a structurally different mechanism from prior directional research: market-neutral BTC funding carry using a 1:1 long BTCUSDT Spot + short BTCUSDT USD-M perpetual hedge with no leverage. Profit source is realized perpetual funding plus basis convergence/divergence, not directional BTC prediction.

This is research only. It does not authorize live shorting or live execution.

## Data

Only frozen qualified development inputs:

- BTCUSDT Spot 15m 2021–2023 SHA-256 `253c6ae35856e58e35df17eaa71caeea5caaa3681c38dd7214a2872afccd8d63`
- BTCUSDT Spot 15m 2024 SHA-256 `3a96b6b668cfacb0fefabb8665675d4ca589cc712b0681fb57e7a13356eda0f2`
- BTCUSDT USD-M perpetual 15m 2021–2024 SHA-256 `3c97c9b59ded32595f129a480a23e920823c0edbbf2e4f32c5d66e5020e35947`
- BTCUSDT funding 2021–2024 SHA-256 `73b9decde0d54a0609d55ccfd49131a6e825416b595d728457bb01a968b55fd6`

Discovery window: 2021-01-01 through 2024-01-01 exclusive.
Reused challenge: 2024-01-01 through 2025-01-01 exclusive.
2025 OOS remains `LOCKED_NOT_ACCESSED`.

## Causal signal

A funding record is known only at its payment timestamp.

Signal after a completed funding payment when the just-observed funding rate is positive and at or above a frozen threshold.

Entry occurs at the next common contiguous 15m open after that funding timestamp:

- long Spot with $1 notional;
- short perpetual with $1 notional;
- total unlevered capital denominator = $2.

No position may overlap another position. Signals while a position is open are ignored.

## Frozen thresholds and holding periods

Funding thresholds:

- 0.00010 = 1 bp
- 0.00030 = 3 bps
- 0.00050 = 5 bps

Holding periods are measured in subsequent funding records:

- 3 records, approximately 24h under normal cadence
- 9 records, approximately 72h under normal cadence

Total frozen configurations: 3 × 2 = 6.

No threshold, holding period, sign or exit rule may change after first complete evidence.

## Exit

For signal funding record i and hold N:

- position opens after funding i;
- it remains open through subsequent funding records i+1 ... i+N;
- exit occurs at the next common 15m open after funding record i+N;
- all funding cashflows i+1 ... i+N are included, positive or negative.

Discovery trades must enter and exit before 2024-01-01.
Challenge trades must enter and exit before 2025-01-01.

## PnL

At entry:

- buy Spot units = 1 / Spot entry price;
- short perpetual units = 1 / perpetual entry price.

Gross PnL:

- Spot: spot_units × (Spot_exit - Spot_entry)
- Perpetual short: perp_units × (Perp_entry - Perp_exit)
- Funding cashflow: sum(perp_units × funding_mark_price × funding_rate) for included funding payments.

If funding mark price is unavailable for a payment, use the most recent completed perpetual 15m close at or before the funding timestamp.

Capital return = total PnL / 2.

## Costs

Base per-side assumptions:

- Spot: 10 bps fee + 5 bps slippage = 15 bps
- Perpetual: 10 bps fee + 5 bps slippage = 15 bps

Severe per-side assumptions:

- each leg: 15 bps fee + 20 bps slippage = 35 bps

Costs apply at both entry and exit on both legs using actual traded notional. Net return is after costs divided by $2 initial capital.

## Statistics and discovery gates

Six discovery configurations are corrected with Benjamini-Hochberg FDR over one-sided daily mean Base-net return p-values. Required q <= 0.10.

All discovery gates required:

1. at least 12 completed non-overlapping trades;
2. at least 8 distinct UTC entry days;
3. at least 2 trades with entry in each of 2021, 2022, 2023;
4. mean Base-net return > 0;
5. mean Severe-net return > 0;
6. median Base-net return > 0;
7. Base-net profit factor > 1.20;
8. each 2021, 2022, 2023 mean Base-net return > 0;
9. BH-FDR q <= 0.10.

## 2024 challenge gates

Only discovery-passing configurations are eligible.

All required:

1. at least 4 completed non-overlapping trades;
2. mean Base-net return > 0;
3. mean Severe-net return > 0;
4. median Base-net return > 0;
5. Base-net profit factor > 1.20.

A configuration passing both stages is `MARKET_NEUTRAL_CARRY_CANDIDATE`.
If none pass, decision is `NO_STABLE_FUNDING_CARRY_EDGE_FOUND`.

## Safety

- No leverage.
- Paired hedge only; no naked perpetual short authority.
- No live execution.
- No risk sizing during M14.
- 2025 OOS remains untouched.
- Any passing candidate still requires a separately frozen paper/shadow execution validation before live consideration.
