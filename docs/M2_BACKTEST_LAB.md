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
- 2026+ remains outside the first baseline study so it can be used later as fresher evidence.

The downloader treats every end timestamp as **exclusive**. This prevents one boundary candle from leaking into two adjacent windows.

## Data integrity gates

Before a window can be backtested it must pass:

- strictly increasing timestamps;
- no duplicate candles;
- sane OHLC relationships;
- expected interval continuity with zero missing 15-minute bars.

The baseline study fails closed when an interval gap is detected.

## Cost stress

Every frozen window runs the same strategy under three scenarios:

| Scenario | Fee / side | Slippage / side |
|---|---:|---:|
| Base | 10 bps | 5 bps |
| Adverse | 10 bps | 10 bps |
| Severe | 15 bps | 20 bps |

These are research assumptions, not claims about a future account's exact fee tier.

## Metrics

The report includes:

- final equity;
- total return;
- annualized return;
- BTC buy-and-hold return;
- benchmark-relative return;
- maximum drawdown;
- trade count;
- win rate;
- profit factor;
- expectancy per trade;
- average win and average loss;
- interval-aware approximate Sharpe and Sortino ratios;
- market exposure;
- estimated fee/slippage cost.

## One-command network validation

Most M2 code and deterministic tests are developed without Replit. A networked runtime is needed only to obtain Binance historical data.

After the runtime has the latest package installed, the intended single study command is:

```bash
eba-baseline-study
```

It downloads/caches the three frozen windows, rejects interval gaps, runs base/adverse/severe cost stress and writes:

```text
artifacts/m2_trend_baseline.json
```

Cached market data stays under ignored `data/cache/` and is not committed to Git.

## Interpretation rules

1. Positive return alone is not a pass.
2. Buy-and-hold is a mandatory benchmark.
3. Lower return can only be justified by materially better drawdown/exposure/risk characteristics.
4. Very low trade count is insufficient evidence.
5. High win rate with weak profit factor/expectancy is a failure.
6. A result that disappears under adverse/severe costs is fragile.
7. The out-of-sample result cannot be used for parameter tuning without restarting the validation cycle.
8. No M2 result authorizes live money.

## Acceptance path

### M2A — Plumbing

- historical download works;
- data-integrity gates work;
- next-bar execution is enforced;
- costs and benchmark are included;
- deterministic unit tests pass.

### M2B — Evidence quality

- frozen research/validation/out-of-sample windows complete;
- base/adverse/severe scenarios complete;
- report artifact is produced;
- result is reviewed against benchmark, drawdown and expectancy.

### M2C — Robustness (next)

Only after M2B:

- parameter-neighborhood tests;
- repeated walk-forward windows;
- regime-specific diagnostics;
- strategy rejection/promotion rules.

M2C must pass before a strategy can be considered for PAPER execution.
