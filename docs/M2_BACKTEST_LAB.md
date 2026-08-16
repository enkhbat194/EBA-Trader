# M2 — Historical Data & Backtest Laboratory

## Goal

Build a zero-cost research path that can test BTC/USDT Spot strategies before any paper or live execution is introduced.

## Safety invariant

M2 contains no exchange account access and no order-execution code. Historical data is downloaded from Binance public REST only.

## Current baseline

- market: BTC/USDT Spot;
- research interval: 15 minutes;
- strategy: long-only EMA trend crossover baseline;
- signal is computed using the completed current candle;
- entry/exit is executed at the **next candle open** to avoid same-bar look-ahead;
- base cost assumption: 10 bps fee + 5 bps slippage per side;
- benchmark: BTC buy-and-hold over the same effective period.

The baseline is deliberately simple. It is a benchmark, not a claim that EMA crossover is the final strategy.

## Replit / Linux workflow

After pulling the latest repository code and reinstalling the editable package:

```bash
python -m pip install -e '.[trading,dev]'
pytest -q
```

Download one year of 15-minute BTC/USDT candles:

```bash
eba-download-history \
  --symbol BTCUSDT \
  --interval 15m \
  --start 2025-01-01 \
  --end 2026-01-01 \
  --out data/raw/btcusdt_15m_2025.csv
```

Run Trend Following V1 baseline:

```bash
eba-backtest-trend --csv data/raw/btcusdt_15m_2025.csv
```

## Output to capture

- final equity;
- total strategy return;
- BTC buy-and-hold return;
- maximum drawdown;
- closed trade count;
- win rate;
- profit factor;
- expectancy in USD per trade;
- approximate Sharpe ratio;
- market exposure;
- estimated transaction/slippage cost.

## Interpretation rules

1. Positive return alone is not a pass.
2. Strategy return below buy-and-hold is not automatically useless, but lower drawdown/exposure must justify the difference.
3. Very low trade count is insufficient evidence.
4. A high win rate with poor profit factor is a failure.
5. Results must later survive out-of-sample, walk-forward and adverse-cost testing before PAPER status.
6. Parameters must not be tuned after seeing the reserved test result without restarting the validation cycle.

## M2 acceptance path

### M2A — Data and baseline plumbing

- historical download succeeds;
- timestamp/duplicate/OHLC integrity checks pass;
- unit tests pass;
- baseline produces deterministic metrics;
- fee/slippage costs are included;
- benchmark is reported.

### M2B — Evidence-quality validation

Next work after M2A:

- explicit train/test split;
- multiple market-regime windows;
- walk-forward evaluation;
- base/adverse/severe cost scenarios;
- parameter-neighborhood robustness;
- benchmark-relative report artifact.

M2B must pass before any strategy is considered for paper execution.
