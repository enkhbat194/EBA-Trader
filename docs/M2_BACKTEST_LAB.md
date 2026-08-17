# M2 — Historical Data & Backtest Laboratory

## Goal

Build a zero-cost research path that can test BTC/USDT Spot strategies before any paper or live execution is introduced.

## Safety invariant

M2 contains no exchange account access and no order-execution code. Historical data is downloaded from Binance public REST only.

## Baseline design

- market: BTC/USDT Spot;
- interval: 15 minutes;
- strategy: long-only EMA 20/50 trend crossover;
- signal uses only the completed current candle;
- execution is modeled at the **next candle open**;
- benchmark: BTC buy-and-hold over the same effective period;
- parameter tuning: disabled for the first baseline.

### Frozen evidence windows

- `research`: 2021-01-01 inclusive → 2024-01-01 exclusive;
- `validation`: 2024-01-01 inclusive → 2025-01-01 exclusive;
- `out_of_sample`: 2025-01-01 inclusive → 2026-01-01 exclusive;
- 2026+ remains outside the first baseline cycle.

The 2025 OOS is locked during development. Development code also refuses to claim the holdout is clean if a 2025 cache file already exists.

## Development evidence

Preferred network command:

```bash
eba-development-study
```

It:

1. verifies no 2025 OOS cache exists;
2. downloads/caches only 2021–2024 development data;
3. runs EMA 20/50 baseline under base/adverse/severe costs;
4. runs parameter-neighborhood robustness on research data;
5. runs rolling walk-forward on research data;
6. runs causal regime diagnostics on research and validation;
7. writes `artifacts/m2_development_evidence.json`;
8. records `oos_2025=LOCKED_NOT_ACCESSED`.

The neighborhood test is a fragility check. It does **not** authorize selecting a better-looking neighboring EMA pair for this first cycle.

## Candidate freeze gate

If development evidence rejects EMA 20/50, stop the cycle and create a new hypothesis without opening 2025.

If EMA 20/50 is retained, freeze exactly the predeclared baseline:

```bash
eba-freeze-oos-candidate
```

The command accepts no EMA parameters. It reads `development_report.frozen_baseline`, writes `artifacts/m2_frozen_candidate.json`, and stores the SHA-256 hash of the development evidence report.

After freeze:

- changing the development evidence invalidates the freeze;
- overwriting the frozen candidate is blocked;
- the OOS command cannot accept ad-hoc `--fast/--slow` overrides.

## Frozen OOS opening

Only after the candidate freeze exists:

```bash
eba-oos-study --confirm-frozen
```

The command:

- verifies the development-report hash;
- verifies the frozen EMA pair still matches the development baseline;
- opens 2025 once;
- writes `artifacts/m2_trend_oos_2025.json`;
- refuses to rerun if the report already exists.

Retuning after OOS is opened is forbidden. A failed OOS returns the project to a **new** research cycle; 2025 must not become a tuning dataset.

## Data integrity gates

Every opened dataset must pass:

- strictly increasing timestamps;
- no duplicate candles;
- sane OHLC relationships;
- zero missing expected 15-minute intervals.

All window end timestamps are exclusive to prevent boundary leakage.

## Cost stress

| Scenario | Fee / side | Slippage / side |
|---|---:|---:|
| Base | 10 bps | 5 bps |
| Adverse | 10 bps | 10 bps |
| Severe | 15 bps | 20 bps |

These are research assumptions, not claims about a future account fee tier.

## Required metrics

- final equity;
- total and annualized return;
- BTC buy-and-hold return;
- benchmark-relative return;
- maximum drawdown;
- trade count;
- win rate;
- profit factor;
- expectancy;
- average win/loss;
- Sharpe and Sortino;
- exposure;
- estimated transaction/slippage costs.

## Interpretation rules

1. Positive return alone is not a pass.
2. Buy-and-hold is mandatory.
3. Lower return must be justified by materially better risk characteristics.
4. Very low trade count is insufficient evidence.
5. High win rate with weak profit factor/expectancy is failure-prone.
6. Results erased by adverse/severe costs are fragile.
7. One winning EMA pair surrounded by failures is an overfitting warning.
8. The frozen OOS is never a tuning dataset.
9. No M2 result authorizes live money.

## Acceptance path

### M2A — Plumbing
Historical data, integrity gates, next-bar execution, costs, benchmark, deterministic tests.

### M2B — Development evidence
Research/validation, cost stress, parameter neighborhood, walk-forward, causal regime diagnostics, development review.

### M2C — Frozen OOS
Freeze the predeclared retained baseline, hash the development evidence, open 2025 once, do not retune.

M2C must pass before PAPER execution is considered.
