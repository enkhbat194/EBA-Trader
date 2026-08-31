# SF2 production closeout — 2026-08-31

SF2 is closed without promotion. This is a development result only; it is not an OOS or live-trading result.

## Production result

Exact production evidence for the 24 preregistered SF2 candidates across the 12 fresh development windows returned:

- `validationState = NO_VERIFIED_CANDIDATE`
- `verifiedCandidateCount = 0`
- `topVerifiedCandidate = null`
- candidate count: 24
- development window count: 12
- Bonferroni search budget: 48
- exact sign-flip permutations: 4096
- Frozen OOS: closed
- real execution: locked

The highest development-ranked candidate was `s2_fpc_s030` from `flow_price_continuation_v1` with short-side parameters `minimum_delta_ratio=0.3` and `minimum_price_return=0.0005`.

Its aggregate development result was:

- mean return: `-0.005505432851504187` (about `-0.5505%`)
- mean expectancy: `-8.3925263235387`
- total trades: `72`
- baseline-beating windows: `5/12`
- positive-return windows: `2/12`
- mean return delta versus baseline: `-0.0015792335234018535` (about `-0.1579%`)
- raw exact sign-flip p-value: `0.752197265625`
- Bonferroni-adjusted p-value: `1.0`

It failed profitability, baseline-coverage and positive-delta requirements. It had enough trades, so this was not a sparse-sample failure.

The second-ranked candidate, `s2_abs_s030`, was also negative (mean return about `-0.5397%`, mean expectancy about `-9.58`) and beat the baseline in only `5/12` windows. No SF2 candidate was robustness-eligible.

## Scientific decision

Do not retune SF2 thresholds on these same 12 windows. The SF2 evidence has now been inspected and is no longer fresh for a new hypothesis search. Lowering the quality gate or repeatedly fitting to these windows would convert a failed search into adaptive overfitting.

SF3 must therefore:

- use new candidate families rather than post-hoc SF2 threshold changes;
- use development windows not used by SF1 or SF2;
- keep fees at 4 bps and adverse slippage at 1.5 bps;
- keep the 48-hypothesis Bonferroni budget;
- keep the same strict profitability, expectancy, activity, cross-window and significance gate;
- keep Frozen OOS and real execution locked.

SF2 is a useful negative result: direct one-minute order-flow response families remained too costly and economically weak even when trade count was adequate. SF3 therefore preregisters slower multi-bar hypotheses and a longer hold contract before its fresh data is inspected.
