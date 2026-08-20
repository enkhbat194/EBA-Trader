# M2 — Predeclared Development Screening Gates

## Purpose

These gates are fixed **before** the first real BTC historical development report is generated.

They are not a profit guarantee and they are not a claim that the thresholds are mathematically optimal. Their purpose is narrower: prevent post-hoc rationalization and block the frozen 2025 out-of-sample (OOS) window unless the predeclared EMA 20/50 baseline shows a minimum level of development evidence.

If the development cycle fails these gates, the correct action is to reject this hypothesis and start a new research cycle **without opening 2025**.

## Frozen screening rules

The first Trend V1 development cycle is eligible for frozen OOS only if **all** gates pass.

### Validation evidence

1. Closed trades in 2024 validation: **>= 20**.
2. Validation base-cost total return: **> 0**.
3. Validation base-cost expectancy: **> 0 USD per closed trade**.
4. Validation base-cost profit factor: **> 1.0**.
5. Validation total return under the severe cost scenario: **> 0**.

### Research robustness

6. At least **60%** of the predeclared EMA neighborhood must have positive expectancy.

The neighborhood is diagnostic only; it cannot replace EMA 20/50 in this cycle.

### Rolling walk-forward

7. At least **50%** of test folds must have positive total return.
8. At least **50%** of test folds must have positive expectancy.
9. At least **50%** of test folds must have a shallower maximum drawdown than BTC buy-and-hold over the same test window.

### Validation return/risk tradeoff

10. At least one must be true:

- strategy validation return is at least BTC buy-and-hold return; or
- if the strategy underperforms BTC on return, its maximum-drawdown magnitude must be **<= 75% of BTC's maximum-drawdown magnitude**.

This prevents a materially lower-return strategy from being retained merely because its drawdown is trivially smaller.

## Why these are screening gates, not proof

Passing means only:

> `ELIGIBLE_FOR_FROZEN_OOS`

It does **not** mean:

- the strategy is profitable in the future;
- live trading is approved;
- leverage is approved;
- paper trading is automatically approved.

The frozen OOS is still required, followed by forward PAPER/SHADOW evidence.

## Enforcement

`eba-development-verdict` recalculates the gates from `artifacts/m2_development_evidence.json`.

It writes:

```text
artifacts/m2_development_verdict.json
```

Possible statuses:

- `ELIGIBLE_FOR_FROZEN_OOS`
- `REJECT_DEVELOPMENT_CYCLE`

`eba-final-freeze` does not trust the status strings alone. It recomputes both signal and
risk-execution gates from their hashed evidence and refuses the freeze if either layer fails.

The one-command network wrapper runs screening automatically after tests and development evidence:

```bash
git pull && bash scripts/run_m2_development.sh
```

If screening fails, the wrapper exits before any OOS freeze/open step.
