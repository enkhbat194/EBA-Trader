# SF4 two-hypothesis prospective replication — 2026-09-01

## Decision

Do not abandon the two most informative SF3 clues, and do not weaken the definition of a good
strategy to rescue them.

The exact SF3 hypotheses carried forward are:

- `s3_vsm_s150` — short volume-shock momentum. SF3 development evidence was sparse and
  economically negative, so this is a secondary replication/control hypothesis rather than a
  near-verified strategy.
- `s3_cex_s075` — short compression/expansion. SF3 development evidence was economically positive
  and statistically interesting but had only four trades, far below the fixed 30-trade activity
  gate.

SF3 remains CLOSED with `NO_VERIFIED_CANDIDATE`. This follow-up does not reopen SF3 and does not
retroactively qualify either candidate.

## Scientific treatment

The hypotheses were chosen after inspecting SF3 development results. To prevent post-selection
bias from being hidden:

1. both parameter sets are copied exactly and are immutable;
2. no SF3 trade, return, expectancy or p-value may be pooled into the new qualification result;
3. the prospective replication must pass the economic/activity/cross-window/significance gate on
   its new data alone;
4. the conservative SF3 planned search budget of 48 is carried forward for Bonferroni correction,
   even though only two hypotheses are being replicated;
5. Frozen OOS, Demo promotion, live execution and real execution remain unavailable;
6. failure remains a valid outcome and cannot trigger threshold relaxation on the same evidence.

## Prospective data

The replication corpus contains 12 contiguous 24-hour BTCUSDT USD-M windows beginning
`2026-09-01T00:00:00Z` and ending `2026-09-13T00:00:00Z`. These windows were declared before the
first window opened.

Evaluation is fail-closed before `2026-09-13T00:00:00Z`. This longer prospective accrual exists to
make the sparse-event hypothesis testable without borrowing its four inspected SF3 trades.

## Unchanged minimum gate

A replication candidate must independently satisfy all of the following before it can even be
considered for a later robustness phase:

- mean return > 0;
- mean expectancy > 0;
- total trades >= 30;
- baseline beaten in at least 9 of 12 declared windows;
- positive mean return delta versus the fixed baseline;
- exact 4096 window sign-flip test with adjusted p <= 0.05 under a carried-forward multiplicity
  budget of 48.

Passing this replication would still not open Frozen OOS. It would only justify a separately
preregistered robustness step.

## Parallel work

Strategy Factory v2 continues in parallel. Its purpose is broad, bounded discovery; this SF4 track
is narrow prospective replication. Neither track has authority to weaken the other track's safety
or verification gates.
