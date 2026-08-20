# M3 Trend V2 Development Result — 2026-08-20

## Decision

`REJECT_TREND_V2_SIGNAL_CYCLE`

The frozen Trend V2 signal/allocation layer failed 14 of the 23 A–D gates. Under the
predeclared stop rule, the risk-sized E layer was not run and gates 24–36 are `BLOCKED`.
No parameter was changed after the result, the AI module remains excluded, and 2025 OOS
remains `LOCKED_NOT_ACCESSED`.

## Provenance and verification

- Policy SHA-256: `af1b0667e0d0b514379286943c3ff7909140592dd562153e0213eff728a435f9`
- Implementation/evidence Git commit: `1d9bf652e29a10cbcd6af60998b55af2aa0e62d5`
- Full test suite before evidence: 138 passed
- Ruff before evidence: passed, zero findings
- Python: 3.12.14
- Market/window: BTCUSDT Spot 15m; research 2021–2023; validation 2024
- Evidence JSON SHA-256: `e810aef9015750ed11dfbc42f79f6693d1d79a98d39fe4812d76714a2aed05f4`
- Research CSV SHA-256: `253c6ae35856e58e35df17eaa71caeea5caaa3681c38dd7214a2872afccd8d63`
- Validation CSV SHA-256: `3a96b6b668cfacb0fefabb8665675d4ca589cc712b0681fb57e7a13356eda0f2`

## Primary validation result

| Metric | Base cost | Adverse cost | Severe cost |
|---|---:|---:|---:|
| Total return | -17.53% | -27.35% | -47.65% |
| Maximum drawdown | -22.90% | -30.39% | -48.81% |
| Closed trades | 101 | 103 | 105 |
| Profit factor | 0.612 | 0.463 | 0.245 |
| Expectancy | -$1.74 | -$2.66 | -$4.54 |

Additional base-cost facts:

- time exposure: 4.71%;
- BTC buy-and-hold return: 120.64%;
- BTC buy-and-hold maximum drawdown: -32.44%;
- unfiltered V2 control: -81.79% return, -81.79% drawdown, 606 trades,
  0.299 profit factor, and -$1.35 expectancy.

## All 36 gates

| Gate | Section | Status | Test |
|---:|:---:|:---:|---|
| 1 | A | PASS | validation closed trades ≥ 20 |
| 2 | A | FAIL | validation base return > 0 |
| 3 | A | FAIL | validation base expectancy > 0 |
| 4 | A | FAIL | validation base profit factor ≥ 1.15 |
| 5 | A | FAIL | validation severe return > 0 |
| 6 | A | FAIL | validation severe expectancy > 0 |
| 7 | A | PASS | validation drawdown magnitude ≤ 25% |
| 8 | A | FAIL | validation exposure between 5% and 60% |
| 9 | A | FAIL | BTC-relative return/drawdown condition |
| 10 | A | PASS | entry invariant violations = 0 |
| 11 | B | FAIL | filtered expectancy > unfiltered control |
| 12 | B | PASS | filtered profit factor > unfiltered control |
| 13 | B | PASS | filtered drawdown no worse than control |
| 14 | B | PASS | filtered trading cost at least 25% lower |
| 15 | C | FAIL | ≥ 6/9 neighborhood variants have positive base expectancy (actual 0/9) |
| 16 | C | FAIL | ≥ 6/9 variants have base profit factor > 1 (actual 0/9) |
| 17 | C | FAIL | ≥ 5/9 variants have positive severe expectancy (actual 0/9) |
| 18 | C | PASS | baseline is not the sole best on both return and expectancy |
| 19 | D | PASS | rolling folds with trades ≥ 80% (actual 28/30, 93.33%) |
| 20 | D | FAIL | positive-return folds ≥ 60% (actual 11/30, 36.67%) |
| 21 | D | FAIL | positive-expectancy folds ≥ 60% (actual 11/30, 36.67%) |
| 22 | D | FAIL | profit-factor-passing folds ≥ 60% (actual 11/30, 36.67%) |
| 23 | D | PASS | shallower drawdown than BTC in ≥ 60% folds (actual 29/30, 96.67%) |
| 24 | E | BLOCKED | risk-sized closed trades ≥ 20 |
| 25 | E | BLOCKED | risk base return > 0 |
| 26 | E | BLOCKED | risk base expectancy > 0 |
| 27 | E | BLOCKED | risk base profit factor ≥ 1.10 |
| 28 | E | BLOCKED | planned risk per trade ≤ 0.35% |
| 29 | E | BLOCKED | entry notional including fee ≤ 50% |
| 30 | E | BLOCKED | base run does not reach drawdown halt |
| 31 | E | BLOCKED | risk base drawdown > -8% |
| 32 | E | BLOCKED | risk severe return > 0 |
| 33 | E | BLOCKED | risk severe expectancy > 0 |
| 34 | E | BLOCKED | risk severe profit factor > 1 |
| 35 | E | BLOCKED | severe run does not reach drawdown halt |
| 36 | E | BLOCKED | no risk entry/veto invariant violation |

Gate totals: 9 `PASS`, 14 `FAIL`, 13 `BLOCKED`.

## Required action

Stop this Trend V2 cycle. Do not run the risk-sized promotion layer, do not retune any frozen
parameter to fit these results, and do not open 2025 OOS.
