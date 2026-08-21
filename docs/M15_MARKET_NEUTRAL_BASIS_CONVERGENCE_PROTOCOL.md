# M15 Market-Neutral Basis Convergence Protocol

Status: `FROZEN_PREDECLARED_NOT_RUN`

## Purpose

Test a materially new market-neutral BTC basis-convergence mechanism using the already qualified BTCUSDT Spot, BTCUSDT USD-M perpetual, and BTCUSDT funding-history inputs.

M15 is not a rescue of M14. M14 entered from positive funding-rate thresholds. M15 enters only from a completed-bar Spot/perpetual basis dislocation and exits on basis convergence or a frozen time stop.

No live trading, risk sizing, leverage, or naked directional shorting is permitted.

## Instruments and hedge

- Long BTCUSDT Spot: `1.0 USD` entry notional.
- Short BTCUSDT USD-M perpetual: `1.0 USD` entry notional.
- Total capital denominator: `2.0 USD`.
- Hedge ratio: fixed `1:1` entry notional.
- Leverage: forbidden.
- Naked short: forbidden.
- Overlapping positions: forbidden.

## Frozen inputs

Only the exact previously qualified 2021-2024 files may be used:

- BTCUSDT Spot research 2021-2023.
- BTCUSDT Spot reused challenge 2024.
- BTCUSDT USD-M perpetual 15m 2021-2024.
- BTCUSDT USD-M funding history 2021-2024.

2025-01-01 through 2026-01-01 remains `LOCKED_NOT_ACCESSED`.

## Causal signal and execution

For each completed aligned 15m bar t:

`basis_t = perpetual_close_t / spot_close_t - 1`

A configuration signals only when `basis_t >= frozen_entry_basis`.

Entry occurs at the next aligned 15m open after the completed signal bar. Signal-bar closes may never be used as executable prices.

After entry, the position is closed at the earlier of:

1. the next aligned 15m open after a completed bar whose basis is `<= 0.0010` (10 bps), or
2. the exact frozen maximum holding time measured from entry.

The convergence exit threshold is fixed at `0.0010` for every configuration.

Funding records with `entry_time <= funding_time < exit_time` are included in PnL. A short perpetual receives positive funding and pays negative funding. Historical funding mark price is used when available; the already-audited completed perpetual close fallback may be used otherwise.

## Frozen search surface

Entry basis thresholds:

- `0.0075` (75 bps)
- `0.0125` (125 bps)
- `0.0200` (200 bps)

Maximum holding periods in 15m bars:

- `96` bars (~24h)
- `288` bars (~72h)
- `672` bars (~7d)

Total configurations: `3 × 3 = 9`.

No threshold, exit level, holding period, hedge ratio, cost, or sign may be changed after the first complete result.

## Costs

Base friction: `15 bps` per side per leg.

Severe friction: `35 bps` per side per leg.

Both entry and exit on both legs are charged. Funding cashflow and Spot/perpetual mark-to-market are included before costs.

## Development chronology

Discovery: 2021-01-01 through 2024-01-01 exclusive.

Reused development challenge: 2024-01-01 through 2025-01-01 exclusive, only for a configuration that passes every discovery gate.

2024 is not pristine OOS. 2025 remains untouched.

## Statistical unit and multiple testing

Trade-level Base-net returns are aggregated to UTC entry-day means for the one-sided positive-mean significance test.

Benjamini-Hochberg FDR is applied across all 9 frozen discovery configurations.

Frozen FDR promotion threshold: `q <= 0.10`.

## Discovery promotion gates

A configuration must satisfy every gate:

- at least 20 trades;
- at least 15 distinct UTC entry days;
- at least 3 trades in each of 2021, 2022, and 2023;
- positive mean Base-net return;
- positive mean Severe-net return;
- positive median Base-net return;
- Base-net profit factor `> 1.20`;
- each discovery year has positive mean Base-net return;
- BH-FDR `q <= 0.10`.

Any failed discovery gate blocks 2024 challenge execution for that configuration.

## Reused-2024 challenge gates

If and only if discovery passes:

- at least 5 trades;
- positive mean Base-net return;
- positive mean Severe-net return;
- positive median Base-net return;
- Base-net profit factor `> 1.20`.

A configuration passing discovery and challenge is classified `MARKET_NEUTRAL_BASIS_CANDIDATE`.

Everything else is `OBSERVATION_ONLY`.

## Prohibited actions

- no 2025 access;
- no after-result threshold changes;
- no changing the fixed 10-bps exit level;
- no hold-period rescue;
- no sign flip to negative-basis trades;
- no leverage;
- no naked short;
- no overlapping positions;
- no cost relaxation;
- no strategy deployment or risk sizing from a failed result.

This first complete frozen evidence result is immutable.
