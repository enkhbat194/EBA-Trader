# M4 V3 Bull Pullback Recovery — Development Result

## Decision

`REJECT_V3_SIGNAL_CYCLE`

The frozen V3 signal/allocation layer failed development. Under the predeclared stop rule, the
risk-sized layer was not run and gates 22–34 remained `BLOCKED`. No V3 parameter or gate was changed
after the result, and 2025 OOS remained `LOCKED_NOT_ACCESSED`.

## Verification

Before the final evidence run, two implementation-only issues were corrected without changing the
frozen hypothesis parameters, gates, or datasets:

- portable LF-normalized policy-document hashing;
- two Ruff boolean/style findings in the implementation.

Final validation state:

- branch: `v3-bull-pullback-recovery`;
- final pushed implementation commit: `dfbddf944a462d499e4a9917ad842794c4319266`;
- full pytest: **157 passed**;
- Ruff: **passed**;
- tracked worktree: clean before evidence;
- 2025 OOS: `LOCKED_NOT_ACCESSED`.

## Primary 2024 result

| Metric | Result |
|---|---:|
| Total return | **-13.73%** |
| Maximum drawdown | **-14.64%** |
| Closed trades | **79** |
| Profit factor | **0.612** |
| Expectancy | **-$1.74/trade** |
| Time exposure | **3.86%** |
| Win rate | **41.77%** |

The same-window BTC buy-and-hold return was approximately **+120.64%** with maximum drawdown of
approximately **-32.44%**. V3 reduced drawdown and exposure but did not produce positive expectancy.

## Gate result

- PASS: 1, 7, 8, 9, 10, 13, 14
- FAIL: 2, 3, 4, 5, 6, 11, 12, 15, 16, 17, 18, 19, 20, 21
- BLOCKED: 22–34

Totals: **7 PASS / 14 FAIL / 13 BLOCKED**.

Important failures:

- base return, expectancy and profit factor were negative/insufficient;
- severe-cost return and expectancy were negative;
- V3 expectancy and profit factor did not improve on the regime-only recovery control;
- positive-expectancy neighborhood variants: **0/9**;
- neighborhood variants with profit factor > 1: **0/9**;
- severe positive-expectancy variants: **0/9**;
- rolling folds with trades: **21/30 (70%)**, below the 80% gate;
- positive-return folds: **4/30 (13.33%)**;
- positive-expectancy folds: **4/30 (13.33%)**;
- profit-factor-passing folds: **4/30 (13.33%)**.

## Required action

Retire V3 for promotion. Do not rescue the rejected cycle by retuning the frozen pullback, recovery,
stop, target, or gating parameters. Preserve 2025 as the untouched holdout.

The next research stage is M5 Edge Discovery: measure a finite, predeclared set of market-event
forward-return hypotheses first, then only create a new strategy contract if a stable edge survives
both 2021–2023 discovery and the fixed 2024 development challenge.
