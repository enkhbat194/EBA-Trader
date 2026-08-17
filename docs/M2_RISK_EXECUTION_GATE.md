# M2 — Risk-Sized Execution Gate

## Why this stage exists

The original EMA crossover backtest is a **signal/allocation diagnostic**. It moves between cash and BTC and is useful for testing whether the directional hypothesis has evidence.

It is not yet the final EBA Trader execution model.

The real bot must obey the deterministic Risk Engine. Therefore 2025 OOS must not be opened until the risk-sized execution layer is defined and validated using development data only.

## Predeclared first-cycle execution policy

Fixed before real historical development evidence:

- market: BTCUSDT Spot
- leverage: 1× only
- Trend signal: strict EMA 20/50 crossover
- ATR period: 14 completed 15m bars
- initial protective stop: 2.0 × ATR below executed entry
- planned risk per trade: 0.5% of current equity
- maximum position: available Spot cash; borrowing/leverage forbidden
- normal exit: bearish EMA crossover, executed next bar open
- protective exit: ATR stop; adverse gaps execute at the available bar open
- take profit: none in Trend V1
- daily loss entry halt: 2%
- maximum drawdown entry halt: 8%

These values are research assumptions and may prove bad. They cannot be changed after viewing the frozen 2025 OOS within the same cycle.

## Development order

1. Signal development evidence (2021–2024 only).
2. Signal predeclared screening.
3. Risk-sized execution evidence using the **same cached development datasets**.
4. Risk execution screening.
5. Only if both layers pass: final candidate freeze.
6. One-shot 2025 OOS.
7. OOS screening.
8. If OOS passes: forward PAPER/SHADOW — still no live money.

## Risk execution screening

Before final freeze, validation must satisfy all predeclared gates:

- at least 20 closed trades;
- positive base-cost return;
- positive expectancy;
- profit factor > 1.0;
- maximum planned risk per trade <= 0.5% equity;
- Spot notional does not exceed equity;
- base run does not hit the 8% hard drawdown halt;
- severe-cost return remains positive;
- severe-cost run does not hit the 8% hard drawdown halt.

Passing means only `ELIGIBLE_FOR_FINAL_FROZEN_OOS`.

## Evidence files

```text
artifacts/m2_risk_execution_evidence.json
artifacts/m2_risk_execution_verdict.json
```

The risk evidence records SHA-256 hashes of the 2021–2023 research CSV and 2024 validation CSV. Final freeze refuses the candidate if those development datasets change afterward.

## One-command development runtime

When offline audit is complete, the preferred temporary network command is:

```bash
git pull && bash scripts/run_m2_full_development.sh
```

It runs the complete tests first, then signal evidence/screening, then risk evidence/screening. It never opens 2025 OOS.
