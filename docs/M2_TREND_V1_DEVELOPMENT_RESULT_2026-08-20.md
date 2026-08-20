# M2 Trend V1 Development Result — 2026-08-20

## Decision

`REJECT_DEVELOPMENT_CYCLE`

The predeclared long-only strict EMA 20/50 signal baseline failed 8 of 10 development gates. The
risk-sized execution study was blocked by design, no final freeze was created, and 2025 OOS remains
`LOCKED_NOT_ACCESSED`.

## Provenance

- Git commit: `4f8f9087a83b7e3ce47306c8fcb10bc82af09aa4`
- Python: 3.12.14
- Tests: 124 passed
- Market/window: BTCUSDT 15m; research 2021–2023; validation 2024
- Research CSV: 105,050 source bars, plus 70 explicitly documented absent source intervals
- Validation CSV: 35,136 bars, no gaps

## Signal results

| Metric | Research base | Validation base | Validation severe |
|---|---:|---:|---:|
| Closed trades | 1,072 | 337 | 337 |
| Total return | -94.44% | -45.07% | -85.74% |
| Expectancy | -$0.88 | -$1.34 | -$2.54 |
| Profit factor | 0.757 | 0.770 | 0.458 |
| Maximum drawdown | -96.02% | -50.60% | -85.74% |
| BTC buy-and-hold return | 42.94% | 118.21% | 117.33% |
| BTC maximum drawdown | -77.23% | -32.44% | -32.44% |

Robustness diagnostics:

- parameter-neighborhood positive expectancy: 0%;
- walk-forward positive-return folds: 33.3%;
- walk-forward positive-expectancy folds: 33.3%;
- walk-forward drawdown improvement: 63.3%.

Only trade count and walk-forward drawdown improvement passed. Positive return, positive
expectancy, profit factor, severe-cost survival, neighborhood robustness, walk-forward return and
expectancy, and BTC-relative return/risk all failed.

## Evidence hashes

- `m2_development_evidence.json`: `fa6c6ad1575db199948d215b7c32d9b72399c9d3c0fb07698299816b3056f90e`
- `m2_development_verdict.json`: `0a011006f64a7b9817d8c5c54266d5456298d9649cd0d2ef54ac2765869e3e51`
- research CSV: `253c6ae35856e58e35df17eaa71caeea5caaa3681c38dd7214a2872afccd8d63`
- validation CSV: `3a96b6b668cfacb0fefabb8665675d4ca589cc712b0681fb57e7a13356eda0f2`

## Required next action

Retire the first Trend V1 EMA 20/50 historical cycle. Do not freeze it, do not run risk execution
evidence for promotion, and do not open 2025. A materially new hypothesis must begin a new
development cycle using research/validation only.
